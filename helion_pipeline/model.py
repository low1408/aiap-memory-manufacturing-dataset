"""Seven independent binary logistic heads and retrospective predictive comparisons.

The saved joblib file is a single research artifact containing three ablation
variants. Scoring never fits a transformation and never uses labels to predict.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import MissingIndicator, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .data import (ACCEPTANCE_FEATURES, FEATURE_GROUPS, FOLDS, LABEL_COLUMNS, MECHANISMS,
                   DataValidationError, load_prepared, require, sha256, unique, write_json)

MODEL_SCHEMA = "helion-logistic-research-v1"
P_COLUMNS = [f"p_{m}" for m in MECHANISMS]
VARIANTS = ("prevalence", "inspection", "full", "manufacturing")


def make_pipeline(columns: list[str], c_value: float, seed: int) -> Pipeline:
    numeric = [name for name in columns if name != "assembly_tool_id"]
    categorical = [name for name in columns if name == "assembly_tool_id"]
    # All numeric fields get a missing indicator, including measurements that
    # happened to be complete in the training window but may be missing later.
    numeric_transform = FeatureUnion([
        ("values", Pipeline([
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
        ])),
        ("missing", MissingIndicator(features="all", error_on_new=False)),
    ])
    transforms = [("numeric", numeric_transform, numeric)]
    if categorical:
        transforms.append(("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical))
    preprocess = ColumnTransformer(transforms, remainder="drop", sparse_threshold=0)
    classifier = MultiOutputClassifier(LogisticRegression(
        C=float(c_value), solver="lbfgs", max_iter=4000, tol=1e-7,
        class_weight=None, random_state=seed,
    ), n_jobs=1)
    return Pipeline([("preprocess", preprocess), ("classifier", classifier)])


def _probabilities(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    predictions = model.predict_proba(frame)
    return np.column_stack([head[:, 1] for head in predictions])


def _mean_log_loss(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean([log_loss(y[:, i], p[:, i], labels=[0, 1]) for i in range(y.shape[1])]))


def _fit(model: Pipeline, x: pd.DataFrame, y: np.ndarray) -> None:
    require(all(len(np.unique(y[:, i])) == 2 for i in range(y.shape[1])), "Every logistic head requires both classes in each fit window")
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(x, y)


def train_models(root: Path, out: Path, config: dict) -> dict:
    root, out = Path(root), Path(out)
    cases, labels, validation = load_prepared(root, out)
    labels = labels.set_index("stack_id").loc[cases.stack_id]
    train_mask = cases.split.eq("train")
    x = cases.loc[train_mask].reset_index(drop=True)
    y = labels.loc[x.stack_id, list(LABEL_COLUMNS)].to_numpy(dtype=int)
    require(len(x) == 653, "Model fitting must use exactly the 653 training cases")
    seed = int(config.get("seed", 20260921))
    c_values = sorted(float(value) for value in config.get("c_values", [0.1, 1, 10]))
    require(c_values == [0.1, 1.0, 10.0], "Frozen v1 tuning budget is C = [0.1, 1, 10]")
    lot_numbers = x.lot_id.str[1:].astype(int)
    models, selected_c, tuning = {}, {}, []
    folds = []
    for fold_id, (fit_end, score_start, score_end) in enumerate(FOLDS, 1):
        fit_index = np.flatnonzero(lot_numbers.le(fit_end))
        score_index = np.flatnonzero(lot_numbers.between(score_start, score_end))
        require(len(fit_index) > 0 and len(score_index) > 0, "Empty training-only chronological fold")
        require(not set(x.iloc[fit_index].lot_id) & set(x.iloc[score_index].lot_id), "CV lot overlap")
        require(pd.to_datetime(x.iloc[fit_index].test_time_utc, utc=True).max() < pd.to_datetime(x.iloc[score_index].feature_available_time_utc, utc=True).min(), "CV information-time overlap")
        folds.append((fit_index, score_index))
    for variant, columns in FEATURE_GROUPS.items():
        losses = []
        for c_value in c_values:
            fold_losses = []
            for fold_id, (fit_index, score_index) in enumerate(folds, 1):
                candidate = make_pipeline(columns, c_value, seed)
                _fit(candidate, x.iloc[fit_index][columns], y[fit_index])
                loss = _mean_log_loss(y[score_index], _probabilities(candidate, x.iloc[score_index][columns]))
                fold_losses.append(loss)
                tuning.append({"variant": variant, "C": c_value, "fold": fold_id, "mean_binary_log_loss": loss,
                               "n_fit": len(fit_index), "n_score": len(score_index),
                               "fit_stack_ids": x.iloc[fit_index].stack_id.tolist(),
                               "score_stack_ids": x.iloc[score_index].stack_id.tolist()})
            losses.append((float(np.mean(fold_losses)), c_value))
        best_loss = min(value for value, _ in losses)
        chosen = min(c for loss, c in losses if abs(loss - best_loss) <= 1e-10)
        selected_c[variant] = chosen
        final_model = make_pipeline(columns, chosen, seed)
        _fit(final_model, x[columns], y)
        models[variant] = final_model
    qualification = {
        "status": "retrospective_synthetic_only_not_production_qualified",
        "assembly_tool_ids": sorted(x.assembly_tool_id.unique().tolist()),
        "stack_layer_counts": sorted(int(v) for v in x.stack_layer_count.unique()),
        "product_generations": sorted(x.product_generation.unique().tolist()),
        "packaging_routes": sorted(x.packaging_route.unique().tolist()),
        "supplier_contexts": ["not_recorded_in_source"],
        "supplier_warning": "Supplier identities are absent. EMC batches are retained as metadata, not treated as supplier identities; new supplied supplier identities require review.",
    }
    model_digest = hashlib.sha256(json.dumps({"schema": MODEL_SCHEMA, "seed": seed, "source_checksums": validation["source_checksums"],
                                              "selected_c": selected_c, "features": FEATURE_GROUPS}, sort_keys=True).encode()).hexdigest()[:12]
    model_version = f"{MODEL_SCHEMA}-{model_digest}"
    dependencies = {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scikit-learn", "joblib", "pyarrow")}
    artifact = {
        "schema_version": MODEL_SCHEMA, "model_version": model_version, "models": models,
        "prevalence": y.mean(axis=0), "mechanisms": list(MECHANISMS), "label_columns": list(LABEL_COLUMNS),
        "feature_groups": FEATURE_GROUPS, "selected_c": selected_c, "seed": seed,
        "qualification": qualification, "source_checksums": validation["source_checksums"],
        "prepared_checksums": validation["prepared_checksums"], "training_stack_ids": x.stack_id.tolist(),
        "dependencies": dependencies,
    }
    joblib.dump(artifact, out / "model.joblib", compress=3)
    reloaded = joblib.load(out / "model.joblib")
    reload_errors = {variant: float(np.max(np.abs(_probabilities(models[variant], x[columns]) - _probabilities(reloaded["models"][variant], x[columns]))))
                     for variant, columns in FEATURE_GROUPS.items()}
    require(max(reload_errors.values()) == 0, "Saved-model prediction mismatch")
    summary = {
        "schema_version": MODEL_SCHEMA, "model_version": model_version, "model_sha256": sha256(out / "model.joblib"),
        "seed": seed, "dependencies": dependencies, "source_checksums": validation["source_checksums"],
        "feature_groups": FEATURE_GROUPS, "mechanisms": list(MECHANISMS), "selected_c": selected_c,
        "training_cases": len(x), "training_prevalence": dict(zip(MECHANISMS, y.mean(axis=0).tolist())),
        "training_stack_ids": x.stack_id.tolist(), "cv_results": tuning, "qualification": qualification,
        "reload_max_absolute_error": reload_errors,
        "regularisation": "L2 with lbfgs; no class weighting or resampling. Shared C across seven heads within each feature variant.",
        "selection": "Mean of per-fold mean binary log loss; select smaller C for ties within 1e-10; all folds inside supplied train partition.",
        "calibration": "Assessed without a fitted calibration model; probability heads are not normalized across mechanisms.",
        "interpretation": "Validation is development evidence; the already inspected test cohort is retrospective. Acceptance readings may be generated from synthetic fault truth; manufacturing-only ablation is required.",
    }
    write_json(out / "training.json", summary)
    return summary


def predict_cases(cases: pd.DataFrame, artifact: dict, *, batch_valid: bool = True) -> pd.DataFrame:
    """Score a logical CaseSnapshot batch without loading labels or refitting.

    Schema/ingestion failure raises before producing any predictions. Individual
    out-of-context cases retain explicit fallback records with null probabilities.
    Missing numeric measurements are imputable; absent acceptance records are not.
    """
    require(batch_valid, "Invalid nightly import: no fresh scores")
    require(artifact.get("schema_version") == MODEL_SCHEMA, "Unsupported model schema")
    require(not any(c.startswith("fault_") or c.startswith("latent_") or c.startswith("p_") for c in cases.columns), "Truth/probability fields must not enter a case snapshot")
    required = set(FEATURE_GROUPS["full"]) | {"stack_id", "split", "acceptance_record_available", "product_generation", "packaging_route", "supplier_context"}
    require(required <= set(cases.columns), f"Incomplete import schema: {sorted(required - set(cases.columns))}")
    unique(cases, ["stack_id"], "scoring batch")
    values = cases.copy()
    numeric = [name for name in FEATURE_GROUPS["full"] if name != "assembly_tool_id"]
    for column in numeric:
        values[column] = pd.to_numeric(values[column], errors="raise")
    require(not np.isinf(values[numeric].to_numpy(dtype=float)).any(), "Invalid infinite measurement in scoring batch")
    status = pd.Series("scored_retrospective", index=values.index)
    reason = pd.Series("initial probabilities; synthetic retrospective qualification only", index=values.index)
    missing_record = ~values.acceptance_record_available.eq(True)
    status.loc[missing_record] = "fallback_rules_missing_acceptance"
    reason.loc[missing_record] = "required initial acceptance record unavailable"
    qualification = artifact["qualification"]
    context_checks = {
        "assembly_tool_id": qualification["assembly_tool_ids"],
        "stack_layer_count": qualification["stack_layer_counts"],
        "product_generation": qualification["product_generations"],
        "packaging_route": qualification["packaging_routes"],
        "supplier_context": qualification["supplier_contexts"],
    }
    for column, qualified in context_checks.items():
        outside = ~values[column].isin(qualified)
        status.loc[outside] = "manual_review_unqualified_context"
        reason.loc[outside] = f"unqualified or unavailable {column}"
    if "supplier_id" in values:
        outside = values.supplier_id.notna() & values.supplier_id.ne("")
        status.loc[outside] = "manual_review_unqualified_context"
        reason.loc[outside] = "supplier identity not qualified by the supplied training data"
    if "qualification_review_required" in values:
        outside = values.qualification_review_required.fillna(True).astype(bool)
        status.loc[outside] = "manual_review_unqualified_context"
        reason.loc[outside] = "explicit qualification review required"
    valid = status.eq("scored_retrospective")
    records = []
    for variant in VARIANTS:
        prediction = np.full((len(values), len(MECHANISMS)), np.nan)
        if valid.any():
            if variant == "prevalence":
                prediction[valid.to_numpy()] = artifact["prevalence"]
            else:
                columns = artifact["feature_groups"][variant]
                prediction[valid.to_numpy()] = _probabilities(artifact["models"][variant], values.loc[valid, columns])
        result = values[["stack_id", "split"]].copy()
        if "lot_id" in values:
            result["lot_id"] = values.lot_id
        result["variant"] = variant
        result["model_version"] = artifact["model_version"]
        result["scoring_status"] = status
        result["scoring_reason"] = reason
        result["missing_feature_count"] = values[FEATURE_GROUPS["full"]].isna().sum(axis=1)
        for index, column in enumerate(P_COLUMNS):
            result[column] = prediction[:, index]
        records.append(result)
    return pd.concat(records, ignore_index=True)


def _metrics_and_calibration(predictions: pd.DataFrame, labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    evaluated = predictions.merge(labels, on="stack_id", validate="many_to_one")
    metrics, calibration = [], []
    edges = np.linspace(0, 1, 6)
    for (split, variant), subset in evaluated.groupby(["split", "variant"], sort=True):
        total = len(subset)
        subset = subset[subset.scoring_status.eq("scored_retrospective")]
        if subset.empty:
            continue
        y = subset[list(LABEL_COLUMNS)].to_numpy(dtype=int)
        p = subset[P_COLUMNS].to_numpy(dtype=float)
        per_label = []
        for index, mechanism in enumerate(MECHANISMS):
            positives = int(y[:, index].sum())
            row = {
                "split": split, "variant": variant, "mechanism": mechanism, "n_cases": len(subset),
                "n_total_cases": total, "n_scored_cases": len(subset), "positives": positives,
                "negatives": len(subset) - positives,
                "average_precision": float(average_precision_score(y[:, index], p[:, index])) if positives else np.nan,
                "binary_log_loss": float(log_loss(y[:, index], p[:, index], labels=[0, 1])),
                "brier_score": float(brier_score_loss(y[:, index], p[:, index])),
                "evidence_role": "in_sample" if split == "train" else ("development" if split == "validation" else "retrospective"),
            }
            metrics.append(row)
            per_label.append(row)
            bins = np.minimum(np.searchsorted(edges, p[:, index], side="right") - 1, len(edges) - 2)
            for bin_id in range(len(edges) - 1):
                selected = bins == bin_id
                count = int(selected.sum())
                calibration.append({"split": split, "variant": variant, "mechanism": mechanism,
                                    "bin_lower": edges[bin_id], "bin_upper": edges[bin_id + 1],
                                    "n": count, "positives": int(y[selected, index].sum()),
                                    "mean_probability": float(p[selected, index].mean()) if count else np.nan,
                                    "observed_fraction": float(y[selected, index].mean()) if count else np.nan})
        metrics.append({"split": split, "variant": variant, "mechanism": "macro", "n_cases": len(subset),
                        "n_total_cases": total, "n_scored_cases": len(subset), "positives": int(y.sum()),
                        "negatives": int(y.size - y.sum()),
                        **{name: float(np.nanmean([r[name] for r in per_label])) for name in ("average_precision", "binary_log_loss", "brier_score")},
                        "evidence_role": per_label[0]["evidence_role"]})
        metrics.append({"split": split, "variant": variant, "mechanism": "micro", "n_cases": len(subset),
                        "n_total_cases": total, "n_scored_cases": len(subset), "positives": int(y.sum()),
                        "negatives": int(y.size - y.sum()), "average_precision": float(average_precision_score(y.ravel(), p.ravel())),
                        "binary_log_loss": float(log_loss(y.ravel(), p.ravel(), labels=[0, 1])),
                        "brier_score": float(brier_score_loss(y.ravel(), p.ravel())), "evidence_role": per_label[0]["evidence_role"]})
    return pd.DataFrame(metrics), pd.DataFrame(calibration)


def _calibration_plots(calibration: pd.DataFrame, out: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    paths = []
    for split in ("validation", "test"):
        fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharex=True, sharey=True)
        for axis, mechanism in zip(axes.flat, MECHANISMS):
            axis.plot([0, 1], [0, 1], "--", color="gray", linewidth=1)
            for variant in VARIANTS:
                frame = calibration[(calibration.split == split) & (calibration.variant == variant) & (calibration.mechanism == mechanism) & calibration.n.gt(0)]
                axis.plot(frame.mean_probability, frame.observed_fraction, marker="o", label=variant)
                if variant == "full":
                    for row in frame.itertuples():
                        axis.annotate(f"n={row.n}", (row.mean_probability, row.observed_fraction), fontsize=7, xytext=(3, 4), textcoords="offset points")
            axis.set(title=mechanism.replace("_", " "), xlim=(-0.03, 1.03), ylim=(-0.03, 1.03), xlabel="Mean predicted probability", ylabel="Observed positive fraction")
        axes.flat[-1].axis("off")
        handles, legend_labels = axes.flat[0].get_legend_handles_labels()
        axes.flat[-1].legend(handles, legend_labels, loc="center")
        axes.flat[-1].text(0.05, 0.1, "Five fixed-width bins; empty bins omitted.\nAnnotations: full-model bin counts.\nAll counts available in calibration.csv.\nSparse bins are uncertain; no recalibration fitted.", fontsize=9)
        fig.suptitle(f"{split.capitalize()} probability calibration — synthetic, retrospective evidence", fontsize=14)
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        directory = out / "figures"
        directory.mkdir(exist_ok=True)
        path = directory / f"calibration_{split}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(str(path.relative_to(out)))
    return paths


def score_models(root: Path, out: Path, config: dict) -> dict:
    root, out = Path(root), Path(out)
    try:
        cases, labels, validation = load_prepared(root, out)
        training = json.loads((out / "training.json").read_text())
        require(sha256(out / "model.joblib") == training["model_sha256"], "Model artifact changed after training")
        artifact = joblib.load(out / "model.joblib")
        require(artifact["source_checksums"] == validation["source_checksums"], "Model/data source version mismatch")
        require(artifact["prepared_checksums"] == validation["prepared_checksums"], "Model/prepared data version mismatch")
        predictions = predict_cases(cases, artifact)
        # Labels are used only after prediction, for evaluation.
        metrics, calibration = _metrics_and_calibration(predictions, labels)
        predictions.to_parquet(out / "predictions.parquet", index=False)
        metrics.to_csv(out / "predictive_metrics.csv", index=False)
        calibration.to_csv(out / "calibration.csv", index=False)
        plot_paths = _calibration_plots(calibration, out)
        summary = {
            "passed": True, "model_version": artifact["model_version"], "prediction_rows": len(predictions),
            "unique_cases": int(predictions.stack_id.nunique()), "variants": list(VARIANTS),
            "status_counts": {str(k): int(v) for k, v in predictions.scoring_status.value_counts().items()},
            "fresh_scores_available": True, "no_refit_during_scoring": True,
            "prediction_sha256": sha256(out / "predictions.parquet"), "calibration_figures": plot_paths,
            "target_support": validation["target_support"], "coexisting_fault_cases": validation["coexisting_fault_cases"],
            "evidence": "Already inspected test cohort; retrospective synthetic evidence, not fresh prospective or production qualification evidence.",
        }
        write_json(out / "scoring.json", summary)
        return summary
    except Exception as exc:
        # A previous valid file must not masquerade as a fresh successful batch.
        for name in ("predictions.parquet", "predictive_metrics.csv", "calibration.csv"):
            path = out / name
            if path.exists():
                path.unlink()
        write_json(out / "scoring.json", {"passed": False, "fresh_scores_available": False, "error": str(exc)})
        raise
