"""Paired synthetic policy experiments; never pass truth to recommendation code."""
from __future__ import annotations

from copy import deepcopy
import gzip
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .common import MECHANISMS, clean_json, digest, stable_uniform, write_json


def stress_ops(original, scenario):
    ops = deepcopy(original)
    if scenario.startswith("rate_"):
        multiplier = float(scenario.removeprefix("rate_"))
        for staff in ops["staff_pools"]:
            staff["rate_per_hour"] *= multiplier
        for equipment in ops["equipment"]:
            equipment["rate_per_hour"] *= multiplier
    elif scenario.startswith("q_"):
        offset = -0.05 if "minus" in scenario else 0.05
        for procedure in ops["procedures"]:
            procedure["inconclusive_probability"] = min(1, max(0, procedure["inconclusive_probability"] + offset))
    elif scenario.startswith("sensitivity_") or scenario.startswith("specificity_"):
        kind = scenario.split("_")[0]
        offset = -0.05 if kind == "sensitivity" else -0.02
        for procedure in ops["procedures"]:
            for question in procedure["binary_outcomes"]:
                key = f"{kind}_if_conclusive"
                question[key] = min(1, max(0, question[key] + offset))
    elif scenario != "base":
        raise ValueError(f"Unknown stress scenario: {scenario}")
    return ops


def _normalise_summary(summary, case, arm, scenario, replication, audit):
    procedures = summary.get("attempted_procedures", summary.get("procedures", []))
    state = summary.get("final_states", {})
    equipment = summary.get("equipment_hours_by_resource", {})
    row = {
        "stack_id": case["stack_id"], "lot_id": case["lot_id"], "split": case["split"],
        "arm": arm, "scenario": scenario, "replication": replication, "synthetic_audit": audit,
        "cost": summary["spent_cost"], "pending_cost": summary["pending_cost"],
        "technician_hours": summary["technician_hours"], "engineer_hours": summary["engineer_hours"],
        "equipment_hours": summary["equipment_hours"], "nominal_hours": summary["nominal_hours"],
        "complete": bool(summary["complete"]), "correctly_complete": bool(summary["correctly_complete"]),
        "concern_complete": bool(summary.get("concern_complete", summary["complete"])),
        "unresolved_count": summary["unresolved_count"], "false_absences": summary["false_absences"],
        "false_positives": summary["false_positives"], "missed_faults": summary["missed_faults"],
        "missed_coexisting_faults": summary["missed_coexisting_faults"],
        "incorrectly_complete": bool(summary["incorrectly_complete"]), "review_pending": bool(summary["review_pending"]),
        "attempts": summary["attempts"], "initial_recommendation": summary.get("initial_recommendation") or "none",
        "repeated_attempts": summary.get("repeated_attempts", 0),
        "unexplained_count": len(summary.get("unexplained_branches", [])),
        "untested_count": len(summary.get("untested_mechanisms", [])),
        "audit_complete": bool(summary["audit_complete"]),
        "mechanism_evidence_complete": bool(summary["mechanism_evidence_complete"]),
        "battery_attempted": set(procedures) == {"XRAY", "ACOUSTIC", "ELECTRICAL", "IR", "SEM"},
        "attempted_procedures": ",".join(procedures),
        "pending_procedures": ",".join(summary.get("pending_procedures", [])),
        "final_states": json.dumps(clean_json(state), sort_keys=True),
        "equipment_hours_by_resource": json.dumps(clean_json(equipment), sort_keys=True),
    }
    for key in ("inconclusive_attempts", "labor_cost", "equipment_cost", "consumables_cost"):
        row[key] = summary.get(key, 0)
    return row


