"""Validated, point-in-time feature view for the rejected-stack research cohort.

The simulator truth table is read with a target-only ``usecols`` restriction.
Neither its latent state nor generating probabilities enter the feature view.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MECHANISMS = (
    "dram_electrical", "tsv_open_short", "microbump_open_bridge", "die_crack",
    "warpage", "underfill_void", "delamination",
)
LABEL_COLUMNS = tuple(f"fault_{m}" for m in MECHANISMS)
ACCEPTANCE_FEATURES = (
    "stack_assembly_pass", "electrical_test_pass", "uncorrected_error_count",
    "ecc_corrected_errors", "detected_interconnect_failures", "max_pass_data_rate_gbps",
    "measured_bandwidth_gb_s", "power_consumption_w", "thermal_resistance_c_w",
)
MANUFACTURING_FEATURES = (
    "stack_layer_count", "assembly_tool_id", "stack_height_um", "inter_die_gap_mean_um",
    "max_alignment_offset_um", "cumulative_die_shift_um", "emc_viscosity_pa_s",
    "molding_pressure_mpa", "molding_vacuum_absolute_kpa", "reflow_peak_temperature_c",
    "time_above_liquidus_sec", "heating_rate_c_sec", "cure_temperature_c",
    "cure_duration_min", "underfill_void_pct", "delamination_area_pct",
    "package_warpage_um", "stacks_since_tool_service", "core_thickness_mean_um",
    "core_thickness_std_um", "core_warpage_max_um", "core_ttv_mean_um",
    "core_leakage_mean_ua", "core_repair_count_sum", "core_particle_count_sum",
    "core_tsv_resistance_mean_mohm", "core_tsv_resistance_max_mohm",
    "core_bump_coplanarity_max_um", "n_source_wafers", "n_dies_with_detailed_metrology",
    "sampled_core_tsv_void_mean_pct", "sampled_core_cd_mean_nm",
    "base_leakage_current_ua", "base_die_thickness_um",
)
INSPECTION_FEATURES = (
    "stack_layer_count", "underfill_void_pct", "delamination_area_pct",
    "package_warpage_um", "sampled_core_tsv_void_mean_pct", "n_dies_with_detailed_metrology",
) + ACCEPTANCE_FEATURES
FEATURE_GROUPS = {
    "inspection": list(INSPECTION_FEATURES),
    "full": list(MANUFACTURING_FEATURES + ACCEPTANCE_FEATURES),
    "manufacturing": list(MANUFACTURING_FEATURES),
}
FOLDS = ((60, 103, 124), (82, 125, 146), (104, 147, 168))
EXPECTED_SPLITS = {"train": 653, "validation": 126, "test": 137}
FORBIDDEN_FEATURES = frozenset({
    "capacity_gb", "stack_id", "lot_id", "split", "feature_available_time_utc",
    "test_time_utc", "label_available_time_utc", "timing_margin_ps", "final_test_fail",
    "final_test_pass", "defect_type", "defect_stage", "defect_severity", "final_disposition",
    "reliability_pass", "reliability_sampled", "audit_member",
} | set(LABEL_COLUMNS))


class DataValidationError(ValueError):
    """A failed import must not create fresh features or scores."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DataValidationError(message)


