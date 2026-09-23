# Helion Beamer presentation

Eight slides for a ten-minute presentation, based on the [updated outline](../presentation_outline.md) and the canonical `research_v2_concern_closure` benchmark. The slides distinguish synthetic research findings from proposed fab operation. Group 8 is the supplied team identity; member names can be added to the source when known.

- [Presentation PDF](helion_slides.pdf): eight 16:9 slides, without notes or overlays.
- [LaTeX source](helion_slides.tex): editable tables, schedule and architecture diagram.
- [Presenter PDF](helion_presenter.pdf): each slide beside its timed speaker notes.
- [Speaker-note source](speaker_notes.tex): the outline's notes, with evidence references.

## Build

Run from this directory:

```bash
make
```

Requirements: `latexmk` and pdfLaTeX with Beamer, Latin Modern, PGF/TikZ, `pgfpages`, `booktabs` and `tabularx`. These are available in common TeX Live installations. The finished PDFs are copied here; intermediate compilation files remain in ignored `build/`. No downloaded fonts, raster images, network access or shell escape are required.

Separate targets are `make slides` and `make notes`. Without `make`/`latexmk`, run `pdflatex -interaction=nonstopmode -halt-on-error helion_slides.tex` twice, and repeat for `helion_presenter.tex` if needed. Two passes resolve slide totals. Compile from this directory so that LaTeX can find the note source.

To refresh speaker notes after editing the outline:

```bash
python3 sync_speaker_notes.py
make
```

This updates notes only. Slide content is deliberately concise and should be edited in `helion_slides.tex`. The presenter PDF uses Beamer's second-screen format; a compatible presentation viewer can place the slide and notes on separate displays. A normal PDF viewer shows both side by side.

## Timing

| Slide | Topic | Duration | Elapsed |
|---|---|---:|---:|
| 1 | Objective | 0:45 | 0:45 |
| 2 | Pipeline and comparators | 1:00 | 1:45 |
| 3 | Evidence and assumptions | 1:15 | 3:00 |
| 4 | Prediction findings | 1:30 | 4:30 |
| 5 | Diagnostic outcomes | 1:45 | 6:15 |
| 6 | Scheduling example | 1:15 | 7:30 |
| 7 | Proposed operation | 1:30 | 9:00 |
| 8 | Interpretation and next work | 1:00 | 10:00 |

The opening carries the business objective, so there is no extra cover or ninth slide. The architecture condenses the [design blueprint](../../design/images/helion-architecture.mmd) into four connected stages. The schedule is an editable timing diagram of existing Case D. Detailed qualification, monitoring and evidence-scope rules remain in the notes and linked design documents.

## Evidence

All displayed findings are from the supplied local research run. Rebuilding the slides does not rerun training or simulation and does not alter the benchmark.

| Slides | Evidence |
|---|---|
| 1–3 | [Client brief](../../brief/helion_semiconductor_client_brief.md), [pipeline README](../../../helion_pipeline/README.md), [candidate rules](../../design/mock_engineering_inspection_rules.md), [operating assumptions](../../../synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.md), [validation](../../../artifacts/helion_pipeline/research_v2_concern_closure/validation.json) |
| 4 | [Predictive metrics](../../../artifacts/helion_pipeline/research_v2_concern_closure/predictive_metrics.csv), [paired predictive intervals](../../../artifacts/helion_pipeline/research_v2_concern_closure/predictive_paired_comparisons.csv), [training record](../../../artifacts/helion_pipeline/research_v2_concern_closure/training.json) |
| 5 | [Decision metrics](../../../artifacts/helion_pipeline/research_v2_concern_closure/decision_metrics.csv), [paired uncertainty](../../../artifacts/helion_pipeline/research_v2_concern_closure/decision_uncertainty.csv), [post-run verification](../../../artifacts/helion_pipeline/research_v2_concern_closure/verification.json) |
| 6 | [Scheduling results](../../../artifacts/helion_pipeline/research_v2_concern_closure/scheduling.json), [deterministic walkthroughs](../../../artifacts/helion_pipeline/research_v2_concern_closure/walkthroughs.json) |
| 7–8 | [Design notebook](../../design/P1_ml_systems_helion.ipynb), [benchmark report](../../../artifacts/helion_pipeline/research_v2_concern_closure/benchmark_report.md), [executed pipeline walkthrough](../../../artifacts/helion_pipeline/research_v2_concern_closure/pipeline_walkthrough.ipynb) |

Interpretation: macro average precision describes fault ranking. It is separate from the correctly-complete investigation fraction. Costs include unfinished cases and exclude unknown manual-review continuation. All 100 report replications reuse the same test cases. CT-first and the full model produce identical base-test cost/quality outcomes under the assumptions. The scheduling example changes scoped milestone feasibility while both orders cost $240 and finish at 10:30. No policy is qualified for production.
