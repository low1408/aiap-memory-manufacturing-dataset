"""Reproducible reports, uncertainty, figures and a lightweight reading notebook."""
from __future__ import annotations

import json
from pathlib import Path
import textwrap
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, MaxNLocator, PercentFormatter
import nbformat
import numpy as np
import pandas as pd

from .common import MECHANISMS, write_json
from .replay import summarise_replay

NAMES = {"mock": "Mock incumbent", "ct_first": "CT-first rules", "prevalence": "Prevalence heuristic",
         "inspection": "Inspection model", "full": "Full-context model", "manufacturing": "Manufacturing only"}
COLORS = {"mock": "#475569", "ct_first": "#111827", "prevalence": "#a16207", "inspection": "#0f766e", "full": "#2563eb", "manufacturing": "#9333ea"}


def markdown_table(frame, columns=None, digits=3):
    frame = frame[columns] if columns else frame
    lines = ["| " + " | ".join(map(str, frame.columns)) + " |", "| " + " | ".join("---" for _ in frame.columns) + " |"]
    for row in frame.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                value = "unavailable" if np.isnan(value) else f"{value:.{digits}f}"
            values.append(str(value).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def predictive_uncertainty(out, config):
    cases = pd.read_parquet(out / "prepared/cases.parquet")[["stack_id", "lot_id", "split"]]
    truth = pd.read_parquet(out / "prepared/labels.parquet")
    predictions = pd.read_parquet(out / "predictions.parquet")
    rng = np.random.default_rng(config["seed"])
    records, comparisons = [], []
    for split in ("validation", "test"):
        part = cases[cases.split == split].sort_values("stack_id").merge(truth, on="stack_id", validate="one_to_one")
        lots, lot_index = np.unique(part.lot_id, return_inverse=True)
        lot_weights = rng.multinomial(len(lots), np.repeat(1 / len(lots), len(lots)), size=config["bootstrap_samples"])
        weights = lot_weights[:, lot_index].astype(float)
        denominator = weights.sum(axis=1)
        y = part[[f"fault_{m}" for m in MECHANISMS]].to_numpy()
        by_variant = {}
        for variant in ("prevalence", "inspection", "full", "manufacturing"):
            p = part[["stack_id"]].merge(predictions[predictions.variant == variant], on="stack_id", validate="one_to_one")[[f"p_{m}" for m in MECHANISMS]].to_numpy()
            metric_arrays = {"average_precision": [], "binary_log_loss": [], "brier_score": []}
            for j, mechanism in enumerate(MECHANISMS):
                probability = np.clip(p[:, j], 1e-15, 1 - 1e-15)
                loss = -(y[:, j] * np.log(probability) + (1 - y[:, j]) * np.log1p(-probability))
                metric_arrays["binary_log_loss"].append(weights @ loss / denominator)
                metric_arrays["brier_score"].append(weights @ (p[:, j] - y[:, j])**2 / denominator)
                order = np.argsort(-p[:, j], kind="stable")
                ordered_scores, targets = p[order, j], y[order, j]
                w = weights[:, order]
                group_ends = np.r_[np.where(np.diff(ordered_scores) != 0)[0], len(order) - 1]
                pos_cumulative = np.cumsum(w * targets, axis=1)[:, group_ends]
                all_cumulative = np.cumsum(w, axis=1)[:, group_ends]
                positive_increments = np.diff(np.column_stack([np.zeros(len(w)), pos_cumulative]), axis=1)
                precision = np.divide(pos_cumulative, all_cumulative, out=np.zeros_like(pos_cumulative), where=all_cumulative != 0)
                positives = pos_cumulative[:, -1]
                ap = np.divide((positive_increments * precision).sum(axis=1), positives,
                               out=np.full(len(w), np.nan), where=positives != 0)
                metric_arrays["average_precision"].append(ap)
            for metric, values in metric_arrays.items():
                array = np.array(values).T
                by_variant[variant, metric] = array.mean(axis=1)
                for j, mechanism in enumerate([*MECHANISMS, "macro"]):
                    draws = array[:, j] if j < 7 else array.mean(axis=1)
                    valid = draws[np.isfinite(draws)]
                    records.append({"split": split, "variant": variant, "mechanism": mechanism, "metric": metric,
                        "low": np.quantile(valid, .025) if len(valid) else None, "high": np.quantile(valid, .975) if len(valid) else None,
                        "valid_bootstrap_samples": len(valid), "lot_count": len(lots)})
        for metric in ("average_precision", "binary_log_loss", "brier_score"):
            difference = by_variant["full", metric] - by_variant["inspection", metric]
            valid = difference[np.isfinite(difference)]
            comparisons.append({"split": split, "comparison": "full_minus_inspection", "metric": metric,
                                "low": np.quantile(valid, .025), "high": np.quantile(valid, .975), "valid_bootstrap_samples": len(valid)})
    pd.DataFrame(records).to_csv(out / "predictive_uncertainty.csv", index=False)
    pd.DataFrame(comparisons).to_csv(out / "predictive_paired_comparisons.csv", index=False)


def make_figures(out, metrics, decision):
    figures = out / "figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
    macro = metrics[(metrics.split == "test") & (metrics.mechanism == "macro")].set_index("variant")
    variants = ["prevalence", "inspection", "full", "manufacturing"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, metric, title in zip(axes, ["average_precision", "binary_log_loss"], ["Macro average precision · higher is better", "Macro binary log loss · lower is better"]):
        ax.barh(["Training prevalence" if v == "prevalence" else NAMES[v] for v in variants], [macro.loc[v, metric] for v in variants], color=[COLORS[v] for v in variants])
        ax.set_title(title, fontsize=11)
        ax.grid(axis="x", alpha=.2)
    fig.suptitle("Fault prediction on 137 synthetic test cases · retrospective", fontsize=13)
    fig.savefig(figures / "prediction_comparison.png")
    plt.close(fig)

    calibration = pd.read_csv(out / "calibration.csv")
    fig, axes = plt.subplots(2, 4, figsize=(13, 7), constrained_layout=True)
    for ax, mechanism in zip(axes.flat, MECHANISMS):
        ax.plot([0, 1], [0, 1], color="#94a3b8", ls="--", lw=1)
        for variant in ("inspection", "full", "manufacturing"):
            part = calibration[(calibration.split == "test") & (calibration.variant == variant) & (calibration.mechanism == mechanism) & (calibration.n > 0)]
            ax.plot(part.mean_probability, part.observed_fraction, "o-", color=COLORS[variant], label=NAMES[variant], markersize=4)
            if variant == "full":
                for row in part.itertuples():
                    ax.annotate(f"n={row.n}", (row.mean_probability, row.observed_fraction), xytext=(2, 4), textcoords="offset points", fontsize=7)
        ax.set(title=mechanism.replace("_", " "), xlim=(-.04, 1.04), ylim=(-.04, 1.04))
        ax.set_xlabel("Predicted probability")
        ax.set_ylabel("Observed synthetic fraction")
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles, labels, loc="center", frameon=False)
    fig.suptitle("Calibration assessment · full-model bin counts shown; sparse bins are uncertain")
    fig.savefig(figures / "calibration.png")
    plt.close(fig)

    part = decision[(decision.scenario == "base") & (decision.split == "test")]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8))
    fig.subplots_adjust(left=.085, right=.975, top=.86, bottom=.29, wspace=.34)
    for ax, xfield, xlabel in [(axes[0], "complete", "Evidence-complete fraction"), (axes[1], "nominal_hours", "Mean nominal procedure hours (not turnaround)")]:
        groups = {}
        for row in part.itertuples():
            groups.setdefault((round(getattr(row, xfield), 9), round(row.cost, 9)), []).append(row.arm)
        for index, ((x, y), arms) in enumerate(groups.items(), 1):
            color = COLORS[arms[0]] if len(arms) == 1 else "#2563eb"
            label = textwrap.fill(f"G{index}: " + "; ".join(NAMES[a] for a in arms), width=54)
            ax.scatter(x, y, color=color, s=70, label=label)
            ax.annotate(f"G{index}", (x, y), xytext=(7, -9), textcoords="offset points", fontsize=9)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Mean consumed resource cost, USD / case")
        ax.grid(alpha=.18)
        ax.legend(loc="upper center", bbox_to_anchor=(.5, -.17), fontsize=8, frameon=False)
        ax.xaxis.set_major_locator(MaxNLocator(4))
    axes[0].xaxis.set_major_formatter(PercentFormatter(1, decimals=3))
    axes[1].xaxis.set_major_formatter(FormatStrFormatter("%.4f"))
    fig.suptitle("Diagnostic trade-offs · all 137 test cases, including unresolved endings", y=.97)
    fig.savefig(figures / "diagnostic_tradeoffs.png")
    plt.close(fig)

    schedules = json.loads((out / "scheduling.json").read_text())
    fig, ax = plt.subplots(figsize=(10, 3), constrained_layout=True)
    for i, key in enumerate(("D_reference", "D_earliest_deadline")):
        for b in schedules["base"][key]["bookings"]:
            ax.barh(i, b["end"] - b["start"], left=b["start"], height=.4, color="#0f766e" if b["case_id"] == "A" else "#2563eb")
            ax.text((b["start"] + b["end"]) / 2, i, b["case_id"], color="white", ha="center", va="center")
    ax.axvline(2, color="#2563eb", linestyle="--", label="B deadline: 10:00")
    ax.axvline(3, color="#0f766e", linestyle="--", label="A deadline: 11:00")
    ax.set_yticks([0, 1], ["Reference: A first", "Deadline order: B first"])
    ax.set_xticks([0, 1, 2, 3, 4], ["08:00", "09:00", "10:00", "11:00", "12:00"])
    ax.set_xlim(0, 4)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Existing two-case CT fixture · both orders cost $240; deadlines assume conclusive reports")
    fig.savefig(figures / "scheduling.png")
    plt.close(fig)


