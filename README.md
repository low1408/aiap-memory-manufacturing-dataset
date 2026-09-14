# HBM3E manufacturing simulation: SK hynix-like scenario

This is a fully synthetic, reproducible dataset for HBM manufacturing analytics.
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

## Start with the modeling table

Open `data/ml/stack_training.csv`: one row per assembled HBM stack, with pre-electrical-test
features, IDs, a split and the target `final_test_fail` (1 = failure, 0 = pass).
Use the `train`, `validation` and `test` partitions already in the file. Exclude
`stack_id`, `lot_id`, `split` and `feature_available_time_utc` from predictors.
The categorical predictor is `assembly_tool_id`. Missing numerical measurements
must be imputed using training data only. `metadata/ml_task.json` supplies an explicit
feature allowlist and prediction-time definition.

The intended decision is: **after assembly and package inspection, which stacks
will fail final acceptance?** Package inspection measurements are legitimately
available at this checkpoint. They are not valid predictors for a decision made
before assembly. Final acceptance combines assembly inspection and electrical
screening. `electrical_test_pass` and `stack_assembly_pass` identify each component.

For an earlier decision, construct a separate feature snapshot and exclude fields
not yet observed. Never use `data/assembly/electrical_test.csv`, reliability outcomes, simulator
truth, or other labels to predict the same final acceptance outcome.

## Cohort and record structure

The default scenario includes 240 lots, 25 wafers per lot and 32 sampled die
locations per wafer: 6,000 wafers and 192,000 DRAM die records. Each lot is assigned
an 8-high or 12-high HBM3E product. Core dies have 3 GB capacity, producing 24 GB or
36 GB stacks. The base die is separate and does not add DRAM capacity.

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

## Scope of realism

This release represents selected late-fabrication and wafer-level packaging
modules plus HBM stack assembly, not hundreds of upstream DRAM operations. Fab
cycle time, dispatching, queueing, resource capacity, cost, detailed material
chemistry, individual TSV nets, electrical circuit simulation, GPU/interposer
integration and post-stack rework are outside the model. `assembly_tool_id`
denotes a synthetic assembly-line group with multiple processing stations; its
timestamps do not represent a single-resource occupancy schedule. Functional
TSV counts/pitches and wafer-grid pitch are assumed architecture settings.

Potentially useful extensions are earlier prediction checkpoints, real-data
parameter calibration, multiple production recipes and a matched Micron-like
scenario. They require their own assumptions and validation.