def run_replay(root: Path, out: Path, config: dict):
    from .engine import replay_case
    from .data import load_prepared

    cases, label_table, validation = load_prepared(root, out)
    labels = label_table.set_index("stack_id")
    scoring = json.loads((out / "scoring.json").read_text())
    if not scoring.get("passed") or not scoring.get("fresh_scores_available"):
        raise ValueError("Replay requires a successful fresh scoring batch")
    if digest(out / "predictions.parquet") != scoring["prediction_sha256"]:
        raise ValueError("Predictions changed after scoring")
    predictions = pd.read_parquet(out / "predictions.parquet")
    if predictions.duplicated(["stack_id", "variant"]).any():
        raise ValueError("Duplicate predictions")
    expected = {(s, v) for s in cases.stack_id for v in ("prevalence", "inspection", "full", "manufacturing")}
    if set(zip(predictions.stack_id, predictions.variant)) != expected:
        raise ValueError("Incomplete or unexpected case/variant prediction coverage")
    if not (predictions.split == predictions.stack_id.map(cases.set_index("stack_id").split)).all():
        raise ValueError("Prediction split mismatch")
    ops = json.loads((root / config["operating_assumptions"]).read_text())
    probabilities = {}
    for row in predictions.to_dict("records"):
        values = {m: row[f"p_{m}"] for m in MECHANISMS}
        if not all(np.isfinite(v) and 0 <= v <= 1 for v in values.values()):
            raise ValueError("Research replay requires valid scored probabilities; batch fallback is tested separately")
        probabilities[row["stack_id"], row["variant"]] = values
    truth = {s: {m: int(row[f"fault_{m}"]) for m in MECHANISMS} for s, row in labels.iterrows()}
    audits = {s: stable_uniform(config["seed"], "independent_audit", s) < ops["independent_audit_fraction"] for s in cases.stack_id}
    write_json(out / "synthetic_audits.json", {"source": "new_simulated_assignment_not_recovered_history", "seed": config["seed"], "assignments": audits})
    output_path = out / "replay_cases.parquet"
    temporary = out / "replay_cases.parquet.tmp"
    writer = None
    started = time.monotonic()
    scenario_counts = {}
    events_path = out / "replay_events.jsonl.gz"
    # gzip header has no varying timestamp, making identical seeded runs reproducible.
    with (out / "replay_events.jsonl.gz.tmp").open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=3) as events_file:
        try:
            for scenario in ["base", *config["stress_scenarios"]]:
                allowed = config["replay_splits"] if scenario == "base" else config["stress_splits"]
                selected = cases[cases.split.isin(allowed)].sort_values("stack_id").to_dict("records")
                scenario_ops = stress_ops(ops, scenario)
                count = 0
                for replication in range(config["replications"]):
                    rows = []
                    for case in selected:
                        sid = case["stack_id"]
                        for arm, settings in config["arms"].items():
                            summary, events = replay_case(case, truth[sid], probabilities[sid, settings["variant"]],
                                settings["policy"], scenario_ops, config["seed"], replication, audits[sid])
                            result = _normalise_summary(summary, case, arm, scenario, replication, audits[sid])
                            result["fault_count"] = sum(truth[sid].values())
                            rows.append(result)
                            if scenario == "base":
                                entry = {"stack_id": sid, "split": case["split"], "arm": arm, "replication": replication,
                                         "source": "simulated_not_observed", "events": events}
                                events_file.write((json.dumps(clean_json(entry), separators=(",", ":"), allow_nan=False) + "\n").encode())
                    table = pa.Table.from_pylist(rows)
                    if writer is None:
                        writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
                    writer.write_table(table)
                    count += len(rows)
                    if replication == 0 or (replication + 1) % 20 == 0:
                        print(f"replay {scenario}: {replication + 1}/{config['replications']} replications", flush=True)
                scenario_counts[scenario] = count
        finally:
            if writer is not None:
                writer.close()
    temporary.replace(output_path)
    (out / "replay_events.jsonl.gz.tmp").replace(events_path)
    result = {"replications": config["replications"], "case_arm_runs": scenario_counts,
              "audit_cases": sum(audits.values()), "audit_assignment_fixed_across_arms_and_replications": True,
              "events": "Base scenario stores every decision/report; stress cases store complete summaries and reproducible seed/config.",
              "nominal_time_is_not_turnaround": True, "unknown_review_cost": None,
              "wall_seconds": time.monotonic() - started}
    write_json(out / "replay.json", result)
    return result


METRICS = ["cost", "pending_cost", "technician_hours", "engineer_hours", "equipment_hours", "nominal_hours",
           "complete", "concern_complete", "correctly_complete", "unresolved_count", "unexplained_count", "untested_count",
           "false_absences", "false_positives", "missed_faults",
           "missed_coexisting_faults", "incorrectly_complete", "review_pending", "attempts", "inconclusive_attempts",
           "repeated_attempts", "mechanism_evidence_complete", "battery_attempted", "audit_complete"]


