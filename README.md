# HBM3E manufacturing simulation and stack-failure triage

This is a fully synthetic dataset for a supervised manufacturing-quality
classification exercise. **One case is one assembled HBM stack. The current
target is final acceptance failure, combining assembly and electrical failure.**
Individual die measurements are inputs to that stack-level prediction.

The scenario uses public HBM3E architecture and Advanced MR-MUF descriptions as
context. It contains **no SK hynix production records** and is **not calibrated
to SK hynix process distributions or yield**. Absolute dimensions, setpoints,
noise levels, tool capabilities and defect probabilities are explicit engineering
assumptions. The evidence and its limits are recorded in
[docs/SOURCES.md](docs/SOURCES.md).

The original Kaggle file motivated this project but is not used as training data,
calibration data or as a source of measurements in this release. HBM requires
different record relationships and failure mechanisms, so the cohort was generated
from scratch.

This README describes the **delivered v1 data and task**, and frames its use for
[BYO_PROBLEM.pdf](BYO_PROBLEM.pdf). Electrical-only prediction and a richer repair
model remain proposed extensions; they have not replaced the current target.
The CSVs are checksum-verifiable, but regenerating them requires the original
generator, which is absent from this cleaned package.

## Problem statement and human decision

The exercise is to help the **on-duty HBM quality engineer** decide which newly
assembled stacks should receive additional engineering review before final testing.
A binary classifier estimates the probability of final acceptance failure from
incoming die results, assembly conditions and package measurements. Success means
identifying more eventual failures within the engineer's review capacity, with
lower weighted error cost than a simple inspection-rule baseline.

The human role, review capacity and error costs below are **exercise assumptions**,
not observations of an actual factory or implemented application behavior.

| Task element | Definition for this release |
|---|---|
| Unit of prediction | One assembled 8-high or 12-high HBM3E stack, including its separate base die. |
| Task type | Supervised binary classification used for human review triage. |
| Target | `final_test_fail`: 1 means final rejection; 0 means both assembly and electrical acceptance passed. |
| Prediction checkpoint | After assembly and package measurements are available, before final electrical testing and the recorded final acceptance verdict. |
| Human decision | The quality engineer reviews a flagged stack's measurements and genealogy and decides whether to request additional investigation or expedited testing. |
| Model output | A failure-risk score and a review flag. It does not authorize shipment, automatic scrap, or bypassing required tests. |
| Scope | One model and one review-routing decision. Die-level screening, reliability forecasting and root-cause classification are outside the primary task. |

### What the classification label means

```text
final_test_fail = 1 - final_test_pass
final_test_pass = stack_assembly_pass AND electrical_test_pass
```

| Assembly acceptance | Electrical acceptance | `final_test_fail` |
|---|---|---:|
| Pass | Pass | 0 |
| Fail | Pass | 1 |
| Pass | Fail | 1 |
| Fail | Fail | 1 |

Assembly failure covers die crack, warpage, underfill void and delamination modes.
Electrical failure covers DRAM/base electrical, TSV open/short and microbump
open/bridge modes. The label identifies whether any acceptance failure occurs;
it does not identify its cause. The simulator draws these faults probabilistically
from shared physical state and process conditions.

The modeled sequence is:

```text
Individual die electrical screening and KGD selection
  -> stack assembly and package measurements
  -> feature snapshot and human-review risk score
  -> final electrical test and recorded assembly/electrical acceptance verdicts
  -> optional sampled reliability testing
```

KGD means known-good die: a die that passed the modeled incoming screens. The
individual dies have already been electrically screened when the prediction is
made. The later test concerns the completed stack, which can contain screening
escapes or faults introduced during assembly. In v1, the formal
`stack_assembly_pass` verdict is an outcome recorded in the final-test table;
package measurements alone are available at the prediction checkpoint.

