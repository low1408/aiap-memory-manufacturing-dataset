# Viva Pre-Read: Helion Semiconductor

**Team:** Group 8; members to complete. **Status:** design only; no measured savings.

**Scope:** One model, one next-test decision: help the engineer select the next diagnostic procedure for each rejected stack. [Brief](../problem-statement/helion_semiconductor_client_brief.md)

## A. Design blueprint

- [x] **Problem:** Tell the process engineer which diagnostic test (among the 5) to run, given the cost associated with each test (i.e. manpower and machine and other cost), and the time/cost is provably lowered (compared to the baseline rule-based system), while ensuring diagnostic coverage is adequate.

- [x] **Cost of error:** Precision contingent on mantaining the seem False Negative rate as the pre-existing rule-based system.

- [x] **Data:** Use versioned and acceptance-test inputs, with independently audited fault labels (1 in 20 full audit). Preserve unknown findings and missingness reasons. Exclude post-investigation information and retain lot/time splits. Collect procedure findings and costs to evaluate diagnostic test selection.

- [x] **Training:** Reproducibility and tracking can be achieved by logging software like MLFlow. Config and modular training is achieved by using pipeline (loader -> preprocessor -> trainer), with hyperparameter and configs (like variable values like the cost of manpower which is subject to change) configurable in a .yaml file.


- [x] **Evaluation:** Macro-precision ultimately informed by the average cost per diagnostic test. Slice by Multi-fault Stacks vs single fault stack in order to benchmark models ability to classify multi-errors vs single errors, same for 8/12-high HBM.

- [x] **Serving:** Batch serving nightly, because the data comes in nightly.


- [x] **Monitoring:** MLFlow. Performance degradation (based of eval score), and concept drift and data drift.


- [x] **Deliberately lean:** Assume that testing machines are ~100% accurate and regularly maintained. Focus on the next diagnostic test for each rejected stack.

### Architecture sketch

![Helion architecture overview: nightly scoring, diagnostic test selection, engineer review and the audit feedback loop](images/helion-architecture.png)

[Three separate detail views](architecture.md) · [Editable Mermaid](images/helion-architecture.mmd) · [Vector SVG](images/helion-architecture.svg)

## B. Key reasoning

**1. Framing & fit:** Tell the process engineer which diagnostic test (among the 5) to run, given the cost associated with each test (i.e. manpower and machine and other cost), and the time/cost is provably lowered (compared to the baseline rule-based system), while ensuring diagnostic coverage is adequate.

**2. Cost & metric:** Precision contingent on mantaining the seem False Negative rate as the pre-existing rule-based system. A False Positive  

**3. Data & leakage:** Exclude post-investigation annotations, simulator internals and synthetic `timing_margin_ps`. Untested/inconclusive mechanisms remain unresolved. Roughly 45 complete audits/quarter limit rare-fault evidence. [Premise](../../problem-statement/helion_semiconductor_client_brief.md)

**4. Serving fit:** Score validated MES inputs in a nightly batch. New diagnostic findings update the case's evidence and eligible next tests; the engineer confirms the procedure and closure. Missing or unsupported inputs use the existing SOP. [Serving design](P1_ml_systems_helion.ipynb#helion-blueprint)

**5. Monitoring & loop:** Independent audits counter selective labels. Monitor input validity, missingness, inconclusive findings, overrides and audited model performance. Confirmed model-related drift or a qualified process change, together with an approved audited dataset and evaluation protocol, triggers reviewed candidate training. [Monitoring design](P1_ml_systems_helion.ipynb#helion-operations)

**6. Trade-offs:** Validation, reliability and observability outrank complexity. Neither an inconclusive test nor a first confirmed fault authorises stopping. Missing procedure prerequisites or costs require the engineer to follow the existing SOP. [Decision policy](P1_ml_systems_helion.ipynb#helion-policy)

## C. Before submission

- [x] Eight decisions, six answers, diagram; detail in [notebook](P1_ml_systems_helion.ipynb).
- [ ] Supply names and rehearse; submit the day before. [Rubric](../problem-statement/PRESENTATION_RUBRIC_APPRENTICE.md)
