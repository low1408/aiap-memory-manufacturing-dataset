# Helion research artifacts

`research_v2_concern_closure/` is the canonical evidence set for the current `HELION-PIPELINE-002` code, candidate `MOCK-ENG-002` comparator and bounded concern-closure replay. Start with its `benchmark_report.md`, `pipeline_walkthrough.ipynb` and `run_manifest.json`.

`research_v1/` is an immutable historical run of `HELION-PIPELINE-001` with `MOCK-ENG-001` and the superseded all-seven closure assumption. Its complete artifact set is retained for reproducibility; current claims must not cite it as v2 evidence.

## Retention policy

- Keep each versioned run self-contained, including identical model, prepared-data or metric files shared with another run. Those copies are provenance, not accidental duplicates.
- Keep manifests, pinned requirements, prepared views, model/scoring outputs, aggregate metrics, reports, walkthroughs and figures for canonical and archived runs.
- Do not commit `replay_events.jsonl.gz`, notebook checkpoints, temporary files, Python caches, pytest caches or LaTeX build directories. They are regenerated locally.
- Put smoke runs and experimental comparisons in `/tmp` or another explicitly named non-canonical directory. Promote a run only after all six stages, tests, link checks and presentation build succeed.