def build_notebook(out, report_text):
    nb = nbformat.v4.new_notebook()
    setup = '''from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Image
RUN = Path.cwd()
if not (RUN / "run_manifest.json").exists():
    candidates = list(RUN.glob("artifacts/helion_pipeline/*/run_manifest.json"))
    if len(candidates) != 1:
        raise RuntimeError("Open this notebook with its containing run directory as the working directory")
    RUN = candidates[0].parent
manifest = json.loads((RUN / "run_manifest.json").read_text())
print(manifest["version"], "| synthetic research | not production qualified")'''
    nb.cells = [
        nbformat.v4.new_markdown_cell("# Helion pipeline walkthrough\n\nThis notebook reads the completed research run. It does not retrain, alter sources or turn simulated reports into observed data. The accompanying `benchmark_report.md` is the complete results report."),
        nbformat.v4.new_code_cell(setup),
        nbformat.v4.new_markdown_cell("## 1. What the model learns\n\nEach rejected stack has seven binary targets; coexisting faults are allowed. Probabilities describe fault hypotheses, not the best test or the probability of completing an investigation. Several acceptance predictors contain generator shortcuts, so compare full-context and manufacturing-only results."),
        nbformat.v4.new_code_cell('metrics = pd.read_csv(RUN / "predictive_metrics.csv")\ndisplay(metrics[(metrics.split == "test") & (metrics.mechanism == "macro")])\ndisplay(Image(filename=str(RUN / "figures/prediction_comparison.png")))'),
        nbformat.v4.new_markdown_cell("## 2. Calibration and limited evidence\n\nThe test partition has six die-crack cases and two cases with coexisting faults. Binned curves and bootstrap intervals describe this synthetic sample; they do not qualify future fab use."),
        nbformat.v4.new_code_cell('display(Image(filename=str(RUN / "figures/calibration.png")))\ndisplay(pd.read_csv(RUN / "predictive_paired_comparisons.csv"))'),
        nbformat.v4.new_markdown_cell("## 3. From predictions to eligible procedures\n\nThe evidence engine applies shared scope and destruction rules before selection. The mock rules choose triggered work first; CT-first rules and the model heuristic can advance completeness work. The heuristic values positive unresolved coverage per dollar, including the assumed gross-delamination fraction. It is not an optimal planner; negative evidence still matters for closure."),
        nbformat.v4.new_code_cell('walkthroughs = json.loads((RUN / "walkthroughs.json").read_text())\nrows = [{"case": name, **{k: item["summary"][k] for k in ["spent_cost", "pending_cost", "complete", "unresolved_count"]}} for name, item in walkthroughs.items() if "summary" in item]\ndisplay(pd.DataFrame(rows))\nfor name in ["B", "C", "C_inconclusive"]:\n    print(name, walkthroughs[name]["boundary"])\n    display(pd.DataFrame([{ "procedure": e["procedure"], "cumulative_cost": e["cumulative_cost"], "unresolved": ", ".join(e["unresolved_mechanisms"])} for e in walkthroughs[name]["events"]]))'),
        nbformat.v4.new_markdown_cell("## 4. Compare entire bounded investigations\n\nEvery started case stays in the denominator. A cheaper partial record is not cost-to-completion savings. The columns separate consumed and pending costs, diagnostic errors and unresolved mechanisms; manual-review continuation costs are unknown."),
        nbformat.v4.new_code_cell('decisions = pd.read_csv(RUN / "decision_metrics.csv")\ndisplay(decisions[(decisions.scenario == "base") & (decisions.split == "test")])\ndisplay(Image(filename=str(RUN / "figures/diagnostic_tradeoffs.png")))'),
        nbformat.v4.new_markdown_cell("## 5. Scheduling changes elapsed time independently of fault probability\n\nThe calendar ends after 24 hours. Case D compares A-first and B-first CT bookings with actual staff phases. Both consume $240; the B-first ordering meets the two scoped milestones if reports are conclusive. No future SEM slot is invented."),
        nbformat.v4.new_code_cell('display(Image(filename=str(RUN / "figures/scheduling.png")))\nscheduling = json.loads((RUN / "scheduling.json").read_text())\ndisplay(scheduling["base"]["B"])'),
        nbformat.v4.new_markdown_cell("## 6. Uncertainty and stress tests\n\nLot-cluster bootstrap uncertainty resamples cases by lot. Monte Carlo variation changes hypothetical reports while holding cases fixed. Rate, outcome and outage stresses change assumptions and are not confidence intervals. Correlated errors and narrower scope remain qualitative limitations."),
        nbformat.v4.new_code_cell('display(pd.read_csv(RUN / "decision_uncertainty.csv").query("split == \'test\' and metric in [\'cost\', \'complete\', \'missed_faults\']"))\ndisplay(decisions[(decisions.scenario != "base") & (decisions.split == "test")][["scenario", "arm", "cost", "complete", "missed_faults"]])'),
        nbformat.v4.new_markdown_cell("## 7. What would change the operational recommendation?\n\nActual SOP and repeat decisions, independent complete audits, validated procedure performance, qualified multi-day calendars and prospective comparative evidence. Neither retrospective classifier accuracy nor this synthetic replay establishes production readiness. Engineer closure and reviewed model release remain necessary."),
    ]
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python", "version": "3.12"},
                   "helion": {"source": "offline_research_run", "production_qualified": False}}
    nbformat.validate(nb)
    nbformat.write(nb, out / "pipeline_walkthrough.ipynb")


