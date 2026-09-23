# Helion: HBM3E diagnostic-test selection

AIAP assignment 8 (Designing a Good ML System), Group 8. When an assembled HBM3E stack has **already
failed acceptance testing**, the on-duty quality engineer must choose which of five diagnostic
procedures to run next. We ask whether fault-mechanism predictions can lower investigation cost
**without increasing missed faults** relative to the existing rule-based workflow.

**Status:** viva design submission backed by an executed offline benchmark. All data and operating
assumptions are synthetic: no SK hynix records, not calibrated to any fab. No measured savings,
production threshold or release is claimed.

## Headline result

On the 137-stack test partition, ML-ordered selection did **not** beat the candidate rules:

| Arm | Cost / case (USD) | Evidence-complete | Missed faults / case |
|---|---:|---:|---:|
| Candidate rules (`mock`, MOCK-ENG-002) | 1,169.26 | 86.6% | 0.123 |
| Heuristic, full-context model | 1,170.92 | 86.6% | 0.121 |
| Heuristic, inspection-only model | 1,170.82 | 86.6% | 0.121 |

- **Prediction:** manufacturing context adds nothing over inspection/acceptance inputs
  (macro AP 0.497 vs 0.504; log loss 0.251 vs 0.231). Several acceptance inputs are synthetic shortcuts
  to the labels, so high scores do not show real-fab discrimination.
- **Selection:** the model arms cost about $1.66/case more (paired lot-bootstrap 95% CI $0.51–$2.98)
  and miss slightly fewer faults (−0.002/case). Under the assumed procedure catalogue, CT dominates
  acoustic per dollar, so better probabilities rarely change which procedures run.
- **Interpretation:** keeping the rules is a valid recommendation when incremental ML value cannot be
  shown. This result comes from the exercise's catalogue and heuristic. It does not show that ML
  cannot help a real lab.

Full tables, uncertainty, stress tests and scheduling cases:
[benchmark report](artifacts/helion_pipeline/research_v2_concern_closure/benchmark_report.md) ·
[walkthrough notebook](artifacts/helion_pipeline/research_v2_concern_closure/pipeline_walkthrough.ipynb).

## The decision

| Element | Definition |
|---|---|
| Unit | One rejected 8-high or 12-high HBM3E stack (including its base die) |
| Decision owner | On-duty HBM quality engineer; chooses the procedure and approves closure |
| Model output | Seven mechanism probabilities (multi-label; may co-occur, need not sum to 1) |
| Action supported | Order the eligible next procedure among XRAY (CT), ACOUSTIC, ELECTRICAL, IR, SEM |
| Constraint | Keep the false-negative (missed-fault) rate at parity with the rule baseline; minimise cost within it |
| Authority limits | Scores never authorise shipment, scrap, skipping required tests, or stopping at a first confirmed fault |

```text
acceptance failure → nightly scoring (7 probabilities)
  → eligibility rules (MOCK-ENG-002) → rank eligible procedures → engineer runs one
  → report updates evidence & eligibility → repeat until concern-complete or escalated
  1 in 20 cases: independent full-battery audit (unbiased labels for monitoring)
```

Model probabilities are computed once per stack. Test results update the rule state and
eligibility, not the probabilities. The architecture diagrams are in
[project/design/architecture.md](project/design/architecture.md).

## Rejected-stack cohort and seven targets

916 of the 17,793 synthetic assembled stacks failed acceptance. The original lot/time partitions
(21-day embargoes) are retained: **653 train / 126 validation / 137 test**. Labels are the simulator's
realised fault indicators in `data/simulation_truth/simulation_truth_stack.csv`, used only as
targets. They are synthetic reference labels, not diagnostic findings. 21 stacks have multiple
mechanisms.

| Mechanism | Positives / 916 | Share |
|---|---:|---:|
| `warpage` | 247 | 26.97% |
| `underfill_void` | 206 | 22.49% |
| `microbump_open_bridge` | 137 | 14.96% |
| `tsv_open_short` | 108 | 11.79% |
| `dram_electrical` | 97 | 10.59% |
| `delamination` | 96 | 10.48% |
| `die_crack` | 47 | 5.13% |

