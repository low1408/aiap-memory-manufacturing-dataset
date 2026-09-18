#!/usr/bin/env python3
"""Compare simple review rankings with the archived model; standard library only.

Run from any directory with Python 3.10+. This is a retrospective synthetic-data
audit, not a factory rule qualification or a new model-training utility.
"""

import bisect
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import statistics


ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS = (
    "package_warpage_um",
    "underfill_void_pct",
    "max_alignment_offset_um",
    "delamination_area_pct",
)


def average_precision(labels, scores):
    """Non-interpolated AP, grouping exact score ties."""
    order = sorted(range(len(labels)), key=lambda i: -scores[i])
    positives = sum(labels)
    found = seen = 0
    area = 0.0
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and scores[order[end]] == scores[order[start]]:
            end += 1
        added = sum(labels[i] for i in order[start:end])
        found += added
        seen += end - start
        area += added * found / seen
        start = end
    return area / positives if positives else None


def selected_indices(rows, scores):
    # Equal capacity for every ranking; IDs only break exact score ties.
    capacity = len(rows) // 10
    return set(sorted(range(len(rows)),
                      key=lambda i: (-scores[i], rows[i]["stack_id"]))[:capacity])


def metrics(rows, scores):
    selected = selected_indices(rows, scores)
    labels = [int(row["final_test_fail"]) for row in rows]
    tp = sum(labels[i] for i in selected)
    fp = len(selected) - tp
    failures = sum(labels)
    return {
        "rows": len(rows), "failures": failures,
        "reviews": len(selected), "tp": tp, "fp": fp,
        "fn": failures - tp, "tn": len(rows) - failures - fp,
        "precision": tp / len(selected), "recall": tp / failures,
        "average_precision": average_precision(labels, scores),
        "break_even_benefit_per_review_cost_excluding_overhead":
            len(selected) / tp if tp else None,
    }


def quantile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)


