# Does pre-test investigation justify this project?

**Current decision: the operational case and the need for ML are not established.**
This retrospective audit, added on 2026-09-16, addresses those two questions
separately. It does not change the synthetic data, target or archived model.

## 1. Required testing does not create a saving

The reference workflow tests every stack and investigates failures afterward.
The proposed workflow adds early review of existing measurements and genealogy
so the quality engineer can begin diagnosis preparation before the result.
Every stack still receives the required tests. The model therefore saves no
mandatory test runs, and v1 models no repair that rescues an already failing stack.

An operational benefit requires a specific change in subsequent work: for
example, early preparation must reduce later diagnosis effort or enable a
documented reduction in avoidable delay. These are hypotheses to verify, not
observations in this dataset. If the same investigation simply happens earlier,
there is no labor saving; if it is repeated afterward, there is extra work.
The fixed 12-hour synthetic label delay does not establish usable diagnosis
lead time, a test-duration saving, or the value of acting within that window.

The data contains no engineer actions, review durations, diagnosis durations,
queue costs, intervention effectiveness or avoided downstream defects. It can
measure which eventual failures a queue contains, but not whether acting on that
queue helps. Upstream process containment would need its own action and evidence;
it cannot be counted as a saving from this unchanged per-stack task.

## 2. Replace the arbitrary 10:1 penalty with a break-even question

Let the following quantities use the same units and evaluation period:

- `R`: average early-review cost for each flag, including correctly flagged failures.
- `B`: expected downstream cost avoided per correctly flagged failure, before
  charging early review. This includes the probability that the early action
  works and counts only effort or delay actually avoided.
- `H`: other incremental policy costs, such as implementation, operation,
  maintenance and displaced work not already counted in `R` or `B`.

Under this simplified constant-cost assumption, relative to no early review:

```text
net saving = B * TP - R * (TP + FP) - H
break even requires B / R > (TP + FP) / TP + H / (R * TP)
```

This is an accounting framework, not a fitted cost model. If later work and delay
are unchanged, `B = 0`. If identical investigation work merely moves earlier,
credit only the later work displaced and charge the earlier work: that transfer
does not itself create a net labor benefit. No review policy is worth adding
unless the resulting net saving is positive.

The former `10 * FN + FP` assumption was not grounded in these quantities. It
also hid the cost of reviewing true positives. For fixed actual failure count
`F = TP + FN`, the variable policy cost can be written:

```text
R * (TP + FP) + B * FN = R * F + (B - R) * FN + R * FP
```

Consequently, a 10:1 FN:FP penalty would require `B = 11 * R` in this simplified
model, before policy overhead. There is no evidence for that relationship. Cost
asymmetry must be derived from the action and tested over plausible ranges;
agreement on an arbitrary ratio is insufficient.

The archived F1-threshold result has 31 true positives and 205 false positives:
236 reviews. Ignoring overhead, it needs more than **7.61 review-cost equivalents
of benefit per correctly flagged failure** to break even. At the 10% review
allowance below, the model still finds 31 failures but makes 258 reviews, raising
that requirement to **8.32**. Neither number is an estimated benefit or a selected
penalty. No monetary return is established.

## 3. Compare simple rules before claiming ML is necessary

Run the reproducible audit from the repository root with:

```bash
python3 scripts/audit_review_rules.py
```

It uses Python 3.10+ and the standard library, reads the existing data and saved
coefficients, and writes `metadata/review_rule_audit.json`. Training-only median
imputation, population standardization, missing indicators and categorical
encoding reconstruct the archived logistic scores. The script checks that
average precision and the original threshold confusion matrices match on all
three splits. A tolerance of 1e-12 handles floating-point reconstruction at the
original threshold; it is not used to change the review rankings.

Six simple candidates were specified before calculating their results:

1. Rank by package warpage, largest first.
2. Rank by underfill void, largest first.
3. Rank by maximum alignment offset, largest first.
4. Rank by delamination area, largest first.
5. Rank by the largest training-distribution percentile of warpage, void and alignment.
6. Use the same largest-percentile rule with delamination added.