If a real workflow already knows the mechanical pass/fail verdict at that point,
the appropriate remaining-risk task is **electrical failure among
assembly-accepted stacks**. That is a separate proposed task requiring its own
cohort, label, availability definition and fitted model. It is not the task in
`stack_training.csv` or `metadata/ml_task.json` today.

### Error costs, serving and the baseline to beat

- **False positive:** an ultimately passing stack is unnecessarily flagged,
  consuming engineer time and potentially delaying its testing.
- **False negative:** an ultimately failing stack is not prioritized; the problem
  is discovered later through required testing, with late diagnosis, avoidable
  testing effort or schedule disruption. This is not automatically a defective
  shipment to a customer.
- **Illustrative asymmetry:** use 10 penalty units for a false negative and 1 for
  a false positive: `weighted_error = 10 * FN + FP`. This 10:1 ratio is an
  explicit proposal assumption for group discussion, not a measured factory cost.
  Review does not necessarily prevent a physical failure; this is a triage score,
  not a measured return-on-investment calculation.
- **Capacity and success metric:** a starting assumption is review capacity for
  10% of arriving stacks. Compare weighted error per 1,000 stacks and failure
  recall within the same review budget. Select rules and thresholds using training
  and validation data, then evaluate on untouched test data. No monetary cost
  model or capacity-constrained policy has been fitted in this release.
- **Simple rule baseline still to evaluate:** flag unusually high package warpage,
  underfill void or alignment offset, using thresholds chosen on training and
  validation data. Compare against that policy at the same review capacity.
  The saved always-pass and logistic baselines do not establish that ML beats
  these rules.
- **Serving choice:** batch scoring after a group of stacks completes inspection
  fits a shared engineer review queue. On-demand scoring could fit stacks arriving
  continuously with tight dispatch deadlines. Batch review is the initial design
  assumption; a deployed service and its latency are outside this package.

All stacks remain subject to required final testing. This preserves outcome
observation for flagged and unflagged cases. A future workflow that repairs or
withholds flagged stacks would change the observed outcomes and must record those
interventions separately.

## Start with the modeling table

Open `data/ml/stack_training.csv`: one row per assembled HBM stack, with pre-electrical-test
features, IDs, a split and the target `final_test_fail` (1 = failure, 0 = pass).
It contains **17,793 rows and 40 columns: 35 allowed predictors, four metadata
columns and one target**. Of the predictors, 34 are numeric and one is categorical.
Use the `train`, `validation` and `test` partitions already in the file. Exclude
`stack_id`, `lot_id`, `split` and `feature_available_time_utc` from predictors.
The categorical predictor is `assembly_tool_id`. Missing numerical measurements
must be imputed using training data only. `metadata/ml_task.json` supplies an explicit
feature allowlist and prediction-time definition.

Feature families include constituent-die thickness, warpage, leakage, repair
counts and TSV resistance; base-die measurements; placement accuracy; reflow,
molding and cure conditions; and package voids, delamination and warpage.
The source tables support traceability and inspection of these aggregates.

For an earlier decision, construct a separate feature snapshot and exclude fields
not yet observed. Never use `data/assembly/electrical_test.csv`, reliability outcomes, simulator
truth, or other labels to predict the same final acceptance outcome.
In particular, final-test `timing_margin_ps`, `max_pass_data_rate_gbps`, BER and
ECC results are later observations, not pre-test predictors. The current timing
margin is generated with a sign determined by electrical pass/fail, so including
it would directly leak the answer.

## Cohort and record structure

The default scenario includes 240 lots, 25 wafers per lot and 32 sampled die
locations per wafer: 6,000 wafers and 192,000 DRAM die records. Each lot is assigned
an 8-high or 12-high HBM3E product. Core dies have 3 GB capacity, producing 24 GB or
36 GB stacks. The base die is separate and does not add DRAM capacity.

The delivered package has **18 data tables plus a data dictionary**. It includes
20,068 independently simulated base dies and 17,793 assembled stacks. Of these
stacks, **16,877 pass and 916 fail final acceptance (5.15% failures)**.

