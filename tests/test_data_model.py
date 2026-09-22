"""Feature/truth boundaries, temporal fitting, persistence and fail-closed scoring."""
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from helion_pipeline import data, model

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    out = tmp_path_factory.mktemp("prepared_research")
    data.validate_and_prepare(ROOT, out, {})
    return out


@pytest.fixture(scope="module")
def trained(prepared):
    model.train_models(ROOT, prepared, {})
    return prepared, joblib.load(prepared / "model.joblib")


def test_exact_cohort_separate_truth_and_missingness_provenance(prepared):
    cases, labels, report = data.load_prepared(ROOT, prepared)
    assert len(cases) == 916
    assert cases.split.value_counts().to_dict() == data.EXPECTED_SPLITS
    assert list(labels.columns) == ["stack_id", *data.LABEL_COLUMNS]
    assert not any(name.startswith(("fault_", "latent_", "p_")) for name in cases)
    assert set(data.FEATURE_GROUPS["full"]).isdisjoint(data.FORBIDDEN_FEATURES)
    assert "timing_margin_ps" not in cases
    assert "capacity_gb" not in cases
    assert cases.metrology_none_count.equals(cases.n_dies_with_detailed_metrology)
    assert cases.sampled_core_cd_mean_nm.isna().sum() == 57
    missing = cases.loc[cases.sampled_core_cd_mean_nm.isna()].iloc[0]
    assert json.loads(missing.measurement_missingness_json)["sampled_core_cd_mean_nm"] == "no_observed_detailed_core_metrology"
    assert len(report["source_checksums"]) == 19  # 18 CSVs and the manifest itself
    assert report["target_support"]["test"]["die_crack"] == 6
    assert report["coexisting_fault_cases"]["test"] == 2
    assert all(gap["lot_release_gap_days"] >= 21 for gap in report["chronology"])
    assert report["chronology"][0]["acceptance_label_to_next_feature_days"] < 21


def test_unknown_label_is_rejected_not_imputed(monkeypatch, tmp_path, prepared):
    original = pd.read_csv
    known_checksums = json.loads((prepared / "validation.json").read_text())["source_checksums"]
    monkeypatch.setattr(data, "verify_sources", lambda *a, **k: known_checksums)
    def read_with_missing_target(path, *args, **kwargs):
        frame = original(path, *args, **kwargs)
        if str(path).endswith("simulation_truth_stack.csv"):
            frame.loc[0, "fault_die_crack"] = np.nan
        return frame
    monkeypatch.setattr(data.pd, "read_csv", read_with_missing_target)
    with pytest.raises(data.DataValidationError, match="Unknown labels"):
        data.validate_and_prepare(ROOT, tmp_path, {})
    assert json.loads((tmp_path / "validation.json").read_text())["passed"] is False
    assert not (tmp_path / "prepared/cases.parquet").exists()


def test_manifest_mismatch_rejects_source(monkeypatch):
    original = data.sha256
    monkeypatch.setattr(data, "sha256", lambda path: "0" * 64 if str(path).endswith("lots.csv") else original(path))
    with pytest.raises(data.DataValidationError, match="Source checksum mismatch"):
        data.verify_sources(ROOT)


def test_train_only_preprocessing_and_folds(trained):
    out, artifact = trained
    cases = pd.read_parquet(out / "prepared/cases.parquet")
    train = cases[cases.split == "train"]
    full = artifact["models"]["full"]
    transform = full.named_steps["preprocess"]
    numeric_names = transform.transformers_[0][2]
    numeric_pipeline = dict(transform.named_transformers_["numeric"].transformer_list)["values"]
    np.testing.assert_allclose(numeric_pipeline.named_steps["impute"].statistics_, train[numeric_names].median().to_numpy())
    expected_mean = train[numeric_names].fillna(train[numeric_names].median()).mean().to_numpy()
    np.testing.assert_allclose(numeric_pipeline.named_steps["scale"].mean_, expected_mean)
    assert len(full.named_steps["classifier"].estimators_) == 7
    assert all(estimator.class_weight is None for estimator in full.named_steps["classifier"].estimators_)
    summary = json.loads((out / "training.json").read_text())
    assert set(artifact["training_stack_ids"]) == set(train.stack_id)
    assert len(summary["cv_results"]) == 27
    by_id = cases.set_index("stack_id")
    for row in summary["cv_results"]:
        fitting = by_id.loc[row["fit_stack_ids"]]
        evaluation = by_id.loc[row["score_stack_ids"]]
        assert fitting.split.eq("train").all() and evaluation.split.eq("train").all()
        assert set(fitting.lot_id).isdisjoint(set(evaluation.lot_id))
        assert pd.to_datetime(fitting.test_time_utc, utc=True).max() < pd.to_datetime(evaluation.feature_available_time_utc, utc=True).min()
    assert set(summary["selected_c"].values()) <= {0.1, 1, 10}
    assert max(summary["reload_max_absolute_error"].values()) == 0


