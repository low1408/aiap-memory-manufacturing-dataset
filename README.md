# HBM3E failure-mechanism prediction for diagnostic test selection

**Main proposal:** predict likely HBM failure mechanisms from manufacturing
measurements and initial acceptance-test observations, helping the quality
engineer select additional diagnostic tests with lower investigation cost and
comparable diagnostic coverage. One case is one assembled HBM stack that has
**already failed required acceptance testing**.

The proposed model is one multi-label classifier with seven probability outputs.
It has not been trained or evaluated. Diagnostic test savings, diagnostic accuracy
and a need for ML have not been demonstrated. The delivered v1 package remains a
synthetic dataset and a binary acceptance-failure benchmark; its files, task
metadata and archived results have not been converted to the proposed task.
See [Delivered v1 binary benchmark](#delivered-v1-binary-benchmark).

The scenario uses public HBM3E architecture and Advanced MR-MUF descriptions as
context. It contains **no SK hynix production records** and is **not calibrated
to SK hynix process distributions or yield**. Absolute dimensions, setpoints,
noise levels, tool capabilities and defect probabilities are explicit engineering
assumptions. The evidence and its limits are recorded in
[docs/SOURCES.md](docs/SOURCES.md).

The original Kaggle file motivated this project but is not used as training data,
calibration data or as a source of measurements in this release. HBM requires
different record relationships and failure mechanisms, so the cohort was generated
from scratch. This README frames the new proposal for
[BYO_PROBLEM.pdf](BYO_PROBLEM.pdf), while retaining the delivered v1 data description.
The CSVs are checksum-verifiable, but regenerating them requires the original
generator, which is absent from this cleaned package.

## Problem statement and human decision

Existing diagnostic techniques can identify faults. The question is whether
predictions help an engineer choose a more efficient investigation than the
existing diagnostic workflow. All stacks still undergo required acceptance
testing. The proposed savings concern **additional diagnosis of rejected stacks**;
predicting a defect does not itself improve manufacturing yield or repair a stack.

| Task element | Proposed diagnostic-selection task |
|---|---|
| Unit of prediction | One assembled 8-high or 12-high HBM3E stack, including its separate base die, after acceptance failure. |
| Task type | Supervised multi-label classification: several failure mechanisms can coexist. This is not multiple regression. |
| Target | Seven binary mechanism indicators, used only as training/evaluation labels. |
| Prediction checkpoint | Initial acceptance-test observations are available; additional diagnostic selection and confirmed diagnostic findings are still to follow. |
| Human decision | The on-duty HBM quality engineer selects the additional diagnostic investigation to perform. |
| Model output | Seven estimated mechanism probabilities and their ranking, supporting one investigation-selection decision. |
| Authority | The engineer interprets available evidence, chooses diagnostics and follows the investigation's confirmation and stopping rules. Scores do not authorize shipment, automatic scrap or omission of required acceptance tests. |
| Scope | One model supporting diagnostic selection. Process root-cause discovery, repair, process control and reliability forecasting are outside this proposal. |

The proposed workflow is:

```text
Required acceptance testing
  -> rejected stack
  -> mechanism predictions from manufacturing and initial test observations
  -> quality engineer selects additional diagnostic tests
  -> confirmed findings and investigation effort recorded
```

The engineer can continue or expand an inconclusive investigation. A high-ranked
mechanism is a hypothesis to check. For example, predicting a microbump open does
not establish which manufacturing condition caused that open. Probabilities need
not sum to one because multiple faults can be present.

## Proposed cohort, labels and inputs

### Rejected-stack cohort and seven targets

The proposed cohort contains **916 rejected stacks** from the delivered 17,793
assembled stacks. The 16,877 acceptance passers are outside this diagnostic task;
`final_test_fail` is an eligibility condition, not its prediction target. Retain
the original lot/time partitions rather than creating a random row split:

| Partition | Rejected stacks for the proposed task |
|---|---:|
| Train | 653 |
| Validation | 126 |
| Test | 137 |
| Total | 916 |

Join the records by `stack_id`. The seven realized indicators in
`data/simulation_truth/simulation_truth_stack.csv` are available as **synthetic
reference labels only**. Their counts below use rejected stacks as the denominator;
21 rejected stacks contain multiple mechanisms, so the percentages need not sum
to 100%.

| Failure mechanism | Proposed target column | Positive stacks / 916 | Share of rejected stacks |
|---|---|---:|---:|
| DRAM/base electrical failure | `fault_dram_electrical` | 97 | 10.59% |
| TSV open/short | `fault_tsv_open_short` | 108 | 11.79% |
| Microbump open/bridge | `fault_microbump_open_bridge` | 137 | 14.96% |
| Die crack | `fault_die_crack` | 47 | 5.13% |
| Warpage | `fault_warpage` | 247 | 26.97% |
| Underfill void | `fault_underfill_void` | 206 | 22.49% |
| Delamination | `fault_delamination` | 96 | 10.48% |

The OR of these seven indicators equals `final_test_fail` in the delivered data.
All-zero label vectors therefore belong to acceptance passers and are outside
this cohort. The single `defect_type=multiple` category does not identify which
mechanisms coexist and cannot replace the seven individual indicators.

In an operational study, reference labels would come from confirmed diagnostic
findings. Here, the labels come from the simulator's fault draws. They are not
real diagnostic observations, confirmed process root causes, or evidence that a
particular test can detect a mechanism. No multi-label modeling table, fitted
model or new machine-readable task specification has been delivered.

### Information available at diagnostic selection

Start with the existing 35 manufacturing/package predictors and add only initial
acceptance-test observations known before the engineer selects further tests.
The following is a **proposed input boundary requiring an availability and realism
audit**, not a newly implemented feature allowlist:

| Input group | Candidate fields / role |
|---|---|
| Manufacturing and package measurements | Constituent-die aggregates, base-die measurements, assembly tool, placement, reflow, molding, cure and inspected package measurements from the v1 feature snapshot. |
| Acceptance verdicts | `stack_assembly_pass` and `electrical_test_pass`; overall acceptance failure selects the cohort. |
| Error and interconnect observations | `uncorrected_error_count`, `bit_error_rate`, `ecc_corrected_errors`, `detected_interconnect_failures`. |
| Speed and timing observations | `max_pass_data_rate_gbps`, `measured_bandwidth_gb_s`, `timing_margin_ps`. |
| Power and thermal observations | `power_consumption_w`, `thermal_resistance_c_w`, if actually measured in initial acceptance testing. |
| Initial test conditions | `test_temperature_c`, `test_voltage_v`, `test_duration_sec`, `offered_data_rate_gbps`, `bus_width_bits`, `nominal_peak_bandwidth_gb_s`, `tested_bit_count` and `test_program_id`. Constants or redundant fields need not become fitted predictors. |

The v1 pre-test snapshot is in `data/ml/ml_stack_features.csv`; initial test
records are in `data/assembly/electrical_test.csv`. Use unique-key joins and retain
lot/split information for partitioning. IDs, split markers and timestamps are
join/audit metadata, not predictive features. Imputation, scaling and categorical
encoding must be fitted using training records only.

**Exclude** `defect_type`, `defect_stage`, `defect_severity`, `final_disposition`,
later diagnostic findings, reliability outcomes, all `fault_*` target columns,
latent states and simulator `p_*` probabilities from predictors. Extract only the
seven target columns plus the join key from the truth table into a separate label
view; never merge the full truth table into model inputs.

The original ban on final-test inputs in `metadata/ml_task.json` applies to the
**v1 pre-test binary task**. At the new decision point, completed initial test
measurements may be legitimate inputs. That file still describes v1 and must not
be read as an implemented specification for this proposal. The initial test file
mixes measurements and outcome annotations, so a whole-table feature import would
be inappropriate for either task.

Some measurements were generated directly from simulated outcomes. For example,
`timing_margin_ps` has a sign determined by electrical pass/fail. Its availability
after acceptance does not make it a realistic diagnostic signal. Review the
measurement-generation rules and compare models with and without such fields
before interpreting any mechanism-prediction result.

### Chronology that still needs to be established

V1 stores acceptance observations and defect annotations in the same test record.
It provides no separate timestamp for a later diagnostic confirmation. The new
workflow assumes a distinct acceptance event followed by diagnostic selection and
confirmed findings; separate file columns do not prove that chronology.

The existing `feature_available_time_utc` is the pre-acceptance snapshot time.
Its 12-hour gap to the v1 final label ends **before** the proposed diagnostic
selection. It cannot demonstrate delayed mechanism labels for this new task.
A future operational dataset must record initial-result availability, selection,
tests actually performed, diagnostic completion and the labels each test supports.

## Where diagnostic test savings could come from

The reference is the engineer's existing diagnostic workflow on rejected stacks,
including its inspection rules, ordering and stopping criteria. Do not assume that
engineers currently run every possible procedure. The proposed model would rank
mechanisms to help select the next useful investigation within that workflow.

Ranking can reduce time only when it changes the investigation path or a measured
operational delay. Fewer tests can be claimed only when some procedures are
avoided under a justified completeness requirement. If every procedure still runs,
changing their order does not by itself reduce their count or summed execution
time. A mechanism probability alone does not specify which diagnostic test is
most informative; that also depends on test coverage, cost and existing evidence.

```text
Net saving = existing diagnostic-workflow cost
             - model-assisted diagnostic-workflow cost
             - incremental model overhead
```

Compare the same cases and diagnostic completeness requirement. Workflow costs
include diagnostic procedures, equipment and engineer time, repeat investigations
and the consequences of incorrect recommendations. Count both successful and
unsuccessful investigations. Model overhead includes development, operation and
maintenance over a stated evaluation period. Avoid counting the same delay or
labor cost twice. Required acceptance-test costs common to both workflows cancel.
No numerical savings or monetary costs have been estimated for this proposal.

Before estimating savings, define:

- A diagnostic-test catalogue mapping each procedure to mechanisms it can confirm
  or exclude, its detection limits, possible inconclusive results and dependencies.
- Per-procedure duration, equipment/engineer cost and relevant scheduling effects.
- The existing engineering rules and diagnostic order, including their use of
  initial acceptance observations.
- Confirmation, fallback and stopping rules, with a stated requirement for
  diagnostic completeness that includes coexisting faults.
- Fully investigated reference cases against which a reduced workflow can be
  evaluated, including unresolved cases and any missed mechanisms.

Confirming a TSV defect does not rule out a coexisting microbump defect. Stopping
at the first positive diagnostic result is not automatically a complete diagnosis.
These procedure definitions and investigation records are absent from v1; its
fixed final-test duration is not a catalogue of additional diagnostic costs.

Adaptive testing is an established semiconductor-test direction: Advantest
[describes using device data to adapt test flows and reduce test time](https://www.advantest.com/en/semiconductor-basics/automated-test-equipment/).
That supports the general concept, not the effectiveness of this HBM model or a
claim that required acceptance tests can be omitted.

### Error costs and the former 10:1 assumption

An incorrect high-ranked mechanism can lead to an unnecessary investigation.
An omitted or low-ranked mechanism can delay diagnosis, require repeat work or
leave a coexisting fault unresolved. A low rank is not itself proof that a fault
will be missed: the engineer's fallback and stopping rules determine that outcome.

The relative consequences depend on the mechanism, diagnostic procedure and
investigation policy. They need not be constant across cases. No fixed FN:FP
penalty is justified yet; the earlier 10:1 proposal remains withdrawn. A yield
target does not determine that ratio. These are already rejected stacks, so a
missed diagnostic recommendation is not automatically an escaped shipment.
Core 3 remains pending until a defensible asymmetry is specified and evaluated.

### What the model must add beyond inspection rules

Compare existing engineering rules and diagnostic ordering against model-assisted
selection using **the same available information, procedure catalogue and
completeness requirement**. Include simple warpage/void/alignment/delamination
rules and a fixed diagnostic order as transparent experimental baselines. Select
any thresholds or ordering using training/validation information only.

Already-observed warpage, void or delamination measurements may make some
mechanism recommendations redundant. Check whether the model adds useful
information beyond those observations, rather than crediting it for repeating
an inspection finding. Combinations of measurements are a hypothesis for added
value, not evidence of it. The earlier binary rule comparison belongs to v1 and
neither validates nor disproves this diagnostic-selection task.

Retain ML only if it reduces diagnostic time or cost at the agreed completeness
requirement relative to those baselines, after overhead. If rules suffice, use
rules. Core 4 remains pending until this comparison is performed.

## Delivered v1 data: cohort and record structure

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

The eight failure categories sum to 916. These are mutually exclusive v1
outcome summaries, not the proposed multi-label target vectors. Per-mechanism
counts in the archived v1 [validation report](docs/VALIDATION_REPORT.md) include
overlapping faults and therefore differ from the mutually exclusive counts above.

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
not results of a real root-cause investigation. The new proposal uses the seven
realized indicators as targets only. Neither those indicators nor the latent
probabilities may become predictors of acceptance failure or diagnostic mechanisms.

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
  Latent states remain for simulator audits; only the seven realized stack-fault
  indicators are proposed as multi-label targets, never predictors.
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

## Proposed evaluation and monitoring

Preserve the original lot/time split and its 21-day embargoes when selecting the
916 rejected stacks. No source lot, wafer, core die or receiving base lot crosses
partitions. Fit transformations on training records only; choose model settings,
calibration, ranking thresholds and diagnostic policies on training/validation
information. The v1 timestamp checks concern pre-test features and acceptance
labels; a future diagnostic dataset needs its own checks that training labels
are available before later prediction events.

Manufacturing equipment and recurring material settings may appear in multiple
splits. This evaluates later runs of the same simulated process, not a new fab
or previously unseen equipment. The test cohort has already been examined in
v1 audits. Treat further analysis of it as retrospective and require fresh later
cases for confirmatory performance or savings claims.

| Evaluation level | Proposed measures |
|---|---|
| Mechanism prediction | Per-mechanism precision, recall and average precision, with positive/negative support; probability calibration; macro and micro summaries alongside individual results. |
| Ranked recommendations | Fraction of confirmed active mechanisms covered by the highest-ranked `k` recommendations; report cases where a coexisting mechanism is omitted. Choose `k` on validation rather than test. |
| Diagnostic workflow | Total diagnostic time and cost at a stated, unchanged completeness requirement; tests performed, confirmed mechanisms, unresolved cases and missed coexisting faults. Include wrong recommendations and fallback work. |
| Incremental value | Compare with existing engineering rules and a fixed diagnostic order on the same cases, with the same information and permitted procedures, after model overhead. |

Recommendation coverage is not the same as diagnostic-test coverage: a procedure
may address several mechanisms or fail to resolve one. A procedure catalogue and
observed or explicitly simulated investigation paths are needed to connect the
two. Prediction metrics alone cannot establish tests avoided or money saved.
With only 137 rejected test stacks and few examples of some mechanisms, report
uncertainty and per-mode counts; account for shared lot conditions rather than
assuming independent rows. Do not interpret overall accuracy or the original
5.15% acceptance-failure prevalence as diagnostic-task performance.

Once selective testing is introduced, maintain representative full-diagnostic
audits across recommendation patterns and confidence levels, not only cases the
model prioritizes. Untested or inconclusive mechanisms remain **unknown**, not
confirmed negatives. Record test selection, results, engineer overrides and
label provenance so that selective observation does not silently bias evaluation
or retraining.

For serving, on-demand scoring after acceptance failure would support immediate
selection; batch scoring may fit a scheduled diagnostic bench. The choice depends
on lab capacity and turnaround requirements, which v1 does not model. Monitor
feature availability/missingness, product and tool mix, calibration, mechanism
recall, test use, diagnostic time, unresolved cases and audited missed mechanisms.
Use consistent aggregation at training and serving. Later recipe, test-program
or diagnostic-procedure changes may alter both predictions and observed labels.
No serving system, diagnostic policy or intervention study has been implemented.

## Delivered v1 binary benchmark

The following describes the **unchanged delivered task and archived evidence**.
It predicts acceptance failure before initial testing across all assembled stacks.
It does not predict individual mechanisms or evaluate post-acceptance diagnostic
test selection. The archived [baseline report](docs/BASELINE_REPORT.md),
[baseline metrics](metadata/baseline_metrics.json) and
[review decision audit](docs/REVIEW_DECISION_AUDIT.md) retain their v1 scope.

### Original task and sequence

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

Assembly failure covers die crack, warpage, underfill void and delamination.
Electrical failure covers DRAM/base electrical, TSV open/short and microbump
open/bridge modes. The binary target identifies whether any acceptance failure
occurs, not its mechanism.

```text
Individual die electrical screening and KGD selection
  -> stack assembly and package measurements
  -> v1 pre-test feature snapshot and binary risk score
  -> initial final electrical test and assembly/electrical acceptance verdicts
  -> optional sampled reliability testing for acceptance passers
```

KGD means known-good die: a die that passed the modeled incoming screens. Stack
faults may reflect screening escapes or damage introduced during assembly. In
v1, `stack_assembly_pass` is recorded with final-test outcomes; only package
measurements are available at the original prediction checkpoint. The proposed
diagnostic decision occurs after these acceptance verdicts are known.

### Original modeling table

For the v1 binary task, open `data/ml/stack_training.csv`: one row per assembled HBM stack, with pre-electrical-test
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

For the v1 pre-test decision, exclude fields not yet observed. Never use
`data/assembly/electrical_test.csv`, reliability outcomes, simulator truth, or
other labels to predict the same final acceptance outcome.
In particular, final-test `timing_margin_ps`, `max_pass_data_rate_gbps`, BER and
ECC results are later observations, not pre-test predictors. The current timing
margin is generated with a sign determined by electrical pass/fail, so including
it would directly leak the answer.

### Original dataset partitions and binary results

| Partition | Lots | Stacks | Final failures | Failure rate |
|---|---:|---:|---:|---:|
| Train | 168 | 12,564 | 653 | 5.20% |
| Validation | 36 | 2,640 | 126 | 4.77% |
| Test | 36 | 2,589 | 137 | 5.29% |

Feature snapshots span January to June 2025 in a fabricated chronology. In this
release, the final label arrives exactly **12 simulated hours** after the feature
snapshot. This is a delayed acceptance label for the v1 task only; it does not
establish delayed diagnostic confirmation after the new decision point.

The saved baseline is logistic regression with training-only imputation,
standardization and categorical encoding. Its threshold, **0.082470**, was selected
to maximize validation F1. That is an initial classification benchmark, not the
v1 review-capacity ranking audited below, and it was not selected using costs.

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

### Retrospective v1 inspection-rule audit

The retrospective [rule audit](docs/REVIEW_DECISION_AUDIT.md) compares the archived
model with high-side warpage, underfill-void, alignment and delamination rankings,
plus simple OR combinations. All receive the same assumed review allowance of at most 10%
of stacks. The rule is selected on validation, not test.

| Policy | Validation failures found / 264 reviews | Test failures found / 258 reviews |
|---|---:|---:|
| Delamination rule selected on validation | 26 | 20 |
| Underfill-void rule, shown for context | 24 | 29 |
| Archived logistic model | 23 | 31 |

The selected rule outperforms the model on validation. On test the model finds
11 more failures than that selected rule, but a paired lot-bootstrap interval for
the recall difference includes zero. The underfill-void rule finds only two fewer
test failures than the model; it was not selected using that test result. This
audit does **not establish a robust or economically worthwhile ML advantage**.
The rules are transparent proxies, not manufacturer specification limits or an
engineer's validated procedure. The already examined test set is not a fresh
confirmatory holdout.

Review capacity of 10% is an assumption of that v1 audit. It treats a split as
one offline batch with equal review effort per stack. The 31-versus-29 comparison
measures eventual failures found in a review queue; it supplies no result about
mechanism ranking, diagnostics avoided or post-acceptance investigation cost.

### Historical economics of the v1 early-review proposal

The former v1 proposal compared early review against no early review. Let `B`
be the expected avoidable cost per correctly flagged failure **before charging
for early review**, `R` the cost of each early review, and `H` the policy's other
incremental costs, including implementation, maintenance and any displaced work.
Use a common unit and period:

```text
net saving = B * TP - R * (TP + FP) - H
```

`B` must include the chance that the early action actually helps; it is not the
stack's selling price or its full investigation cost. Every flag costs review
time, including true positives. If later investigation and delay are unchanged,
`B = 0` and the extra review adds cost. If it merely moves identical work earlier,
the displaced later effort offsets that earlier effort for true positives;
false flags still add work. Neither case establishes a saving that would justify
the former early-review decision.

The archived model at its original F1 threshold flagged 236 test stacks: 31
failures and 205 passes. Even ignoring overhead, early action would need to save
more than `236 / 31 = 7.61` review-cost equivalents per correctly flagged failure
to break even against no early review. The data does not establish that benefit.
This is a break-even condition, not an estimated saving or an endorsed cost ratio.

At the v1 audit's 258-review allowance, the model still finds 31 failures;
`258 / 31 = 8.32` review-cost equivalents would be needed before overhead. These
are historical break-even conditions, not measured savings or costs for the new
diagnostic-selection proposal. The unsupported `10 * FN + FP` penalty was
withdrawn and does not define the new task's economics.

## Compliance with the BYO problem specification

Reference: [Bring Your Own Problem - Pre-Work Brief](BYO_PROBLEM.pdf), Sections
2A-2D and 4-5, PDF pages 3-7. It requires **all five core items**, **at least four
of six enrichment items**, and **group-owned framing**. Synthetic data is allowed;
a working pipeline is an optional stretch. This assessment concerns the proposed
post-acceptance diagnostic-selection task, not the archived binary benchmark.

**Status key:** "Met - data" identifies delivered supporting records;
"Defined - proposal" identifies a specified scenario or design, not an implemented
system; "Pending" identifies evidence or group action still required.

| Requirement | Status | Evidence, interpretation or remaining action |
|---|---|---|
| Core 1: supervised prediction with definable labels (2A, p. 3) | Met - synthetic label data; proposed task | Seven realized binary fault indicators for 916 rejected stacks support multi-label classification. They are simulator labels, not observed diagnostic outcomes; the new model/table has not been built. |
| Core 2: a named human acts on the output (2A, pp. 3-4) | Defined - proposal | The on-duty HBM quality engineer selects the additional diagnostic investigation after acceptance failure, using mechanism probabilities and existing test evidence. Operational benefit remains unverified. |
| Core 3: asymmetric error costs (2A, p. 4) | Pending economic justification | A wrong recommendation can waste a procedure; an omitted mechanism can prolong or leave diagnosis incomplete. A defensible difference in consequences must be established through the procedure catalogue and stopping policy. No fixed 10:1 penalty is asserted. |
| Core 4: genuinely needs ML rather than a few rules (2C, p. 4) | Pending diagnostic-workflow comparison | Compare diagnostic time/cost at the same completeness requirement against engineering rules and fixed ordering using the same inputs. Existing binary results do not answer this question. |
| Core 5: one model, one decision (2D, p. 5) | Defined - proposal | One multi-label classifier with seven outputs supports one engineer decision: selecting the additional diagnostic investigation. There is no separate deployed model for each fault or automatic process correction. |
| Enrichment 1: class imbalance (2B, p. 4) | Met - data | Within the 916 rejected stacks, mechanism prevalence ranges from die crack at 47/916 (5.13%) to warpage at 247/916 (26.97%). Evaluate each label; overall acceptance-failure prevalence is not this cohort's imbalance. |
| Enrichment 2: late, noisy, proxy or selectively observed label (2B, p. 4) | Proposed workflow only; not established by v1 chronology | Confirmed diagnostic findings would follow test selection, and selective tests could leave labels unknown. V1 supplies complete simulated mechanisms with no separate diagnosis timestamp. Its 12-hour pre-acceptance delay does not establish this property. |
| Enrichment 3: time dimension (2B, p. 4) | Met - data | Retain timestamped lots and ordered train/validation/test partitions with 21-day embargoes. Proposed diagnostic cases total 653/126/137; the task remains per-stack classification. |
| Enrichment 4: leakage trap and/or train/serve skew (2B, p. 4) | Met - data and defined boundary | Defect annotations and simulator truth would reveal the targets; whole-table joins would mix them with initial test measurements. Initial test observations may be valid at the new checkpoint. Audit feature availability, generated shortcuts and consistent aggregation. |
| Enrichment 5: feedback loop and/or genuine serving choice (2B, p. 4) | Defined - proposal | Test selection changes which mechanism labels are observed, requiring representative full-diagnostic audits. On-demand selection versus batch bench scheduling depends on diagnostic capacity and turnaround; neither is implemented. |
| Enrichment 6: plausible data/concept drift (2B, p. 4) | Met - data and proposal | Tool age, maintenance and material effects create changing inputs. Future recipe, test-program or diagnostic-procedure changes could change relationships or label ascertainment; those changes are not implemented. |
| Framing belongs to the group (2D, p. 5; Section 5, p. 7) | Pending group confirmation | The group must choose and defend the diagnostic decision, labels, costs, baselines and completeness requirement. LLM-assisted documentation cannot certify that ownership. |
| Other disqualifiers (2D, pp. 4-5) | Partly addressed; core gates unresolved | Supervised labels, human control and one decision are defined. Cost asymmetry and a need for ML remain open; no full-compliance claim is made. |
| Do not leave both drift/monitoring and leakage/skew blank (2D, p. 5) | Met - data and proposal | Both have concrete risks and proposed checks above. |
| Data plan and optional pipeline (Sections 1 and 4, pp. 1-2, 6) | Synthetic prediction data available; workflow evidence pending | V1 supplies candidate inputs and mechanism labels. A diagnostic catalogue, costs, investigation paths and confirmation timestamps are still needed to evaluate test savings. |
| Half-page group proposal and mentor approval (Section 4, p. 6) | Pending group action | Summarize the revised decision and evidence gaps for the group's submission. Submission and mentor sign-off are not evidenced here. |

**Assessment:** Core 1 has synthetic label support; Core 2 and Core 5 are defined
as a proposal. Core 3 and Core 4 remain unresolved. Enrichments 1, 3 and 4 have
delivered-data support; 6 combines data and a drift scenario. Enrichment 5 adds a
proposed serving/selection-feedback argument, while 2 is a future workflow
property. These do not establish diagnostic savings or repair the missing core
evidence. Group ownership and mentor approval remain separate requirements.

A defensible viva statement is: **"We propose one multi-label model to help the
quality engineer select additional diagnostics after a stack fails acceptance.
The hypothesis is lower investigation cost at comparable diagnostic completeness.
V1 provides synthetic mechanism labels and an older binary benchmark; a trained
mechanism model, workflow comparison, justified error costs and measured test
savings remain to be established."**

## Cleaned package layout

This copy is organized for data analysis rather than regeneration:

```text
data/manufacturing/   Lot, wafer, process, metrology and TSV records
data/assembly/        Stack genealogy, assembly, final test and reliability records
data/ml/              Delivered v1 binary-task features, labels and training table
data/simulation_truth/ Audit truth; seven stack-fault indicators proposed as labels only
docs/                 Archived v1 model, source, validation and baseline reports
metadata/             Configuration, manifests and machine-readable results
scripts/              Reproducible retrospective v1 binary review-rule audit
```

The original Python generator, validation and training utilities and their
dependency file were removed during cleanup. The later rule-audit script uses
Python's standard library and reconstructs the archived scores; it does not
regenerate data or train a replacement model. `metadata/manifest.json` retains
original row counts,
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

- No additional diagnostic-test catalogue, procedure-level coverage, cost,
  investigation path or separate confirmation timestamp is modeled. The proposed
  input/label boundary and test-saving workflow therefore require new validation.
- Some initial test readings are functions of simulated acceptance faults. A
  model can exploit those generated relationships without establishing realistic
  diagnostic value; outcome annotations must remain excluded from inputs.

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

Other possible data-generation extensions include an electrical-only task among assembly-accepted
stacks, explicit fault/repair semantics, causal speed-margin modeling, clustered
metrology, additional recipes and real-data parameter calibration. Each needs its
own assumptions and validation. None is required merely to add more features for
the BYO exercise, and none should be presented as already implemented in v1.