| HBM3E product | DRAM capacity | Assembled stacks | Final passes | Final failures | Failure rate |
|---|---:|---:|---:|---:|---:|
| 8-high | 24 GB | 8,217 | 7,874 | 343 | 4.17% |
| 12-high | 36 GB | 9,576 | 9,003 | 573 | 5.98% |
| Total | Mixed | 17,793 | 16,877 | 916 | 5.15% |

These percentages use **assembled stacks built from screened eligible dies** as
the denominator. They are not full-wafer yield, overall fab yield, or electrical
failure rates measured in current HBM manufacturing.

The die locations are sampled without replacement from a geometric, illustrative
300 mm wafer grid with a 3 mm edge exclusion and 10 mm square pitch. This is not a
disclosed SK hynix die size. The number of sites on that assumed grid is retained
in `data/manufacturing/wafers.csv`. The sample is a modeling cohort: counts of stacks are not a full
wafer yield or factory throughput estimate.

| File | Row represents | Main links |
|---|---|---|
| `data/manufacturing/lots.csv` | One DRAM lot and its product/split | `lot_id` |
| `data/manufacturing/wafers.csv` | One wafer and sampling frame | `wafer_id`, `lot_id` |
| `data/manufacturing/recipes.csv` | One illustrative recipe/product configuration | `recipe_id` |
| `data/manufacturing/wafer_process.csv` | One wafer through one selected process module | `run_id`, `wafer_id`, `recipe_id` |
| `data/manufacturing/die_metrology.csv` | One sampled DRAM die and incoming test results | `die_id`, `wafer_id` |
| `data/manufacturing/tsv_inspection.csv` | TSV geometry/screening summary for one sampled die | `die_id` |
| `data/manufacturing/base_die.csv` | One independently simulated base die | `base_die_id`, `receiving_lot_id` |
| `data/assembly/stack_membership.csv` | One base or core die assigned to a stack | `stack_id`, `die_id` or `base_die_id` |
| `data/assembly/stack_assembly.csv` | One assembled stack and package inspection | `stack_id`, `lot_id`, `base_die_id` |
| `data/assembly/electrical_test.csv` | One final acceptance/test record | `stack_id` |
| `data/assembly/reliability_test.csv` | Sampling status and optional stress-test outcome | `stack_id` |
| `data/assembly/die_disposition.csv` | Rejected, assembled or unassigned sampled die | `die_id`, optional `stack_id` |
| `data/manufacturing/sensor_trace.csv` | One temperature sample in a selected wafer run | `run_id`, `sample_index` |
| `data/ml/ml_stack_features.csv` | A pre-final-test feature snapshot | `stack_id`, `lot_id`, `split` |
| `data/ml/ml_stack_labels.csv` | Final acceptance and reliability labels | `stack_id` |
| `data/ml/stack_training.csv` | Features joined to `final_test_fail` | `stack_id` |
| `data/simulation_truth/simulation_truth_die.csv` | Unobservable die state, for simulator audits | `die_id` |
| `data/simulation_truth/simulation_truth_stack.csv` | Unobservable stack fault probabilities and realized modes | `stack_id` |

Only eligible known-good DRAM dies and passing base dies can be assembled. Each
physical die is consumed at most once. Core layers are 1 through N; layer 0 is the
base. Stacks draw DRAM dies from multiple wafers within the same lot. This is a
declared simplifying allocation policy, not a claim about SK hynix lot mixing.
Unused eligible dies remain in inventory. Rejected dies and bases remain visible
in the tables. Stacks rejected at final acceptance are scrapped in this scenario;
post-stack rework is not simulated.

The mutually exclusive reported outcomes are:

| `defect_type` | Stacks |
|---|---:|
| `none` | 16,877 |
| `warpage` | 239 |
| `underfill_void` | 195 |
| `microbump_open_bridge` | 130 |
| `tsv_open_short` | 104 |
| `delamination` | 92 |
| `dram_electrical` | 90 |
| `die_crack` | 45 |
| `multiple` | 21 |

