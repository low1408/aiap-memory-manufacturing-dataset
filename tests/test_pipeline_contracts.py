import json
from pathlib import Path

import pandas as pd
import pytest

from helion_pipeline.common import digest
from helion_pipeline.replay import METRICS, run_replay, stress_ops, summarise_replay


def test_replay_rejects_edited_or_incomplete_scoring(monkeypatch, tmp_path):
    cases = pd.DataFrame([{"stack_id": "s", "lot_id": "L1", "split": "test"}])
    labels = pd.DataFrame([{"stack_id": "s"}])
    monkeypatch.setattr("helion_pipeline.data.load_prepared", lambda root, out: (cases, labels, {}))
    path = tmp_path / "predictions.parquet"
    pd.DataFrame([{"stack_id": "s", "split": "test", "variant": "full"}]).to_parquet(path)
    scoring = {"passed": True, "fresh_scores_available": True, "prediction_sha256": "wrong"}
    (tmp_path / "scoring.json").write_text(json.dumps(scoring))
    with pytest.raises(ValueError, match="changed after scoring"):
        run_replay(tmp_path, tmp_path, {})
    scoring["prediction_sha256"] = digest(path)
    (tmp_path / "scoring.json").write_text(json.dumps(scoring))
    with pytest.raises(ValueError, match="prediction coverage"):
        run_replay(tmp_path, tmp_path, {})


def test_paired_bootstrap_and_quality_aware_tradeoffs(tmp_path):
    rows = []
    # Full is cheaper but incomplete; it must not dominate an otherwise sound comparator.
    for case, lot in [("a", "L1"), ("b", "L1"), ("c", "L2"), ("d", "L3")]:
        for rep in range(2):
            for arm, cost, complete in [("mock", 20., 1.), ("ct_first", 10., 1.), ("full", 5., 0.)]:
                row = dict.fromkeys(METRICS, 0.)
                row.update(stack_id=case, lot_id=lot, split="test", arm=arm, scenario="base", replication=rep,
                           cost=cost, complete=complete, correctly_complete=complete, synthetic_audit=False,
                           fault_count=1, initial_recommendation="XRAY", attempted_procedures="XRAY")
                rows.append(row)
    pd.DataFrame(rows).to_parquet(tmp_path / "replay_cases.parquet")
    summarise_replay(tmp_path, {"seed": 7, "bootstrap_samples": 1000, "arms": {"mock": {}, "ct_first": {}, "full": {}}})
    stats = pd.read_csv(tmp_path / "decision_uncertainty.csv")
    paired = stats.query("arm == 'ct_first' and reference == 'mock' and metric == 'cost'").iloc[0]
    assert paired.paired_mean_difference == paired.lot_bootstrap_low == paired.lot_bootstrap_high == -10
    assert paired.mc_standard_error == 0
    frontier = pd.read_csv(tmp_path / "tradeoffs.csv").set_index("arm")
    assert frontier.loc["ct_first", "empirically_nondominated"]
    assert frontier.loc["full", "empirically_nondominated"]
    assert not frontier.loc["mock", "empirically_nondominated"]


def test_rate_stress_changes_only_allocated_rates_and_not_source():
    root = Path(__file__).resolve().parents[1]
    ops = json.loads((root / "synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.json").read_text())
    altered = stress_ops(ops, "rate_0.75")
    assert altered["staff_pools"][0]["rate_per_hour"] == .75 * ops["staff_pools"][0]["rate_per_hour"]
    assert altered["procedures"] == ops["procedures"]  # supplies, scope and durations unchanged
    assert ops["staff_pools"][0]["rate_per_hour"] == 70
