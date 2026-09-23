# Helion: guided understanding and viva preparation

**Group 8 · Diagnostic-selection design, revised 22 September 2026**

Use this guide to defend the [canonical notebook](../design/P1_ml_systems_helion.ipynb#helion-context). These are team practice questions. Every member should understand the complete design and its evidence limits. [Assessment rubric](../brief/PRESENTATION_RUBRIC_APPRENTICE.md)

**Objective:** help the engineer select the next diagnostic procedure for a rejected stack, reducing investigation cost while maintaining adequate completeness. One seven-output model supports one next-test decision; the engineer approves procedures and closure. [Client objective and scope](../brief/helion_semiconductor_client_brief.md)

Keep brief facts, verified synthetic evidence, assumptions and unknowns distinct. The supplied cohort contains 916 rejected cases split 653/126/137, including 21 co-fault cases and 47 die-crack positives. Diagnostic histories and real complete-audit labels remain missing. The later offline research run is evidence about the supplied simulation. [Evidence inventory](../design/P1_ml_systems_helion.ipynb#helion-evidence) · [Research boundaries](../../helion_pipeline/README.md)

## 1. Vocabulary that changes the design

| Term | Meaning and consequence |
|---|---|
| Acceptance testing | Required for every assembled stack; diagnosis begins after rejection. |
| Diagnostic procedure | Investigates the mechanism; the stack is scrapped regardless. Findings inform process engineering. |
| Multi-label prediction | Faults coexist; seven probabilities need not sum to one. |
| Initial probability | Prediction from the initial snapshot; findings update evidence, not these probabilities. |
| Mechanism state | Untested, confirmed present, confirmed absent or inconclusive. Untested/inconclusive remain unresolved. |
| Inconclusive rate | Chance of not resolving the diagnostic question; distinct from sensitivity, specificity and fault probability. |
| Diagnostic policy | Recommends an eligible next test using costs, current evidence and required coverage. |
| Selective labels | Chosen procedures determine which faults receive findings; uninvestigated faults remain unknown. |
| Independent audit | A full diagnostic battery selected independently of model advice, supplying complete findings when conclusive. |
| Shadow study | Recommendations are logged while current practice continues; unused advice does not establish realised savings. |

Procedure context comes from the [brief](../brief/helion_semiconductor_client_brief.md); evidence handling and the policy are [design choices](../design/P1_ml_systems_helion.ipynb#helion-policy).

## 2. Understand the decision before modelling

1. Identify the rejected-stack checkpoint and the engineer's next-test decision.
2. Trace ordinary, co-fault and inconclusive investigations through the actual SOP.
3. Record evidence provenance, availability times and the distinction between unknown and confirmed-negative findings.
4. Establish the completeness standard, qualified procedure coverage and comparable costs.
5. Compare the recommendation with the rules using the same information and evidence obligations.
6. Revisit assumptions when new process conditions or audit outcomes change their support.

These are proposed investigation steps; no stakeholder interviews or operational approvals are claimed. [Evidence gaps](../design/P1_ml_systems_helion.ipynb#helion-evidence)

## 3. Decision register to defend

| Decision | Why; alternative | Reopen when |
|---|---|---|
| One regularised model artifact with seven logistic heads | Coexisting faults require independent outputs; simple baseline for limited labels. | Qualified evidence supports a more complex candidate. |
| Nightly initial scores and current local findings | Matches nightly MES availability; findings update procedure eligibility. | Qualified new inputs arrive between imports and immediate predictions are useful. |
| Cost-aware coverage ranking | Reviewable heuristic; incompletely values negative findings. | Procedure/outcome evidence supports a better next-test policy. |
| Engineer approval and no automatic closure | Low probability cannot establish fault absence. | The qualified completeness standard changes. |
| Independent audits and lot/time separation | Supports meaningful negative labels and leakage control. | Evidence supports an alternative approach to selectively observed labels. |
| Reviewed releases and SOP fallback | Supports air-gapped operation and qualified recovery. | Fab requirements or the approved software environment change. |

These choices are documented in the [blueprint](../design/P1_ml_systems_helion.ipynb#helion-blueprint), [data design](../design/P1_ml_systems_helion.ipynb#helion-data) and [operating design](../design/P1_ml_systems_helion.ipynb#helion-operations).

## 4. Explain the next-test policy

For stack `i` and eligible procedure `t`:

`R_i(t) = (1 − q_t) × Σ[w_m × p_im] / c_it`

Sum over unresolved mechanisms within the procedure's validated coverage. Here `q_t` is inconclusiveness, `p_im` is the unchanged initial fault probability, `w_m` is an approved importance weight and `c_it` is a positive, comparable procedure cost. Equal weights are illustrative. Missing costs require the qualified SOP route. [Policy definition](../design/P1_ml_systems_helion.ipynb#helion-policy)

This is weighted positive-fault coverage per cost, not information gain or the probability of completing the diagnosis. It incompletely values negative findings. Required evidence and destructive-test prerequisites override the score. Do not add money, duration and a destruction flag directly, or charge labour twice. [Policy limitations and cost accounting](../design/P1_ml_systems_helion.ipynb#helion-evaluation)

The engineer reviews the next-test recommendation and alternatives. After the result, update only supported mechanism states, retain unresolved obligations and recompute eligibility. An inconclusive result is neither a negative label nor permission to stop. The initial probabilities stay fixed. [Evidence transitions](../design/P1_ml_systems_helion.ipynb#helion-policy)

## 5. Walk through the difficult cases

These are hypothetical examples from the [worked cases](../design/P1_ml_systems_helion.ipynb#helion-worked-cases).

- **Suspected warpage:** offer eligible X-ray with its rationale; a positive result leaves other mechanisms unresolved. The rules may choose the same test.
- **TSV plus microbump:** a TSV confirmation leaves microbump untested. Preserve required evidence before an authorised cross-section.
- **Inconclusive acoustic test:** retain the consumed cost and unresolved delamination; use the qualified repeat/alternative path.
- **Missing metrology:** preserve expected sampling gaps and their reasons. Missing required acceptance records makes the checkpoint unsupported and exposes SOP fallback.
- **Failed nightly import:** show no fresh model advice; retain existing findings and let the engineer follow SOP while the import is recovered.
- **New supplier or bonder:** use SOP for unqualified conditions and review applicability against independent audit evidence.

The [costed walkthrough](../design/workflow_walkthrough.md) adds three paper cases covering CT choice, acoustic/electrical evidence and completion including a co-fault.

## 6. Practice the seven assessment dimensions

**1 — Framing: Why use ML?** The model must change next-test choices enough to improve investigation cost or effort at the same completeness standard. If rules suffice, retain them. [Framing](../design/P1_ml_systems_helion.ipynb#helion-context)

**2 — Metrics: What counts as success?** Compare investigation cost, required procedures and diagnostic completeness on the same cases. Track missed co-faults and unresolved cases; per-fault recall, AP and calibration are supporting prediction metrics. Labour and machine costs remain components of procedure cost. [Evaluation](../design/P1_ml_systems_helion.ipynb#helion-evaluation)

**3 — Data: What can the files establish?** They support a synthetic experiment. Preserve lot/time splits and train-only preprocessing, exclude later annotations and simulator internals, and retain unknown labels. Real qualification needs independent complete audits. [Data controls](../design/P1_ml_systems_helion.ipynb#helion-data)

**4 — Serving: Why nightly scoring?** Inputs consolidate nightly inside an air-gapped fab. Current findings update next-test eligibility between batches. Unsupported inputs use SOP. [Architecture](../design/P1_ml_systems_helion.ipynb#helion-blueprint)

**5 — Feedback: Could recommendations bias labels?** Yes: fewer selected acoustic tests can reduce recorded delamination findings without reducing actual faults. Compare independent full-battery audits and retain pending audit cases in reporting. Confirmed model-related drift or a qualified process change plus an approved audited dataset/protocol opens reviewed candidate training. [Monitoring](../design/P1_ml_systems_helion.ipynb#helion-operations)

**6 — Trade-offs: Why keep the policy simple?** Limited labels and incomplete procedure-outcome evidence favour a reviewable candidate. The coverage/cost heuristic exposes its limits; human approval and SOP fallback remain available. [Policy](../design/P1_ml_systems_helion.ipynb#helion-policy)

**7 — Defence: Does model-driven ordering create value?** Reordering an almost unchanged concern set does not lower fixed execution cost. Under v2 the full model changes about 5.9% of sequences, costs $1.66 more per case and does not materially change completion. Savings need qualified alternative paths, repeat handling or evidence of better outcomes at comparable quality. [Research interpretation](../../artifacts/helion_pipeline/research_v2_concern_closure/benchmark_report.md)

## 7. Team rehearsal

Each member should redraw the three-part architecture, explain the six diagnostic cases and distinguish proposed fab operation from the executed synthetic experiment. Rehearse the evidence for each claim, the relevant alternative and what would change the decision. Retaining the existing rules must remain a defensible outcome. [Assessment rubric](../brief/PRESENTATION_RUBRIC_APPRENTICE.md)