def main():
    task = json.loads((ROOT / "metadata/ml_task.json").read_text())
    saved = json.loads((ROOT / "metadata/baseline_metrics.json").read_text())
    with (ROOT / "data/ml/stack_training.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len({row["stack_id"] for row in rows}) == len(rows)
    splits = {split: [row for row in rows if row["split"] == split]
              for split in ("train", "validation", "test")}
    assert sum(map(len, splits.values())) == len(rows)
    for first, second in (("train", "validation"), ("train", "test"),
                          ("validation", "test")):
        assert not ({row["lot_id"] for row in splits[first]} &
                    {row["lot_id"] for row in splits[second]})

    # Reconstruct archived preprocessing using training observations only.
    preprocessing = {}
    for name in task["numeric_predictors"]:
        observed = [float(row[name]) for row in splits["train"] if row[name]]
        median = statistics.median(observed)
        imputed = [float(row[name]) if row[name] else median
                   for row in splits["train"]]
        preprocessing[name] = (median, statistics.fmean(imputed),
                               statistics.pstdev(imputed) or 1.0)

    def model_score(row):
        logit = saved["intercept"]
        for coefficient in saved["coefficients"]:
            name = coefficient["feature"]
            if name.endswith("__missing"):
                value = float(not row[name.removesuffix("__missing")])
            elif "=" in name:
                field, category = name.split("=", 1)
                value = float(row[field] == category)
            else:
                median, mean, sd = preprocessing[name]
                value = ((float(row[name]) if row[name] else median) - mean) / sd
            logit += coefficient["coefficient"] * value
        return 1.0 / (1.0 + math.exp(-logit))

    reference = {}
    for name in MEASUREMENTS:
        assert all(row[name] for row in rows), f"Missing rule input: {name}"
        reference[name] = sorted(float(row[name]) for row in splits["train"])

    def percentile(name, value):
        values = reference[name]
        return (bisect.bisect_left(values, value) +
                bisect.bisect_right(values, value)) / (2 * len(values))

    # Six candidates fixed before examining their validation/test performance.
    # A worst-percentile score is an OR of high-side measurement thresholds.
    rule_names = list(MEASUREMENTS) + ["worst_percentile_3", "worst_percentile_4"]
    scores = {}
    reconstruction = {}
    for split, part in splits.items():
        score = {name: [float(row[name]) for row in part] for name in MEASUREMENTS}
        for count in (3, 4):
            score[f"worst_percentile_{count}"] = [
                max(percentile(name, float(row[name])) for name in MEASUREMENTS[:count])
                for row in part
            ]
        score["archived_logistic"] = [model_score(row) for row in part]
        scores[split] = score
        labels = [int(row["final_test_fail"]) for row in part]
        ap = average_precision(labels, score["archived_logistic"])
        original = saved["splits"][split]["logistic_regression"]
        assert math.isclose(ap, original["average_precision"], abs_tol=1e-12)
        # The archived threshold can land on a training-reconstruction rounding
        # boundary. Include scores within 1e-12 solely for this recovery check.
        predictions = [s >= saved["selected_threshold"] or
                       math.isclose(s, saved["selected_threshold"], rel_tol=0, abs_tol=1e-12)
                       for s in score["archived_logistic"]]
        tp = sum(y for y, flag in zip(labels, predictions) if flag)
        fp = sum(predictions) - tp
        recovered = {"tp": tp, "fp": fp, "fn": sum(labels) - tp,
                     "tn": len(labels) - sum(labels) - fp}
        assert recovered == original["confusion_matrix"]
        reconstruction[split] = {"average_precision": ap, "confusion_matrix": recovered}

    # Validation selects the rule; test never selects a candidate or budget.
    validation_results = {name: metrics(splits["validation"], scores["validation"][name])
                          for name in rule_names}
    selected_rule = max(rule_names, key=lambda name: validation_results[name]["tp"])
    results = {split: {name: metrics(part, scores[split][name])
                       for name in rule_names + ["archived_logistic"]}
               for split, part in splits.items()}

    test_rows = splits["test"]
    rule_selected = selected_indices(test_rows, scores["test"][selected_rule])
    model_selected = selected_indices(test_rows, scores["test"]["archived_logistic"])
    by_lot = {}
    for i, row in enumerate(test_rows):
        counts = by_lot.setdefault(row["lot_id"], [0, 0])
        outcome = int(row["final_test_fail"])
        counts[0] += outcome * (int(i in model_selected) - int(i in rule_selected))
        counts[1] += outcome
    rng = random.Random(20260916)
    lot_counts = list(by_lot.values())
    differences = []
    for _ in range(2000):
        sample = rng.choices(lot_counts, k=len(lot_counts))
        failures = sum(count[1] for count in sample)
        if failures:
            differences.append(sum(count[0] for count in sample) / failures)

    inputs = ("data/ml/stack_training.csv", "metadata/ml_task.json",
              "metadata/baseline_metrics.json")
    output = {
        "status": "Retrospective synthetic-data audit; no measured operational savings",
        "capacity": "floor(10% of each split); split treated as one offline batch",
        "rule_candidates_in_tie_break_order": rule_names,
        "rule_definition": "Single high-side measurements or maximum training empirical percentile; first 3 exclude delamination",
        "selection": "Most validation failures in capacity; candidate order breaks ties",
        "score_ties": "Ascending stack_id, used only to break exact score ties",
        "selected_rule": selected_rule,
        "reconstruction_checks": reconstruction,
        "results": results,
        "test_queue_comparison": {
            "both_flagged": len(rule_selected & model_selected),
            "model_only_failures": sum(int(test_rows[i]["final_test_fail"])
                                       for i in model_selected - rule_selected),
            "rule_only_failures": sum(int(test_rows[i]["final_test_fail"])
                                      for i in rule_selected - model_selected),
        },
        "paired_lot_bootstrap": {
            "seed": 20260916, "replicates": 2000, "test_lots": len(by_lot),
            "statistic": "Logistic recall minus selected-rule recall",
            "interval_95_percentile": [quantile(differences, .025), quantile(differences, .975)],
            "limitation": "Fixed original test flags; no refitting, reselection or reranking; resampled review counts vary",
        },
        "limitations": [
            "10% is an assumed comparison budget, not measured engineer capacity.",
            "The test set has already been examined in earlier project audits; this is not a fresh confirmatory holdout.",
            "Simple measurement rules are proxies, not actual factory specification limits or validated engineer procedures.",
            "A whole split is not a production arrival batch; this does not validate online dispatch or lead time.",
            "No review duration, action effectiveness, diagnosis time, cost or intervention outcome is observed.",
        ],
        "input_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                         for name in inputs},
    }
    target = ROOT / "metadata/review_rule_audit.json"
    target.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(f"Selected rule: {selected_rule}")
    for split in ("validation", "test"):
        print(f"{split}: {json.dumps(results[split])}")
    print(f"Paired lot bootstrap: {output['paired_lot_bootstrap']}")
    print(f"Saved {target}")


if __name__ == "__main__":
    main()
