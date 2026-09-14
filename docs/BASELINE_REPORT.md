# Synthetic HBM stack classification baseline

This benchmark predicts `final_test_fail`: 1 means failed final acceptance (assembly or electrical) and 0 means passed. The prediction checkpoint is after assembly and package inspection, before final electrical testing. These results describe this simulation and do not estimate SK hynix fab performance.

This is the preserved result from the original training utility, which was removed
from the cleaned data-only package. Unrounded results remain in
`metadata/baseline_metrics.json`.

## Join and split protocol

Join on the unique stack key, using only the selected label from the labels file:

```python
features = pd.read_csv("data/ml/ml_stack_features.csv")
labels = pd.read_csv("data/ml/ml_stack_labels.csv")
data = features.merge(labels[["stack_id", "final_test_fail"]],
                      on="stack_id", validate="one_to_one")
train = data.loc[data["split"] == "train"]
validation = data.loc[data["split"] == "validation"]
test = data.loc[data["split"] == "test"]
```

Ordered lots 70/15/15, 21-day embargo at boundaries. No die/wafer/lot crosses split. Fit transformations on train only.

The example checks that label and feature splits match, lots do not cross splits, and labels from an earlier split are available before the next split begins. Use only the predictor allowlist in `metadata/ml_task.json`. IDs, split flags, timestamps, final test measurements, other outcome labels, disposition and simulator truth are excluded.

## Method

Numeric medians, numeric means and standard deviations, missing-value indicator selection, and categorical vocabularies are fitted on the training split only. Numeric values are median-imputed and standardized. Columns with missing training observations receive a missingness indicator. `assembly_tool_id` uses one-hot encoding with the first training category as reference. Previously unseen categories use the reference encoding.

Logistic regression minimizes mean log loss plus `0.001 / 2 × sum(coefficient²)`, excluding the intercept from regularization. No class weighting or resampling is used. The regularization strength is fixed. The classification threshold maximizes validation F1 over distinct predicted probabilities, with a higher threshold breaking exact ties. The model is then evaluated on test without refitting or further threshold selection.

Selected validation threshold: **0.082470**. Optimizer converged in 5 iterations.

Average precision (AP) is the non-interpolated sum of precision times recall increment. ROC AUC uses grouped equal-score thresholds, so tied positive/negative pairs receive half credit. AP differs from trapezoidal PR AUC. For an uninformative constant score, AP equals failure prevalence. Always-pass predictions have undefined precision, shown as n/a.

## Results

| Split | Model | Stacks | Failures | Prevalence | AP | ROC AUC | Precision | Recall | F1 | Balanced accuracy | Accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | Logistic | 12,564 | 653 | 0.0520 | 0.0917 | 0.6180 | 0.1140 | 0.1700 | 0.1364 | 0.5488 | 0.8882 |
| train | Always pass | 12,564 | 653 | 0.0520 | 0.0520 | 0.5000 | n/a | 0.0000 | 0.0000 | 0.5000 | 0.9480 |
| validation | Logistic | 2,640 | 126 | 0.0477 | 0.0949 | 0.5687 | 0.0987 | 0.1825 | 0.1281 | 0.5495 | 0.8814 |
| validation | Always pass | 2,640 | 126 | 0.0477 | 0.0477 | 0.5000 | n/a | 0.0000 | 0.0000 | 0.5000 | 0.9523 |
| test | Logistic | 2,589 | 137 | 0.0529 | 0.0947 | 0.5584 | 0.1314 | 0.2263 | 0.1662 | 0.5713 | 0.8799 |
| test | Always pass | 2,589 | 137 | 0.0529 | 0.0529 | 0.5000 | n/a | 0.0000 | 0.0000 | 0.5000 | 0.9471 |

Test confusion matrix (positive means failure):

| Actual | Predicted pass | Predicted failure |
|---|---:|---:|
| Pass | 2,247 | 205 |
| Failure | 106 | 31 |

## Largest fitted coefficients

Coefficients are conditional associations learned from the synthetic training data. A numeric coefficient corresponds to one training standard deviation. Missing indicators and one-hot coefficients represent a change from 0 to 1. Correlated features, sampling and regularization affect their sizes and signs. They are not estimates of manufacturing causal effects or feature importance in a real fab.

| Feature | Coefficient (log odds of failure) |
|---|---:|
| `package_warpage_um` | +0.2198 |
| `underfill_void_pct` | +0.1542 |
| `assembly_tool_id=ASSEMBLY_T06` | +0.1511 |
| `core_thickness_std_um` | +0.1144 |
| `core_leakage_mean_ua` | +0.1114 |
| `stack_height_um` | -0.0993 |
| `core_tsv_resistance_max_mohm` | +0.0972 |
| `inter_die_gap_mean_um` | -0.0915 |
| `molding_vacuum_absolute_kpa` | +0.0740 |
| `core_tsv_resistance_mean_mohm` | +0.0666 |
| `assembly_tool_id=ASSEMBLY_T02` | +0.0647 |
| `max_alignment_offset_um` | +0.0631 |

All fitted coefficients, input checksums, optimizer diagnostics and unrounded metrics are in `metadata/baseline_metrics.json`. No serialized model or reusable fitted preprocessing object is saved.

This single temporal holdout measures performance on later simulated lots under the same generator. It does not establish transfer to a different generator, process recipe, fab or manufacturer. F1 threshold selection assigns no monetary cost to missed failures or rejected good stacks. Stacks within a lot share conditions, so row-level independence should not be assumed when estimating uncertainty.