The eight failure categories sum to 916. These are diagnostic labels, not
additional classification targets for the primary exercise. Per-mechanism counts
in `docs/VALIDATION_REPORT.md` include overlapping faults and therefore differ
from the mutually exclusive counts above.

## How values and defects are generated

`metadata/generation_config.json` contains the effective scenario settings and seed.
The variable dictionary is in `data/data_dictionary.csv`, with explanations and
generating rules in `docs/GENERATING_MODEL.md`. Generator source references are
retained as provenance in the dictionary, but the Python utilities are omitted
from this cleaned data-only package. All stochastic coefficients are illustrative.

The generator follows product and lot conditions through wafer processing,
spatial die measurements, screening, stack allocation, packaging and final test.
Shared material, lot, wafer and tool effects create correlated records. Tool
states drift between cleaning events, and brief multi-wafer excursions occur.
Wafer effects include radial variation and occasional localized clusters.

TSV conductor resistance is based on copper resistivity and conductor geometry,
with a void correction, contact resistance and measurement noise. TSV etch depth
is the blind-via depth before thinning; conductor length after thinning follows
die thickness. Those quantities are deliberately separate. Aspect ratio is
derived from etched depth and diameter. Stack height sums all core-die thicknesses,
one gap per core die, base thickness and mold cap. The 12-high nominal core-die
thickness is 60% of the 8-high value; the absolute values are assumptions.

Seven probabilistic final failure mechanisms are represented: DRAM/base electrical,
TSV/interconnect open or short, microbump open or bridge, die crack, warpage,
underfill void and delamination. A package can have more than one mechanism.
`defect_type=multiple` reports such packages; individual indicators are retained
only in the simulator-truth table. Those indicators are synthetic ground truth,
not results of a real root-cause investigation. For multi-label research they
may serve as targets, but must never become predictors of final acceptance.

Wafer probe and TSV screening have imperfect detection. Some hidden faults escape
known-good-die screening. Final screening in this scenario perfectly reports the
realized acceptance faults; uncertainty comes from the physical fault model, not
from arbitrary label flipping. Thresholds are not a universal function of one
or two measured sensors. Mechanical rejects can remain electrically functional.

## Missingness and test conditions

- Detailed metrology is sampled on 25% of die records, with an additional 2%
  instrument dropout among sampled dies. Each record distinguishes `not_sampled`,
  `instrument_dropout` and `none`. Missing values are blank CSV cells, not zero.
- Geometric/physical states are generated for every die, even when not observed.
  The latent truth files preserve selected states exclusively for simulator audits.
- TSV continuity, wafer probe, basic thickness and package inspections use 100%
  coverage in this scenario. Those are assumptions, not manufacturer practices.
- Pressure, gas flow, etch rate and RF power are structurally unavailable for
  process stages where the corresponding recipe field is null. Do not impute
  those values as if they were missed readings from the same process.
- Reliability testing samples 20% of final-test passers. Untested or rejected
  stacks have null reliability outcomes. The 200-cycle, -40 to 125 degC synthetic
  screen is not a JEDEC qualification claim or a lifetime forecast.
- Final tests use a declared 85 degC controlled package-top case temperature and
  1.1 V scenario with 9.6 Gbps offered rate,
  a 1,024-bit bus and 10^12 tested bits. Power and thermal measurements are
  synthetic responses under that scenario; they are not product specifications.
  Thermal resistance means effective junction-to-package-top resistance under
  this controlled boundary, not a board-level junction-to-ambient measurement.
- `tsv_copper_void_pct` is a mean per-via copper-fill void-volume fraction surrogate.
  `underfill_void_pct` is void area divided by inspected underfill cross-section
  area; `delamination_area_pct` uses inspected package interface area. These
  denominators differ and the percentages must not be added together.