def summarise_replay(out: Path, config: dict):
    frame = pd.read_parquet(out / "replay_cases.parquet")
    means = frame.groupby(["scenario", "split", "arm"], sort=True)[METRICS].mean().reset_index()
    counts = frame.groupby(["scenario", "split", "arm"])["stack_id"].nunique().rename("cases").reset_index()
    means = means.merge(counts, on=["scenario", "split", "arm"])
    means.to_csv(out / "decision_metrics.csv", index=False)
    routine_frame = frame[~frame.synthetic_audit]
    routine_means = routine_frame.groupby(["scenario", "split", "arm"], sort=True)[METRICS].mean().reset_index()
    routine_counts = routine_frame.groupby(["scenario", "split", "arm"])["stack_id"].nunique().rename("cases").reset_index()
    routine_means = routine_means.merge(routine_counts, on=["scenario", "split", "arm"])
    routine_means.to_csv(out / "routine_decision_metrics.csv", index=False)
    baseline = frame[frame.arm == "mock"].set_index(["scenario", "split", "replication", "stack_id"])
    # One paired baseline exists for each arm, seed and case; no independent resampling.
    joined = frame.join(baseline[["initial_recommendation", "attempted_procedures"]],
                        on=["scenario", "split", "replication", "stack_id"], rsuffix="_mock")
    joined["first_choice_differs"] = joined.initial_recommendation != joined.initial_recommendation_mock
    joined["sequence_differs"] = joined.attempted_procedures != joined.attempted_procedures_mock
    changes = joined.groupby(["scenario", "split", "arm"])[["first_choice_differs", "sequence_differs"]].mean().reset_index()
    changes.to_csv(out / "recommendation_changes.csv", index=False)
    rng = np.random.default_rng(config["seed"])
    uncertainty = []
    base = frame[(frame.scenario == "base") & (frame.split != "train")]
    for split, split_frame in base.groupby("split"):
        per_case = split_frame.groupby(["arm", "lot_id", "stack_id"])[METRICS].mean()
        for reference_arm in ("mock", "ct_first"):
            reference = per_case.loc[reference_arm]
            for arm in config["arms"]:
                if arm == reference_arm:
                    continue
                paired = per_case.loc[arm].subtract(reference)
                grouped = paired.groupby("lot_id")
                totals = grouped.sum().to_numpy()
                n = grouped.size().to_numpy()
                chosen = rng.integers(0, len(n), size=(config["bootstrap_samples"], len(n)))
                draws = totals[chosen].sum(axis=1) / n[chosen].sum(axis=1)[:, None]
                # Monte Carlo variation: cases held fixed, paired replication means.
                rep_means = split_frame.groupby(["arm", "replication"])[METRICS].mean()
                rep_diff = rep_means.loc[arm].subtract(rep_means.loc[reference_arm])
                for j, metric in enumerate(METRICS):
                    uncertainty.append({"split": split, "arm": arm, "reference": reference_arm, "metric": metric,
                        "paired_mean_difference": float(paired[metric].mean()),
                        "lot_bootstrap_low": float(np.quantile(draws[:, j], .025)),
                        "lot_bootstrap_high": float(np.quantile(draws[:, j], .975)),
                        "mc_replication_sd": float(rep_diff[metric].std(ddof=1)) if len(rep_diff) > 1 else None,
                        "mc_standard_error": float(rep_diff[metric].std(ddof=1) / np.sqrt(len(rep_diff))) if len(rep_diff) > 1 else None,
                        "lot_count": len(n), "bootstrap_samples": config["bootstrap_samples"]})
    pd.DataFrame(uncertainty).to_csv(out / "decision_uncertainty.csv", index=False)
    # Empirical dominance includes diagnostic quality; no scalar dollar penalty for missing evidence.
    points = means[(means.scenario == "base") & (means.split == "test")].copy()
    dimensions = ["cost", "unresolved_count", "false_absences", "false_positives", "missed_faults", "incorrectly_complete", "nominal_hours"]
    vectors = points[dimensions].to_numpy()
    vectors = np.column_stack([vectors, -points["complete"], -points["correctly_complete"]])
    points["empirically_nondominated"] = [not any(np.all(other <= v + 1e-10) and np.any(other < v - 1e-10)
                                                           for other in vectors) for v in vectors]
    points.to_csv(out / "tradeoffs.csv", index=False)
    slices = frame[frame.scenario == "base"].assign(coexisting=lambda x: x.fault_count > 1).groupby(
        ["split", "arm", "synthetic_audit", "coexisting"])[METRICS].mean().reset_index()
    slices.to_csv(out / "decision_slices.csv", index=False)
    return means