def test_probability_heads_not_normalized_and_reload_equal(trained):
    out, artifact = trained
    cases = pd.read_parquet(out / "prepared/cases.parquet").iloc[:10]
    first = model.predict_cases(cases, artifact)
    second = model.predict_cases(cases, joblib.load(out / "model.joblib"))
    pd.testing.assert_frame_equal(first, second)
    assert first[model.P_COLUMNS].ge(0).all().all() and first[model.P_COLUMNS].le(1).all().all()
    assert not np.allclose(first[model.P_COLUMNS].sum(axis=1), 1)
    assert set(first.variant) == set(model.VARIANTS)


def test_individual_missing_measurement_and_unknown_context(trained):
    out, artifact = trained
    cases = pd.read_parquet(out / "prepared/cases.parquet").iloc[:4].copy()
    cases.loc[cases.index[0], "sampled_core_tsv_void_mean_pct"] = np.nan
    cases.loc[cases.index[1], "assembly_tool_id"] = "NEW_BONDER"
    cases.loc[cases.index[2], "supplier_context"] = "NEW_SUPPLIER"
    cases.loc[cases.index[3], "acceptance_record_available"] = False
    scored = model.predict_cases(cases, artifact)
    statuses = scored[scored.variant == "full"].set_index("stack_id").scoring_status
    assert statuses.iloc[0] == "scored_retrospective"
    assert statuses.iloc[1] == statuses.iloc[2] == "manual_review_unqualified_context"
    assert statuses.iloc[3] == "fallback_rules_missing_acceptance"
    assert scored.loc[scored.scoring_status != "scored_retrospective", model.P_COLUMNS].isna().all().all()
    assert scored.loc[scored.scoring_status == "scored_retrospective", model.P_COLUMNS].notna().all().all()


def test_batch_failure_and_truth_contamination(trained):
    out, artifact = trained
    cases = pd.read_parquet(out / "prepared/cases.parquet").iloc[:2].copy()
    with pytest.raises(data.DataValidationError, match="Invalid nightly import"):
        model.predict_cases(cases, artifact, batch_valid=False)
    with pytest.raises(data.DataValidationError, match="Incomplete import schema"):
        model.predict_cases(cases.drop(columns="electrical_test_pass"), artifact)
    cases["fault_die_crack"] = 0
    with pytest.raises(data.DataValidationError, match="Truth/probability"):
        model.predict_cases(cases, artifact)


def test_failed_stage_removes_stale_predictions(monkeypatch, tmp_path):
    (tmp_path / "predictions.parquet").write_text("a stale batch")
    def unavailable(*args, **kwargs):
        raise data.DataValidationError("failed import")
    monkeypatch.setattr(model, "load_prepared", unavailable)
    with pytest.raises(data.DataValidationError, match="failed import"):
        model.score_models(ROOT, tmp_path, {})
    assert not (tmp_path / "predictions.parquet").exists()
    assert json.loads((tmp_path / "scoring.json").read_text())["fresh_scores_available"] is False


def test_metrics_have_support_and_calibration_counts(trained):
    out, artifact = trained
    cases = pd.read_parquet(out / "prepared/cases.parquet")
    labels = pd.read_parquet(out / "prepared/labels.parquet")
    predictions = model.predict_cases(cases, artifact)
    metrics, calibration = model._metrics_and_calibration(predictions, labels)
    test = metrics[(metrics.split == "test") & (metrics.variant == "full")]
    assert set(test.mechanism) == {*data.MECHANISMS, "macro", "micro"}
    assert test.loc[test.mechanism == "die_crack", "positives"].item() == 6
    assert test.evidence_role.eq("retrospective").all()
    counts = calibration.groupby(["split", "variant", "mechanism"]).n.sum()
    assert counts.loc["test"].eq(137).all()
    assert metrics.binary_log_loss.ge(0).all()
    assert metrics.brier_score.between(0, 1).all()