Inputs are the 35 manufacturing/package predictors plus initial acceptance observations.
Excluded: defect annotations, dispositions, reliability outcomes, simulator latents, IDs and
`timing_margin_ps` (its sign is generated from pass/fail). Untested or inconclusive mechanisms
stay **unknown**, never negative.

## Repository map

```text
project/brief/          Client brief and presentation rubric (supplied)
project/design/         Design notebook, architecture, mock inspection rules, walkthrough, diagrams
project/presentation/   Pre-read, outline + speaker notes, viva prep, slides/ (LaTeX beamer)
project/evidence/       Archived v1 reports, sources, and the v1 dataset description
synthetic-data-assumptions/operation-assumptions/
                        SYN-OPS-001: procedure costs, staffing, sensitivity/specificity, inconclusive rates
helion_pipeline/        validate → train → score → replay → schedule → report
artifacts/helion_pipeline/
  research_v2_concern_closure/   Canonical current run
  research_v1/                   Immutable archive (superseded rules); do not cite as current
data/, metadata/        Synthetic v1 dataset (18 tables, sha256-checked) and its manifests
tests/                  Pipeline, engine, scheduling and data contract tests
```

Where to start:

- **Presenting:** [pre-read](project/presentation/PRE_READ_team_8.md) →
  [presentation outline](project/presentation/presentation_outline.md) →
  [viva preparation](project/presentation/viva_preparation.md)
- **Design reasoning:** [design notebook](project/design/P1_ml_systems_helion.ipynb) and
  [mock inspection rules](project/design/mock_engineering_inspection_rules.md)
- **Assumptions:** [synthetic operating assumptions](synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.md)
- **Code:** [pipeline README](helion_pipeline/README.md)

## Running

Python 3.12 with the versions pinned in `pyproject.toml`; no network access is needed at runtime.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/helion-mpl python -m pytest -q
```

```bash
python -m helion_pipeline run --out /tmp/helion-smoke --replications 2 --bootstrap-samples 50
```

Individual stages are `validate`, `train`, `score`, `replay`, `schedule` and `report`. The CLI refuses
to write into `data/`, `metadata/`, `project/` or `synthetic-data-assumptions/`. Only regenerate the
canonical run deliberately, into a fresh `--out` directory whenever the config or sources change.
Build the slides with `make` in `project/presentation/slides/` (see its README).

## Limitations

- **Synthetic end to end.** Costs, staffing, test sensitivity/specificity and inconclusive rates are
  invented (SYN-OPS-001). The replay generates reports from the same assumptions the policies use.
  The stress tests (rates ×0.75/1.25, q ±0.05, sensitivity −0.05, specificity −0.02) are the honest
  check. They are not confidence intervals.
- **Candidate rules, not real SOP.** MOCK-ENG-002 stands in for Helion's incumbent procedure.
- **Retrospective test set.** The test partition was examined in earlier audits, so it is not a
  pristine holdout.
- **Dollars are resource capacity** (standard costs), not avoidable cash. Queue delay is not
  monetised.
- **Rare mechanisms.** About 45 audits/quarter gives limited evidence for die crack and
  coexisting faults.
- **Next evidence needed:** the real SOP and stopping rules, observed procedure costs, qualified
  diagnostic performance from complete audits, and a prospective paired comparison.

## Background: the v1 dataset

The synthetic cohort was built from scratch using public HBM3E / Advanced MR-MUF descriptions
([sources](project/evidence/SOURCES.md)). Its generator is not in this package, so the CSVs can be
verified by checksum but not regenerated. The earlier v1 task predicted binary acceptance failure
before testing, which is a different decision. The full record structure, generation rules,
missingness conventions, v1 benchmark and scope-of-realism notes are archived in
[project/evidence/V1_DATA_AND_PROPOSAL.md](project/evidence/V1_DATA_AND_PROPOSAL.md). Variable
definitions are in [data/data_dictionary.csv](data/data_dictionary.csv).