- Bandwidth is in **GB/s**; per-pin data rate is in **Gbps**. Nominal bandwidth is
  `9.6 * 1024 / 8 = 1228.8 GB/s`. Measured throughput includes an efficiency factor.
- Sampled traces cover temperature only, at 121 equally spaced samples per run
  for 60 runs per selected process module. Time spacing varies with run duration.
  Traces are autocorrelated process segments with mean/SD matching the recorded
  summaries, not a complete thermal recipe waveform. AR coefficient is in config.

## Split and evaluation protocol

Lots are ordered by release time and assigned approximately 70/15/15 to training,
validation and test. A 21-day embargo is inserted at the two boundaries. No source
lot, wafer, core die or receiving base lot crosses partitions. The validation
checks timestamps to ensure outcomes in one partition precede the next partition's
available features. Manufacturing equipment and recurring material settings may
appear in multiple splits: this evaluates future runs on an existing process,
not generalization to a previously unseen tool or foundry.

The data includes normal process variation, mild drift and fixed-size excursions.
The defect rate is a simulated scenario result. A pass rate or model accuracy here
does not establish a real manufacturer's quality or relative competitiveness.
Use precision/recall, average precision (PR-AUC convention documented in the example),
balanced accuracy and per-mode counts. Ordinary accuracy alone can be misleading.

`docs/BASELINE_REPORT.md` records the held-out result and
`metadata/baseline_metrics.json` contains the underlying metrics. Do not use the
test labels to select a preferred model or threshold.

### Dataset partitions and existing baseline

| Partition | Lots | Stacks | Final failures | Failure rate |
|---|---:|---:|---:|---:|
| Train | 168 | 12,564 | 653 | 5.20% |
| Validation | 36 | 2,640 | 126 | 4.77% |
| Test | 36 | 2,589 | 137 | 5.29% |

Feature snapshots span January to June 2025 in a fabricated chronology. In this
release, the final label arrives exactly **12 simulated hours** after the feature
snapshot. This gives a concrete delayed-label problem even though the simulator's
acceptance labels themselves are noise-free.

The saved baseline is logistic regression with training-only imputation,
standardization and categorical encoding. Its threshold, **0.082470**, was selected
to maximize validation F1. That is an initial classification benchmark, not the
capacity-constrained or cost-selected review policy proposed above.

| Existing model, test split | Average precision | ROC AUC | Precision | Recall | F1 | Accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Logistic regression | 0.0947 | 0.5584 | 0.1314 | 0.2263 | 0.1662 | 0.8799 |
| Always predict pass | 0.0529 | 0.5000 | Undefined | 0.0000 | 0.0000 | 0.9471 |

Average precision here is the non-interpolated precision-recall summary; its
constant-score baseline equals failure prevalence. High accuracy from predicting
every stack passes illustrates why accuracy alone is misleading.

A follow-up audit reconstructed the same fitted model's scores from the saved
coefficients and training preprocessing; the original average precision matched
on all three splits. Reusing those scores on the test split gives:

| Outcome used to evaluate the existing composite score | Failures / evaluated stacks | Prevalence | Average precision | ROC AUC |
|---|---:|---:|---:|---:|
| Combined final rejection | 137 / 2,589 | 5.29% | 0.0947 | 0.5584 |
| Assembly rejection | 79 / 2,589 | 3.05% | 0.0784 | 0.5977 |
| Electrical rejection among assembly-accepted stacks | 58 / 2,510 | 2.31% | 0.0304 | 0.5044 |

This is a diagnostic decomposition, **not three fitted models or three project
decisions**. No dedicated electrical-only model has been trained. The existing
score discriminates assembly risk better than residual electrical risk; its
electrical result does not establish that the narrower task is unlearnable.
Neither low nor high ROC AUC establishes physical realism. The original baseline
and validation reports remain archived results; the decomposition is documented
here as a later audit of the unchanged data and model.

