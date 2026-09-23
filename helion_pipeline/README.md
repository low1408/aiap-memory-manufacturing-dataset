# Helion offline diagnostic research

This package implements the current model/policy benchmark using the supplied synthetic rejected stacks, candidate comparator `MOCK-ENG-002` and `SYN-OPS-001`. It is an offline research exercise, not qualified fab software. The earlier `research_v1` run remains archived with its original `MOCK-ENG-001` provenance.

Start with the [executed benchmark report](../artifacts/helion_pipeline/research_v2_concern_closure/benchmark_report.md) or the [walkthrough notebook](../artifacts/helion_pipeline/research_v2_concern_closure/pipeline_walkthrough.ipynb). The [HTML report](../artifacts/helion_pipeline/research_v2_concern_closure/benchmark_report.html) includes the same figures and tables. The [artifact index](../artifacts/helion_pipeline/README.md) records the current/archive boundary.

## Run

From the repository root with Python 3.12 and the versions in `pyproject.toml`:

```bash
python -m helion_pipeline run
```

The tested interpreter on this workstation is `/home/harry/Documents/aiap-deep-skill/all-assignments/.venv/bin/python`. No runtime network connection is used. An air-gapped installation needs the pinned dependencies supplied in advance; the package does not fetch or install them automatically.

For bounded native numerical threads and a writable plotting cache:

```bash
MPLCONFIGDIR=/tmp/helion-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /home/harry/Documents/aiap-deep-skill/all-assignments/.venv/bin/python \
  -m helion_pipeline run
```

Default output: `artifacts/helion_pipeline/research_v2_concern_closure/`. A quick integration exercise belongs in a different directory:

```bash
python -m helion_pipeline run --out /tmp/helion-smoke --replications 2 --bootstrap-samples 50
```

Stages are individually available as `validate`, `train`, `score`, `replay`, `schedule`, and `report`; use the same `--out` and configuration for a run. The CLI checks stage prerequisites, invalidates dependent stages after upstream changes, and records failures rather than claiming stale scores are current. Configuration or authoritative source changes require a new output directory. Per-stage code checksums preserve the code version used for each computation.

## Pipeline and evidence boundaries

```text
Original CSVs + immutable assumptions
  -> checksum / key / chronology / cohort validation
  -> separate feature and seven-label tables
  -> training-only transformations + seven binary logistic heads
  -> saved alternative pipelines + initial fault probabilities
  -> shared evidence rules + mock / CT-first / heuristic policies
  -> paired hypothetical reports + bounded diagnostic paths
  -> all-case quality/cost comparisons + uncertainty + report

Existing one-day roster + separate A/B/D fixtures
  -> qualified staff/equipment bookings + deadline comparisons
```

`data.py` owns the explicit feature boundary and validates all supplied manifest tables. It preserves 653/126/137 rejected-stack partitions and observed missingness reasons. Fault truth is extracted through a target-only column selection and never enters the policy input. Metadata and raw truth-derived annotations are not fitted predictors.

`model.py` owns train-only preprocessing and training/scoring. One `model.joblib` contains the inspection, full-context and manufacturing-only seven-head logistic alternatives, plus training prevalence. It records feature lists, training identities and version metadata. All variants use the same small C search and training-lot folds. Seven output probabilities do not sum to one. No class weighting or calibration model is fitted.

The acceptance inputs are legitimate *synthetic post-acceptance* inputs but include simulator shortcuts. The manufacturing-only comparison is essential; predictive scores are not evidence of realistic fab accuracy. The old acceptance-failure task is neither overwritten nor a numerical comparator for this new task.

`engine.py` separates `CaseSnapshot`, `InvestigationState`, recommendation, report generation and truth-based evaluation. The policy sees initial observations, probabilities and reports, never hidden truth. Initial probabilities stay fixed; scoped findings update evidence and eligibility. IR does not assign a mechanism label; a negative gross-delamination CT result cannot exclude all delamination; contradictory findings require review.

`replay.py` pairs reports by sample, procedure, question, attempt and replication. The gross-delamination subtype and independent synthetic audit assignment are fixed per sample. Unexamined or inconclusive questions never become negative labels. An inconclusive CT, acoustic or electrical attempt may receive one independent conditional repeat; IR and destructive SEM are not repeated. Unresolved continuations remain unpriced and pending. Every started case remains in the metrics denominator.