The last two express an OR of high-side thresholds. Delamination is included
because it is another package measurement already available to the engineer.
These are transparent inspection-rule proxies, not actual manufacturer limits.
All measurements used by these rules are present in the delivered data.

Each policy receives `floor(0.10 * number of stacks)` reviews in each split:
264 in validation and 258 in test. Equal scores use ascending stack ID solely as
a tie-breaker. Training data defines percentile reference distributions. The
candidate finding the most validation failures is selected; predefined candidate
order breaks any tie. No test labels select the rule or the review allowance.
No new ML model is fitted or chosen.

| Ranking policy | Validation failures found | Test failures found | Test false flags | Test recall |
|---|---:|---:|---:|---:|
| Package warpage | 25 | 23 | 235 | 16.79% |
| Underfill void | 24 | 29 | 229 | 21.17% |
| Alignment offset | 11 | 19 | 239 | 13.87% |
| Delamination area **(selected on validation)** | **26** | **20** | **238** | **14.60%** |
| Worst percentile of three measurements | 21 | 26 | 232 | 18.98% |
| Worst percentile of four measurements | 23 | 25 | 233 | 18.25% |
| Archived logistic model | 23 | 31 | 227 | 22.63% |

There are 126 validation failures and 137 test failures. The selected rule finds
more validation failures than the model. On test, the model finds 11 more than
that rule, an 8.03 percentage-point recall difference. A paired bootstrap of the
36 test lots (2,000 resamples, seed 20260916) gives a descriptive 95% percentile
interval of **-0.83 to +17.17 percentage points**. It keeps the original flags
fixed; it does not refit, reselect or rerank, and resampled review counts vary.
The interval includes zero and does not establish a stable advantage.

The underfill-void rule finds 29 test failures compared with the model's 31.
This is useful context for the limited advantage over a simple measurement;
it is not permission to replace the validation-selected rule using test results.
At equal review count and equal `R` and `B`, the model's incremental gross benefit
over the selected rule would be `11 * B` on this cohort; that must exceed its
additional overhead. Different review times, failure modes or action success
rates would require a richer comparison.

Important limits of this audit:

- The test set was examined in previous project audits. This is retrospective
  evidence, not a fresh confirmatory test of a new proposal.
- The 10% allowance is assumed. Equal counts imply equal effort only if reviews
  take equal time. Actual engineer procedures and staffing have not been supplied.
- A split is treated as one offline batch. Future batch sizes, dispatch, waits and
  deadlines have not been simulated or validated.
- A small candidate set cannot establish superiority over practical engineering
  rules, and no result on this simulator establishes factory performance.
- All policies use the same outcome labels. Finding an eventual failure does
  not demonstrate useful diagnosis, prevention, or a cost-saving intervention.

## 4. What must be resolved before the viva

First specify the early action and its counterfactual: what happens if the
engineer waits for the mandatory test? Record total engineer effort, diagnosis
completion time, any valuable delay avoided and displaced work under both
workflows. Estimate these in a controlled operational study or an explicitly
assumed workflow scenario; distinguish either from what the current CSVs show.
Retain no early review as an eligible policy.

Only if early action has positive net value should the group compare engineering
rules and ML at the same engineer-time budget. Freeze candidates and costs using
training/validation information and assess the comparison on fresh later cases.
If rules provide the required benefit, use them. If no early action improves on
waiting for final tests, change the problem rather than adding a classifier.
Changing to electrical-only prediction does not resolve this action-value gap.

The viva answer supported today is: **"We have demonstrated a synthetic prediction
task, not the need for an extra review or for ML. All required tests remain. We
withdrew the unsupported 10:1 cost ratio, and simple rules are competitive. We
would proceed only with evidence that an early action saves net effort or delay
and that ML adds enough value over those rules."**

Core 3 and Core 4 therefore remain unresolved. A useful human action is named
as a hypothesis under Core 2; its value is not an observed result.
