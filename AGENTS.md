# Helion: HBM diagnostic-test selection (AIAP assignment 8, Group 8)

Viva deliverable, not production software. Graded on design reasoning; the build is ~1-2% of marks.
Task: for an HBM3E stack that has already failed acceptance testing, recommend the next of 5
diagnostic procedures to cut investigation cost while keeping the false-negative rate at parity
with the rule-based baseline. All data is synthetic (no SK hynix records, not calibrated).

## Layout
- `project/brief/` — client brief + presentation rubric (supplied; don't edit)
- `project/design/` — design notebook, architecture, mock rules (MOCK-ENG-002), walkthrough, diagrams
- `project/presentation/` — `PRE_READ_team_8.md`, outline, viva prep, `slides/` (LaTeX beamer)
- `project/evidence/` — archived v1 reports + `SOURCES.md`
- `synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.{md,json}` — SYN-OPS-001; source of truth for costs, rates, sensitivity/specificity, inconclusive rates
- `helion_pipeline/` — code; `config.json` (seed 20260921)
- `artifacts/helion_pipeline/research_v2_concern_closure/` — canonical current run (start with `benchmark_report.md`)

## Stale — do not trust or cite
- `project/evidence/V1_DATA_AND_PROPOSAL.md` is the pre-pipeline README; its "model untrained" and "Core 3–4 pending" claims are superseded.
- `project/evidence/`, `metadata/`, `data/` document the v1 dataset; `data/` is still the pipeline input.
- `artifacts/helion_pipeline/research_v1/` is an immutable archive (MOCK-ENG-001). Never cite it as current.

## Domain vocabulary
- Procedures (`PROCEDURE_ORDER`): XRAY, ACOUSTIC, ELECTRICAL, IR, SEM (destructive, last).
- Mechanisms (`common.MECHANISMS`): dram_electrical, tsv_open_short, microbump_open_bridge, die_crack, warpage, underfill_void, delamination.
- Policies: `mock` (rule baseline), `ct_first`, `heuristic` (coverage × (1 − p_inconclusive) / cost).
- Routine cases use concern-complete closure; 1 in 20 audit cases run the full battery.
- Model probabilities are static per stack; test results update rule state, not probabilities.

## Code map (`helion_pipeline/`)
data (sha256 check + lot/time split 653/126/137) → model (7 logistic heads) → engine (state, eligibility rules, recommend)
→ replay (paired policy simulation) → scheduling → reporting. `fixtures` = scripted A/B/C walkthroughs.

## Commands (repo root)
```bash
PY=/home/harry/Documents/aiap-deep-skill/all-assignments/.venv/bin/python
# Tests (plugin flag required: a ROS pytest plugin on this machine breaks collection)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/helion-mpl $PY -m pytest -q
# Smoke run — only when tests can't cover a code change
$PY -m helion_pipeline run --out /tmp/helion-smoke --replications 2 --bootstrap-samples 50
# Stages: run | validate | train | score | replay | schedule | report
# Slides (speaker notes are edited in project/presentation/presentation_outline.md)
cd project/presentation/slides && python3 sync_speaker_notes.py && make
```

## Rules
- Never edit `data/` or `metadata/manifest.json` (sha256-checked; the generator is absent).
- Don't re-run the pipeline by default. Doc and design edits need no run. For code changes, run the tests.
- Regenerate the canonical `research_v2_concern_closure` run only when the user asks. Its `run_manifest.json` checksums `project/` and the assumptions, so drift after edits is expected.
- Smoke/experimental runs go to `/tmp`. The CLI refuses output under `data/`, `metadata/`, `project/` or `synthetic-data-assumptions/`.
- Change assumptions only in the `.md` + `.json` pair and keep them in sync.
- Keep the project's claims honest: "synthetic"; "design only; no measured savings"; costs are "standard resource costs, not avoidable cash"; inconclusive or unexamined ≠ negative label; a first confirmed fault does not authorise stopping.
- Don't commit `replay_events.jsonl.gz`, caches or `slides/build/`.