def unique(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    require(not frame[columns].isna().any().any(), f"Missing key in {source}: {columns}")
    require(not frame.duplicated(columns).any(), f"Duplicate key in {source}: {columns}")


def verify_sources(root: Path, *, dimensions: bool = False) -> dict[str, str]:
    """Hash every delivered CSV; optionally check the declared rectangular dimensions."""
    root = Path(root)
    manifest_path = root / "metadata/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    require(len(manifest["files"]) == 18, "Expected all 18 supplied manifest tables")
    checksums = {"metadata/manifest.json": sha256(manifest_path)}
    for entry in manifest["files"]:
        relative = Path(entry["file"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe manifest path")
        path = root / relative
        require(path.is_file(), f"Missing source file: {relative}")
        digest = sha256(path)
        require(digest == entry["sha256"], f"Source checksum mismatch: {relative}")
        checksums[str(relative)] = digest
        if dimensions:
            with path.open(newline="") as stream:
                rows = csv.reader(stream)
                header = next(rows)
                require(len(header) == entry["columns"], f"Column count mismatch: {relative}")
                count = 0
                for count, row in enumerate(rows, 1):
                    require(len(row) == len(header), f"Nonrectangular CSV: {relative} row {count}")
                require(count == entry["rows"], f"Row count mismatch: {relative}")
    return checksums


def _same_ids(left: pd.DataFrame, right: pd.DataFrame, name: str) -> None:
    unique(right, ["stack_id"], name)
    require(set(left.stack_id) == set(right.stack_id), f"Incomplete one-to-one join: {name}")


def _time(series: pd.Series) -> pd.Series:
    result = pd.to_datetime(series, utc=True, errors="coerce")
    require(result.notna().all(), f"Invalid or missing timestamp: {series.name}")
    return result


def _prepare(root: Path, out: Path, config: dict) -> dict:
    source_hashes = verify_sources(root, dimensions=True)
    features = pd.read_csv(root / "data/ml/ml_stack_features.csv")
    unique(features, ["stack_id"], "manufacturing feature view")
    expected = set(MANUFACTURING_FEATURES) | {"stack_id", "lot_id", "split", "capacity_gb", "feature_available_time_utc"}
    require(set(features.columns) == expected, "Unexpected manufacturing feature schema")
    require(len(features) == 17793, "Expected 17,793 source stacks")
    acceptance = pd.read_csv(root / "data/assembly/electrical_test.csv", usecols=[
        "stack_id", "test_time_utc", *ACCEPTANCE_FEATURES,
    ])
    eligibility = pd.read_csv(root / "data/ml/ml_stack_labels.csv", usecols=[
        "stack_id", "split", "final_test_fail", "label_available_time_utc",
    ])
    # Only the join key and seven labels cross the simulator-truth boundary.
    labels = pd.read_csv(root / "data/simulation_truth/simulation_truth_stack.csv",
                         usecols=["stack_id", *LABEL_COLUMNS])
    assembly = pd.read_csv(root / "data/assembly/stack_assembly.csv", usecols=[
        "stack_id", "lot_id", "split", "base_die_id", "product_generation", "packaging_route",
        "emc_batch_id", "assembly_start_time_utc", "assembly_end_time_utc",
    ])
    for name, table in (("acceptance", acceptance), ("eligibility", eligibility), ("labels", labels), ("assembly", assembly)):
        _same_ids(features, table, name)
    require(eligibility.final_test_fail.isin([0, 1]).all(), "Unknown or invalid acceptance eligibility")
    require(labels[list(LABEL_COLUMNS)].isin([0, 1]).all().all(), "Unknown labels cannot be replaced by negatives")
    labels = labels.set_index("stack_id").loc[features.stack_id].reset_index()
    eligibility = eligibility.set_index("stack_id").loc[features.stack_id].reset_index()
    assembly = assembly.set_index("stack_id").loc[features.stack_id].reset_index()
    require(features.split.equals(eligibility.split), "Eligibility split disagrees with features")
    require(features.split.equals(assembly.split) and features.lot_id.equals(assembly.lot_id), "Assembly partition mismatch")
    require(np.array_equal(labels[list(LABEL_COLUMNS)].max(axis=1), eligibility.final_test_fail), "Fault OR must agree with source acceptance failure")
    require(set(features.split) == set(EXPECTED_SPLITS), "Unexpected source partitions")
    require(features.groupby("lot_id").split.nunique().max() == 1, "A lot crosses partitions")
    cases = features.drop(columns="capacity_gb").merge(acceptance, on="stack_id", validate="one_to_one")
    cases = cases.merge(assembly.drop(columns=["lot_id", "split"]), on="stack_id", validate="one_to_one")
    cases = cases.merge(eligibility.drop(columns="split"), on="stack_id", validate="one_to_one")
    require((_time(cases.assembly_start_time_utc) <= _time(cases.assembly_end_time_utc)).all(), "Invalid assembly chronology")
    require((_time(cases.assembly_end_time_utc) <= _time(cases.feature_available_time_utc)).all(), "Features precede assembly completion")
    require((_time(cases.feature_available_time_utc) <= _time(cases.test_time_utc)).all(), "Acceptance precedes source feature availability")
    require((_time(cases.test_time_utc) == _time(cases.label_available_time_utc)).all(), "Unexpected source acceptance label timestamp")
    require(cases[list(ACCEPTANCE_FEATURES)].notna().all().all(), "Incomplete initial acceptance record")
    for column in ("stack_assembly_pass", "electrical_test_pass"):
        require(cases[column].isin([0, 1]).all(), f"Invalid acceptance verdict {column}")
    require(np.array_equal((1 - cases.stack_assembly_pass * cases.electrical_test_pass), cases.final_test_fail), "Acceptance components disagree with eligibility")
    numeric = [c for c in FEATURE_GROUPS["full"] if c != "assembly_tool_id"]
    require(not np.isinf(cases[numeric].to_numpy(dtype=float)).any(), "Infinite predictor value")
    require(cases.assembly_tool_id.notna().all(), "Missing tool qualification identifier")

    # Validate upstream identities and chronology on the full supplied population.
    membership = pd.read_csv(root / "data/assembly/stack_membership.csv", usecols=[
        "stack_id", "die_role", "die_id", "base_die_id", "layer_index", "placement_time_utc",
    ])
    unique(membership, ["stack_id", "layer_index"], "membership")
    require(set(membership.stack_id) == set(cases.stack_id), "Membership coverage mismatch")
    dies = pd.read_csv(root / "data/manufacturing/die_metrology.csv", usecols=[
        "die_id", "wafer_id", "available_time_utc", "metrology_sampled", "metrology_missing_reason",
    ], keep_default_na=False)
    wafers = pd.read_csv(root / "data/manufacturing/wafers.csv", usecols=["wafer_id", "lot_id", "split"])
    lots = pd.read_csv(root / "data/manufacturing/lots.csv", usecols=["lot_id", "split", "release_time_utc"])
    unique(dies, ["die_id"], "dies")
    unique(wafers, ["wafer_id"], "wafers")
    unique(lots, ["lot_id"], "lots")
    require(set(dies.wafer_id) <= set(wafers.wafer_id), "Unresolved die-to-wafer key")
    require(set(wafers.lot_id) == set(lots.lot_id), "Unresolved wafer-to-lot key")
    lot_map = lots.set_index("lot_id").split
    require((wafers.split == wafers.lot_id.map(lot_map)).all(), "Wafer partition disagrees with lot")
    require((cases.split == cases.lot_id.map(lot_map)).all(), "Stack partition disagrees with lot")
    core = membership[membership.die_role.eq("core")].merge(dies, on="die_id", how="left", validate="many_to_one")
    require(core.wafer_id.notna().all(), "Unresolved core-die membership")
    core = core.merge(wafers.rename(columns={"lot_id": "wafer_lot_id", "split": "wafer_split"}), on="wafer_id", validate="many_to_one")
    core = core.merge(cases[["stack_id", "lot_id", "split", "assembly_start_time_utc"]], on="stack_id", validate="many_to_one")
    require((core.wafer_split == core.split).all(), "A constituent wafer crosses partitions")
    for key in ("die_id", "wafer_id", "wafer_lot_id"):
        require(core.groupby(key).split.nunique().max() == 1, f"{key} crosses partitions")
    require(not core.die_id.duplicated().any(), "A core die is reused across stacks")
    require((_time(core.available_time_utc) <= _time(core.placement_time_utc)).all(), "Core die not available at placement")
    require((_time(core.assembly_start_time_utc) <= _time(core.placement_time_utc)).all(), "Placement precedes assembly start")
    base = membership[membership.die_role.eq("base")]
    require(base.base_die_id.notna().all() and not base.base_die_id.duplicated().any(), "Missing or reused base die")
    require(set(base.stack_id) == set(cases.stack_id), "Incomplete base-die membership")
    base_map = base.set_index("stack_id").base_die_id
    require((cases.base_die_id == cases.stack_id.map(base_map)).all(), "Base-die identity mismatch")
    reasons = {"none", "not_sampled", "instrument_dropout"}
    require(set(core.metrology_missing_reason) <= reasons, "Unrecognized metrology missingness reason")
    reason_counts = pd.crosstab(core.stack_id, core.metrology_missing_reason).reindex(columns=sorted(reasons), fill_value=0)
    for reason in sorted(reasons):
        cases[f"metrology_{reason}_count"] = cases.stack_id.map(reason_counts[reason]).astype(int)
    require((cases.metrology_none_count == cases.n_dies_with_detailed_metrology).all(), "Metrology coverage aggregate disagrees with membership provenance")
    require((cases[[f"metrology_{r}_count" for r in reasons]].sum(axis=1) == cases.stack_layer_count).all(), "Core membership count mismatch")
    require((cases.stack_id.map(core.groupby("stack_id").wafer_id.nunique()) == cases.n_source_wafers).all(), "Source-wafer aggregate mismatch")
    cases["source_wafer_ids_json"] = cases.stack_id.map(core.groupby("stack_id").wafer_id.apply(lambda x: json.dumps(sorted(set(x)))))
    cases["source_die_ids_json"] = cases.stack_id.map(core.groupby("stack_id").die_id.apply(lambda x: json.dumps(sorted(x))))

    gap_records = []
    for previous, following in (("train", "validation"), ("validation", "test")):
        release_gap = (_time(lots.loc[lots.split.eq(following), "release_time_utc"]).min() - _time(lots.loc[lots.split.eq(previous), "release_time_utc"]).max()).total_seconds() / 86400
        availability_gap = (_time(cases.loc[cases.split.eq(following), "feature_available_time_utc"]).min() - _time(cases.loc[cases.split.eq(previous), "label_available_time_utc"]).max()).total_seconds() / 86400
        require(release_gap >= 21, "Lot-release separation is less than 21 days")
        require(availability_gap > 0, "Source partitions overlap in observation chronology")
        gap_records.append({"previous": previous, "following": following, "lot_release_gap_days": release_gap,
                            "acceptance_label_to_next_feature_days": availability_gap})
    fold_records = []
    lot_numbers = lots.lot_id.str[1:].astype(int)
    for number, (fit_end, score_start, score_end) in enumerate(FOLDS, 1):
        fitted = lots[lot_numbers.le(fit_end)]
        scored = lots[lot_numbers.between(score_start, score_end)]
        require(fitted.split.eq("train").all() and scored.split.eq("train").all(), "CV fold uses held-out partitions")
        gap = (_time(scored.release_time_utc).min() - _time(fitted.release_time_utc).max()).total_seconds() / 86400
        require(gap >= 21, "CV lot-release separation is less than 21 days")
        fold_records.append({"fold": number, "fit_lots": [1, fit_end], "score_lots": [score_start, score_end], "lot_release_gap_days": gap})

    # Eligibility is not a predictor; rejected cases alone form this new task.
    rejected = cases[cases.final_test_fail.eq(1)].drop(columns="final_test_fail").copy()
    require(rejected.split.value_counts().to_dict() == EXPECTED_SPLITS, "Rejected cohort/split counts changed")
    rejected = rejected.sort_values("stack_id").reset_index(drop=True)
    rejected["acceptance_record_available"] = True
    rejected["supplier_context"] = "not_recorded_in_source"
    rejected["qualification_context_status"] = "retrospective_synthetic_only"
    rejected["availability_checkpoint"] = "initial_acceptance_complete_before_additional_diagnosis_assumed"
    def missingness(row):
        return json.dumps({c: ("no_observed_detailed_core_metrology" if c.startswith("sampled_core_") and row.n_dies_with_detailed_metrology == 0 else "missing_measurement")
                           for c in FEATURE_GROUPS["full"] if pd.isna(row[c])}, sort_keys=True)
    rejected["measurement_missingness_json"] = rejected.apply(missingness, axis=1)
    rejected_labels = labels.set_index("stack_id").loc[rejected.stack_id].reset_index()
    require(not (set(FEATURE_GROUPS["full"]) & FORBIDDEN_FEATURES), "Prohibited feature selected")
    prepared = out / "prepared"
    prepared.mkdir(parents=True, exist_ok=True)
    rejected.to_parquet(prepared / "cases.parquet", index=False)
    rejected_labels.to_parquet(prepared / "labels.parquet", index=False)
    supports = rejected[["stack_id", "split"]].merge(rejected_labels, on="stack_id", validate="one_to_one")
    summary = {
        "passed": True, "schema_version": "helion-diagnostic-data-v1", "source_checksums": source_hashes,
        "prepared_checksums": {name: sha256(prepared / name) for name in ("cases.parquet", "labels.parquet")},
        "all_source_stacks": len(features), "rejected_stacks": len(rejected), "split_counts": EXPECTED_SPLITS,
        "feature_groups": FEATURE_GROUPS, "label_columns": list(LABEL_COLUMNS), "mechanisms": list(MECHANISMS),
        "target_support": {s: {m: int(supports.loc[supports.split.eq(s), f"fault_{m}"].sum()) for m in MECHANISMS} for s in EXPECTED_SPLITS},
        "coexisting_fault_cases": {s: int(supports.loc[supports.split.eq(s), list(LABEL_COLUMNS)].sum(axis=1).gt(1).sum()) for s in EXPECTED_SPLITS},
        "missing_feature_counts": {c: int(rejected[c].isna().sum()) for c in FEATURE_GROUPS["full"] if rejected[c].isna().any()},
        "chronology": gap_records, "training_folds": fold_records,
        "qualification": "Retrospective supplied synthetic context only; supplier identity and actual diagnostic-result timestamps are absent.",
        "evidence_boundary": "Acceptance label time equals initial test time; it does not establish a delayed diagnostic-label chronology. Several acceptance fields are synthetic truth-derived readings. No procedure history or audit flag is supplied.",
        "embargo_interpretation": "The supplied 21-day embargo is a lot-release rule, not a 21-day acceptance-label-to-next-feature gap.",
    }
    write_json(out / "validation.json", summary)
    return summary


def validate_and_prepare(root: Path, out: Path, config: dict) -> dict:
    root, out = Path(root), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        return _prepare(root, out, config)
    except Exception as exc:
        write_json(out / "validation.json", {"passed": False, "error": str(exc), "fresh_features_available": False})
        raise


def load_prepared(root: Path, out: Path, *, include_labels: bool = True) -> tuple[pd.DataFrame, pd.DataFrame | None, dict]:
    """Read only validated prepared records; fail closed after source or import changes."""
    root, out = Path(root), Path(out)
    validation = json.loads((out / "validation.json").read_text())
    require(validation.get("passed") is True, "No successful current data validation")
    require(verify_sources(root) == validation["source_checksums"], "Sources changed after preparation")
    for name, expected in validation["prepared_checksums"].items():
        require(sha256(out / "prepared" / name) == expected, f"Prepared table changed without validation: {name}")
    cases = pd.read_parquet(out / "prepared/cases.parquet")
    labels = pd.read_parquet(out / "prepared/labels.parquet") if include_labels else None
    return cases, labels, validation