def build_report(root: Path, out: Path, config: dict):
    from .fixtures import walkthroughs
    ops = json.loads((root / config["operating_assumptions"]).read_text())
    write_json(out / "walkthroughs.json", walkthroughs(ops))
    decision = summarise_replay(out, config)
    predictive_uncertainty(out, config)
    metrics = pd.read_csv(out / "predictive_metrics.csv")
    make_figures(out, metrics, decision)
    test = decision[(decision.scenario == "base") & (decision.split == "test")].set_index("arm")
    macro = metrics[(metrics.split == "test") & (metrics.mechanism == "macro")]
    macro_index = macro.set_index("variant")
    context_ap_delta = macro_index.loc["full", "average_precision"] - macro_index.loc["inspection", "average_precision"]
    context_loss_delta = macro_index.loc["full", "binary_log_loss"] - macro_index.loc["inspection", "binary_log_loss"]
    context_interpretation = ("The full-context model does not improve either macro average precision or binary log loss over inspection/acceptance alone in these test point estimates."
                              if context_ap_delta <= 0 and context_loss_delta >= 0 else
                              "Prediction metrics show trade-offs; consult the paired intervals before interpreting incremental manufacturing-context value.")
    full, mock, rules = test.loc["full"], test.loc["mock"], test.loc["ct_first"]
    comparison_fields = ["cost", "complete", "correctly_complete", "unresolved_count", "false_absences", "false_positives", "missed_faults", "nominal_hours"]
    same_as_simple = np.allclose(full[comparison_fields].to_numpy(dtype=float), rules[comparison_fields].to_numpy(dtype=float), rtol=0, atol=1e-10)
    selection_interpretation = ("The full-model and CT-first rules arms have identical aggregate cost, completion, error and nominal-duration outcomes in the base test replay. This benchmark therefore demonstrates no incremental diagnostic value from the model over that simple rules comparator."
                                if same_as_simple else "The full-model and CT-first rules arms differ; evaluate their paired cost and quality differences together before attributing value to ML.")
    audits = json.loads((out / "synthetic_audits.json").read_text())
    training = json.loads((out / "training.json").read_text())
    uncertainty = pd.read_csv(out / "decision_uncertainty.csv")
    differences = uncertainty[(uncertainty.split == "test") & (uncertainty.reference == "mock") & uncertainty.metric.isin(["cost", "complete", "missed_faults", "incorrectly_complete"])]
    columns = ["cost", "pending_cost", "complete", "correctly_complete", "unresolved_count", "missed_faults", "false_absences", "false_positives", "attempts"]
    table = test[columns].reset_index()
    narrative = f"""# Helion model pipeline and diagnostic benchmark

**Executed offline research · synthetic data and operating assumptions · retrospective test partition**

## Result and interpretation

The full-context policy consumed **${full.cost:,.2f} per test case**, compared with **${mock.cost:,.2f} for the mock incumbent** and **${rules.cost:,.2f} for the CT-first rules comparator**. Its evidence-complete fraction was **{full.complete:.1%}**, compared with **{mock.complete:.1%}** and **{rules.complete:.1%}**, respectively. These are bounded-replay outcomes, including unfinished investigations—not measured fab savings or the cost of completing every investigation.

The full-context policy changes consumed cost by **{full.cost - mock.cost:+.2f} USD** and the complete fraction by **{100 * (full.complete - mock.complete):+.2f} percentage points** against the mock baseline. Judge these jointly with diagnostic errors and uncertainty below. No operating winner or production release is selected.

**{selection_interpretation}**

## Evidence and design boundary

- Supplied cohort: 916 synthetic rejected stacks; 653 train, 126 validation, 137 test. The seven simulator indicators are synthetic reference labels, not procedure findings.
- Test evidence includes six die-crack cases and two cases with coexisting faults. Test data had previously been inspected; this is retrospective evaluation.
- The original acceptance-failure benchmark targets a different decision and remains unchanged. It is not compared numerically with seven-fault prediction.
- MOCK-ENG-001 supplies the invented SOP comparator; SYN-OPS-001 supplies invented staff, dollar rates and report-error assumptions. Neither is validated Helion practice.
- Procedure histories, diagnostic effort, real audit membership and live calendars were not supplied. Newly generated records are explicitly simulated. {sum(audits['assignments'].values())} of 916 cases were independently assigned to the synthetic audit group, fixed across policies and report replications.
- Existing lot/time partitions are retained. Internal tuning uses the frozen expanding-lot folds with at least 21 days between fitting and scoring lot releases. Source chronology details in `validation.json` distinguish lot-release spacing from observed timestamp gaps; no genuine diagnostic-label availability timestamp exists.

## 1. Does manufacturing context improve fault prediction?

{context_interpretation} The full-minus-inspection differences are {context_ap_delta:+.4f} macro AP and {context_loss_delta:+.4f} binary log loss; higher AP and lower loss are preferred.

{markdown_table(macro, ['variant', 'average_precision', 'binary_log_loss', 'brier_score'])}

![Fault prediction comparison](figures/prediction_comparison.png)

One saved artifact contains alternative logistic pipelines with identical fitting protocols. Each has seven binary heads and training-only imputation, indicators, scaling and encoding. A shared C is chosen within training; no reweighting, oversampling or post-hoc calibration was fitted. Raw sigmoid probabilities are assessed rather than presumed calibrated. Per-label results, support, calibration-bin counts and paired full-minus-inspection bootstrap intervals are in the companion CSVs.

Acceptance-derived inputs have substantial synthetic shortcuts: interconnect failures equal the TSV-plus-microbump truth count, acceptance gates are functions of fault subsets, and other acceptance readings depend on generated faults. The manufacturing-only comparison removes the nine acceptance predictors. High performance does not establish real-fab discrimination. `timing_margin_ps`, post-investigation annotations, IDs and simulator internals are prohibited predictors.

![Calibration assessment](figures/calibration.png)

## 2. Do predictions improve diagnostic selection beyond rules?

{markdown_table(table)}

Cost is USD per started case. Complete/correctly-complete columns are fractions; fault and unresolved columns are counts per case. Every case remains in the denominator. Pending cost values currently identifiable unattempted procedures; it is not an estimate of unknown manual review or eventual completion.

The mock baseline performs triggered branches first. CT-first rules use the same safe procedure catalogue but may advance completeness work. The four heuristic arms use prevalence, inspection-only, full-context or manufacturing-only fault probabilities. They share the same evidence requirements, scope restrictions, report draws, audit assignment and one-attempt limit. This separates a simple rule improvement from predictive value.

The heuristic uses (1 − inconclusive probability) × predicted unresolved positive coverage / resource cost, with equal importance weights and 60% gross-delamination coverage for CT. It does not fully value negative findings, model expected continuation cost or establish an optimal sequence. Findings update evidence and eligibility; initial fault probabilities do not become automatically updated posteriors.

The base assumptions explain why changing probabilities may not change the procedure set. CT's delamination contribution is `0.90 × 0.60 × p(D) / 120 = 0.0045 × p(D)`; acoustic's is `0.85 × p(D) / 200 = 0.00425 × p(D)`. CT also receives greater void coverage per dollar and any unresolved warpage contribution. Consequently this particular heuristic ranks an eligible, unattempted CT ahead of acoustic. Learned scores can change other ordering without changing the evidence eventually collected. This is a consequence of the exercise's catalogue and heuristic, not a claim that ML can never help a real lab.

![Diagnostic cost and quality trade-offs](figures/diagnostic_tradeoffs.png)

The empirical nondominance table also considers unresolved questions, false absences, false positives, incorrect completion and nominal duration. Point-estimate nondominance is not evidence of statistical superiority. Identical procedure sets cost the same in any eligible order. A true delamination finding is useful; omitting required delamination investigation merely to reduce spending is not an equal-completeness comparator.

### Paired uncertainty against the mock baseline

{markdown_table(differences, ['arm', 'metric', 'paired_mean_difference', 'lot_bootstrap_low', 'lot_bootstrap_high', 'mc_standard_error'])}

The 95% percentile intervals use {config['bootstrap_samples']:,} paired lot-cluster bootstrap samples. Monte Carlo standard errors describe {config['replications']} repeated synthetic report draws on the same cases; they are reported separately. Neither quantifies uncertainty in the invented costs or procedure performance. All-case averages and audit/coexisting slices are supplied; rare slices require particular caution.

### Unresolved paths and truth errors

An inconclusive CT can leave warpage unresolved; electrical isolation can leave DRAM/base questions unresolved; SEM can leave microbump/crack questions unresolved. IR localisation does not resolve a mechanism. Contradictions remain pending review. Independent nondestructive branches may continue, but destructive preparation is not authorised while intact-sample evidence/review remains open. No independent repeat-success draws or free manual resolutions are invented.

An evidence-complete record may still be wrong because reports have synthetic false-positive and false-negative rates. Evaluation therefore uses hidden truth separately. The recommender never receives truth. Audit battery attempts, supported mechanism evidence and review requirements are distinct; an inconclusive audit is not a complete operational reference.

## 3. Can dispatch improve the existing scheduling example?

![Bounded CT scheduling](figures/scheduling.png)

In Case D, A-first misses B's 10:00 scoped milestone; B-first meets both milestones if conclusive. **Both orders cost $240.** Actual incumbent dispatch is unknown. These two cases demonstrate timing feasibility, not a quarterly turnaround gain. Staff phases, equipment occupancy and sample conflicts are checked, not merely machine availability.

Case A schedules CT 09:00–09:45 for $120. Case B schedules acoustic 09:00–10:30 and electrical isolation 12:00–16:00; with its prior $120 CT the illustrated cumulative cost is $920. SEM remains pending because the calendar ends at 24 hours. The $2,720 conclusive Case C path is a conditional nominal evidence/cost trace, not a future appointment. A stale calendar prevents new slot promises.

## Sensitivity and reproducibility

All six policies are replayed for all three partitions under base assumptions. Numerical stresses are evaluated on the test partition with paired report draws: staff/equipment rates ×0.75/1.25 (supplies unchanged), q ±0.05, sensitivity −0.05 and specificity −0.02. Scheduling separately tests a 2/4-hour extension of the existing CT outage. These are assumption stresses, not confidence intervals. Correlated report errors and narrower real examination scope remain qualitative limitations; no new distributions were invented.

Read `decision_metrics.csv` for base and stress outcomes, `replay_cases.parquet` for every case/arm/replication summary, and `replay_events.jsonl.gz` for every base-run recommendation and report. Stress reports are reproducible from recorded seeds and configuration. `run_manifest.json` records source/code checksums, dependencies and stage status. The single `model.joblib` must only be loaded from this trusted local run.

## Operational boundary and next evidence

These dollar values measure consumed resource capacity, not entirely avoidable cash. No salaries, equipment depreciation or full system ownership costs are claimed as cash savings. Queue delays are not monetised. Nominal procedure-hour totals are not actual turnaround time; no future roster or whole-cohort arrivals are fabricated.

No model release is qualified. The remaining evidence is the actual SOP/closure/repeat standard, representative complete audits, qualified diagnostic coverage and performance, observed operating costs, and fresh prospective comparisons. The independent 1-in-20 audit policy remains necessary; approximately 45 cases per quarter gives limited rare-mechanism evidence. Existing metrology sampling is unchanged. A valid recommendation remains to retain the rules if incremental ML value cannot be established.
"""
    (out / "benchmark_report.md").write_text(narrative)
    try:
        import mistune
        html = mistune.create_markdown(plugins=["table"])(narrative)
        (out / "benchmark_report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Helion benchmark</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#172033}table{border-collapse:collapse;font-size:13px;display:block;overflow:auto}td,th{padding:8px;border:1px solid #d5dce5;text-align:right}th{background:#eef2f6}img{max-width:100%}h1,h2,h3{line-height:1.2;color:#152846}code{background:#edf1f5;padding:2px 4px}a{color:#1260b3}</style><body>' + html + '</body></html>')
    except ImportError:
        pass
    build_notebook(out, narrative)
    return {"report": "benchmark_report.md", "notebook": "pipeline_walkthrough.ipynb", "production_qualified": False}