For a future system design, monitor review load, missingness, feature availability,
product mix, score distributions and delayed per-product/lot performance. Reuse
the same aggregation and preprocessing definitions at training and serving time.
Actual human actions and their effects are not recorded in this release.

## Compliance with the BYO problem specification

Reference: [Bring Your Own Problem - Pre-Work Brief](BYO_PROBLEM.pdf), Sections
2A-2D and 4-5, PDF pages 3-7. It requires **all five core items**, **at least four
of six enrichment items**, and **group-owned framing**. Its pages 2 and 6 explicitly
allow synthetic data and say realism is not graded. A working pipeline is an
optional stretch; the assessed work is problem framing, system design and the viva.

**Status key:** "Met - data" means supported by delivered records; "Met - framing"
means the exercise defines the required decision or scenario, not that a service
has been built; "Pending" identifies evidence or group action still needed.

| Requirement | Status | Evidence, interpretation or remaining action |
|---|---|---|
| Core 1: supervised classification with a definable label (2A, p. 3) | Met - data | One row per stack; binary `final_test_fail`; explicit assembly/electrical acceptance identity; labels for all 17,793 cases. |
| Core 2: a named human acts on flagged cases (2A, pp. 3-4) | Met - framing | The on-duty HBM quality engineer decides whether to request extra investigation or expedited testing. The model supplies a review flag and retains human control. |
| Core 3: asymmetric error costs (2A, p. 4) | Met - framing | Missed failures imply late diagnosis and disruption; false flags consume review time. Proposed FN:FP penalties are 10:1, explicitly assumed and subject to group agreement. |
| Core 4: genuinely needs ML rather than a few rules (2C, p. 4) | Pending | Multiple interacting process conditions and imperfect incoming screens motivate the question, but no comparison against practical warpage/void/alignment rules has been run. Low AUC or stochastic labels alone do not establish the need for ML. |
| Core 5: one model, one decision (2D, p. 5) | Met - framing | One stack-failure classifier routes cases to human review. Extra source tables and diagnostic outcome breakdowns do not introduce additional deployed models. |
| Enrichment 1: class imbalance (2B, p. 4) | Met - data | 916 of 17,793 stacks fail final acceptance (5.15%). Always predicting pass gives 94.85% overall accuracy while finding no failures. |
| Enrichment 2: late, noisy, proxy or selectively observed label (2B, p. 4) | Met - data | Primary labels arrive 12 simulated hours after features. This satisfies the delayed-label alternative; primary labels are complete and noise-free, not claimed to be noisy operator diagnoses. |
| Enrichment 3: time dimension (2B, p. 4) | Met - data | Timestamped cases and later outcomes; ordered lot splits with 21-day embargoes. The task remains per-stack classification, not time-series forecasting. |
| Enrichment 4: leakage trap and/or train/serve skew (2B, p. 4) | Met - data | Final-test timing margins, BER and simulator truth would leak outcomes. Random row splits could mix shared lots/wafers. The feature allowlist and group/time split address these traps; aggregate definitions must match at serving. |
| Enrichment 5: feedback loop and/or genuine serving choice (2B, p. 4) | Met - framing | Batch review queues versus on-demand pre-test scoring depend on engineer capacity and dispatch deadlines. Serving choice satisfies this line; an intervention feedback loop is not implemented. |
| Enrichment 6: plausible data/concept drift (2B, p. 4) | Met - data and framing | Tool age, maintenance, excursions and material effects create changing inputs. A later recipe or screening change could alter the feature-to-failure relationship; that concept-drift scenario is not implemented. |
| Framing belongs to the group, rather than an assigned Kaggle/tutorial task (2D, p. 5; Section 5, p. 7) | Pending group confirmation | The Kaggle source was only topic inspiration. This is an LLM-assisted framing proposal; group members must choose, challenge and defend the target, human action, metric and baseline themselves. This README cannot certify that ownership. |
| Other disqualifiers (2D, pp. 4-5) | Avoided in the framing | The proposed system is supervised, supports a human, has asymmetric error assumptions and makes one decision. It is not a clustering task, chatbot or fully automated decision system. |
| Do not leave both drift/monitoring and leakage/skew blank (2D, p. 5) | Met - framing and data | Both have concrete examples above and a proposed monitoring approach. |
| Data plan and optional pipeline (Sections 1 and 4, pp. 1-2, 6) | Data available | Synthetic CSVs, a dictionary, feature/label views and archived baselines are available. A smaller group-disjoint cohort could support the exercise if needed. Real fab access and a built serving pipeline are not required by the brief. |
| Half-page group proposal and mentor approval (Section 4, p. 6) | Pending group action | The problem statement, costs, data plan and checklist here supply the content. Submit a half-page version together before ML Systems Week; submission and mentor sign-off are not evidenced by this repository. |