`scheduling.py` uses the existing 24-hour calendar and staff-phase definitions. It never extends a roster, invents arrivals or provides an unsupported SEM appointment. Existing examples are separate except the explicit two-case D fixture. Confirmed bookings are preserved. Deadlines refer to scoped evidence conditional on conclusive reports, not whole-investigation closure.

## Comparators and interpretation

| Arm | What changes |
|---|---|
| `mock` | Candidate MOCK-ENG-002 concern work in documented priority order |
| `ct_first` | Compatibility comparator; equivalent priority order under concern closure |
| `prevalence` | Coverage/cost heuristic with seven training-prevalence probabilities |
| `inspection` | Same heuristic with inspection/acceptance probabilities |
| `full` | Same heuristic with the full permitted manufacturing context |
| `manufacturing` | Same heuristic excluding the nine acceptance predictors |

All arms share costs, concern-opening rules, co-fault safeguards, scope, repeat/report-error assumptions, stopping requirements, audit obligations and destructive-work restrictions. Audits use the same fixed all-five order across arms. Model scores cannot waive required questions.

Dollar values are standard resource costs: attended technician/engineer time, instrument occupancy and consumables. They are not wholly avoidable cash. Pending costs include known unattempted procedures, not unknown manual review or guaranteed completion. Nominal procedure-hour totals are not actual turnaround. A lower cost accompanied by less complete diagnosis is not savings at unchanged quality.

The report separates lot-cluster uncertainty, Monte Carlo report variation and assumption stresses. Base replay covers all 916 cases; stresses cover the 137-case retrospective test partition. Training results are in-sample diagnostics. The two test co-fault cases and six die-crack cases provide limited evidence. No winner, production threshold or release approval is inferred.

## Output guide

| Output | Purpose |
|---|---|
| `run_manifest.json`, `config_used.json`, `operating_assumptions_used.json`, `requirements.lock.txt`, `verification.json` | Reproduction, source/code versions, stage status and post-run checks |
| `validation.json`, `prepared/*.parquet` | Verified feature/label views, counts, missingness and actual chronology gaps |
| `model.joblib`, `training.json` | Single trusted local model artifact, C selection and fitting provenance |
| `predictions.parquet`, `scoring.json` | Per-case seven probabilities, model version and scoring/fallback status |
| `predictive_metrics.csv`, `calibration.csv`, `predictive_uncertainty.csv`, `predictive_paired_comparisons.csv` | Prediction and calibration evidence |
| `synthetic_audits.json` | Newly simulated audit membership, not recovered history |
| `replay_cases.parquet` | Every case/arm/replication summary for base and numerical stresses |
| `replay_events.jsonl.gz` | Every base-run recommendation, scoped report, evidence transition and resource charge |
| `decision_metrics.csv`, `decision_uncertainty.csv`, `decision_slices.csv`, `tradeoffs.csv`, `recommendation_changes.csv` | All-case comparisons, paired uncertainty, slices and empirical trade-offs |
| `scheduling.json`, `walkthroughs.json` | Exact finite-calendar scenarios and scripted diagnostic branches |
| `benchmark_report.md`, `.html`, `pipeline_walkthrough.ipynb`, `figures/` | Human-readable results and learning material |

Stress event records can be reproduced from the saved configuration and paired seeds; full per-case stress summaries are retained. Only load `model.joblib` from a trusted local run, since Python model serialization is executable when loaded.

Logical batch scoring is also available through `predict_cases(cases, artifact, batch_valid=True)`. It never loads targets or refits. Invalid imports fail before new scores; missing acceptance records or unqualified tool/supplier contexts produce explicit fallback/manual-review rows with null probabilities. The supplied data has EMC batches but no supplier identity, so batches are not mislabelled as suppliers. No live nightly scheduler or production interface is installed.

## Verify

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/helion-mpl \
  python -m pytest -q
```

Disabling plugin auto-loading avoids an incompatible preinstalled ROS pytest plugin on this workstation; this package requires no pytest plugins. Tests cover source and artifact tampering, partition/feature leakage, saved-model equality, missing/unknown inputs, report scope, coexisting faults, audit handling, inconclusive and contradictory branches, scheduling conflicts and cost/quality comparison semantics.

Reproduce a run using its configuration, dependencies and the source/code revisions recorded in its manifest. Scientific metrics and simulation traces are deterministic under those inputs; timestamps, wall-clock durations and executed-notebook timing metadata are not scientific outputs.