**Assessment:** four of the five core items are defined; the "needs ML" gate
remains unverified. All six enrichment lines have a supported data or framing
argument, including delayed labels and a serving choice rather than forced label
noise or feedback effects. Group ownership and mentor approval remain separate
requirements. This is a compliance self-assessment, not a claim of full approval.

## Cleaned package layout

This copy is organized for data analysis rather than regeneration:

```text
data/manufacturing/   Lot, wafer, process, metrology and TSV records
data/assembly/        Stack genealogy, assembly, final test and reliability records
data/ml/              Modeling features, labels and the joined training table
data/simulation_truth/ Latent simulator state for audits only
docs/                 Model, source, validation and baseline reports
metadata/             Configuration, manifests and machine-readable results
```

The Python generator, validation and training utilities and their dependency file
were removed during cleanup. `metadata/manifest.json` retains original row counts,
column counts and CSV checksums. The initial simulation seed was 20260914.
The saved reproducibility checks describe an earlier run with that original code;
the seed and preserved equations alone do not make this copy self-regenerating.

## Scope of realism

This release represents selected late-fabrication and wafer-level packaging
modules plus HBM stack assembly, not hundreds of upstream DRAM operations. Fab
cycle time, dispatching, queueing, resource capacity, cost, detailed material
chemistry, individual TSV nets, electrical circuit simulation, GPU/interposer
integration and post-stack rework are outside the model. `assembly_tool_id`
denotes a synthetic assembly-line group with multiple processing stations; its
timestamps do not represent a single-resource occupancy schedule. Functional
TSV counts/pitches and wafer-grid pitch are assumed architecture settings.

Current limitations relevant to interpretation are:

- Incoming `repair_count` and screening exist, but explicit spare-row/column
  budgets, TSV redundancy and post-package repair do not. Inherited latent faults
  raise stack-failure probabilities without fully distinguishing repairable
  defects from fatal unrepaired faults.
- Detailed metrology is selected independently per die with random instrument
  dropout. There is no nested wafer/site sampling plan or gauge-bias model.
- Spatial structure consists of radial and local-cluster effects on 32 sampled
  sites per wafer. This is not a full-wafer defect-map benchmark.
- Physical height accounting is consistent, with recorded heights from 604.35
  to 625.63 um. The 8-high and 12-high mean heights are approximately 617.63 and
  613.31 um; exact equality of product mean heights is not enforced.
- Current public evidence does not calibrate the simulated final electrical
  failure rate. Company-level yield claims and research bit-error rates have
  different populations or denominators and cannot supply that calibration.
- Baselines assess predictive usefulness on this simulation. Physical constraints,
  causal semantics and empirical comparison are separate tests of realism.

Potential extensions include an electrical-only task among assembly-accepted
stacks, explicit fault/repair semantics, causal speed-margin modeling, clustered
metrology, additional recipes and real-data parameter calibration. Each needs its
own assumptions and validation. None is required merely to add more features for
the BYO exercise, and none should be presented as already implemented in v1.
