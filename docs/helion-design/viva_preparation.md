# Helion: guided understanding and viva preparation

**Group 8 · Design proposal · No trained model or measured diagnostic savings**

Use this guide to understand and defend the design in the [canonical notebook](P1_ml_systems_helion.ipynb#helion-context). These are **practice questions created for the team, not the mentor question bank**. The assessment is a short presentation followed by individual oral defence; a working pipeline is optional. Each team member should be able to explain the whole system, including its limitations. [Assessment rubric](../../problem-statement/PRESENTATION_RUBRIC_APPRENTICE.md)

Keep three kinds of statement separate throughout the discussion:

- **Brief fact:** a condition of the fictional client scenario, such as nightly MES consolidation.
- **Observed package evidence:** something checked in the supplied synthetic files, such as the rejected-stack count. This is not production evidence.
- **Proposed design or assumption:** something the team recommends or assumes for investigation, such as the procedure-ranking heuristic. It remains subject to validation and qualification.

Our present recommendation is to retain the qualified procedure, define missing diagnostic evidence and collect it, then consider a qualified shadow study. A need for ML and a reduction in diagnostic effort remain unproved. [Evidence and recommendation](P1_ml_systems_helion.ipynb#helion-evidence)

The supplied package contains 17,793 synthetic stacks, with 916 rejected cases split 653/126/137 into train/validation/test; 21 rejected cases have multiple faults and 47 have die crack. Procedure history, diagnostic hours and the full-battery flag are absent. The older binary benchmark is not diagnostic-policy evidence. [Package scope](../../README.md)

## 1. Vocabulary that changes the design

| Term | Meaning here—and why it matters |
|---|---|
| Acceptance testing | Required testing of assembled stacks. It still happens for every stack. Our decision begins after rejection. |
| Diagnostic procedure | An additional investigation into why a rejected stack failed. The stack is scrapped either way; useful diagnosis informs process engineering. |
| Failure mechanism | A physical/electrical failure category, such as TSV open/short. Identifying it does not establish its manufacturing root cause. |
| Multi-label prediction | Several mechanisms may be present together. Seven probabilities need not sum to one; confirming one does not eliminate another. A 0.5 cutoff is not an automatic decision rule. |
| Initial probability | The proposed model's score from the initial feature snapshot. It remains an initial score after subsequent tests; the design does not calculate posterior probabilities. |
| Investigation state | For each mechanism: untested, confirmed present, confirmed absent or inconclusive. Only qualified diagnostic evidence changes presence/absence. |
| Selective labels | Engineers observe findings only for tests they choose. An uninvestigated mechanism is unknown, not a negative training example. |
| Full-battery audit | Independently selected cases receiving the complete diagnostic battery. This is the reference for completeness, not the normal cost baseline. |
| Calibration | Whether predicted probabilities agree with observed frequencies in suitable reference cases. It is different from correctly ranking cases. |
| Leakage | Information reaching a model that would not legitimately be available at its decision point, including later investigation annotations. |
| Shadow study | Record recommendations without allowing them to change the investigation. It can test feasibility and disagreements, but cannot establish causal hours saved. |
| Qualification | Controlled approval of a software/process version for fab use. An improved offline metric does not itself authorize release. |

The client supplies the testing context, coexistence concern and audit arrangement; the notebook specifies the proposed model and state handling. [Client brief](../../problem-statement/helion_semiconductor_client_brief.md) · [Policy design](P1_ml_systems_helion.ipynb#helion-policy)

## 2. An onboarding algorithm: update context around decisions

Your context is a maintained account of the objective, people, workflow, evidence, constraints, uncertainties and decisions. Full understanding is not a finish line: seek enough verified context for the next decision, then keep updating it.

1. **Name the pending decision.** Write who acts, when, on what and toward which outcome. For Helion: the on-duty quality engineer chooses the next additional diagnostic procedure for a rejected stack. Avoid drifting into predicting acceptance failure, repairing stacks or controlling recipes. **Output:** one decision statement and scope boundary. [Framing](P1_ml_systems_helion.ipynb#helion-context)
2. **Map the people and their definitions of success.** Identify the quality manager, shift engineer, process engineering, data owner and fab IT/qualification owners. Establish who can authorize procedure changes, define completeness and resolve data failures. These are proposed responsibilities to confirm, not interviews already conducted. **Output:** an owner for every consequential decision and unknown. [Operations](P1_ml_systems_helion.ipynb#helion-operations)
3. **Trace a case through the real workflow.** Start at acceptance failure; follow measurements, test choice, findings, repeats, escalation and closure. Ask where documents differ from practice. In this package, tracing is a design exercise because real diagnostic events are missing. **Output:** a workflow with timestamps, handoffs and evidence boundaries. [Evidence inventory](P1_ml_systems_helion.ipynb#helion-evidence)
4. **Inventory claims and their support.** For each material claim, record source, date/version, evidence type and limitation. Example: “916 rejected stacks” is synthetic file evidence; “900 per quarter” is the brief's operational scenario; “45 audits per quarter” is arithmetic from the scenario, not a measured dataset count. **Output:** a claim register that keeps these statements distinct. [Supplied-data scope](../../README.md)
5. **Find contradictions before proposing fixes.** The brief describes selective diagnostic findings, but delivered labels are complete simulator truth. It requests next-test selection, while a fault classifier alone provides probabilities. Write each gap as a question or design requirement instead of silently treating it as resolved. **Output:** prioritized uncertainty and assumption lists. [Traceability](P1_ml_systems_helion.ipynb#helion-traceability)
6. **Investigate what could change the decision.** Prioritize unknowns by consequence, uncertainty and cost of checking. Qualified coverage and closure rules matter more than choosing a sophisticated classifier: without them, neither recommendations nor savings are defensible. **Output:** the smallest next evidence collection that could change the recommendation. [Evaluation gates](P1_ml_systems_helion.ipynb#helion-evaluation)
7. **Explain back, decide provisionally, and refresh.** Have relevant owners check your account. Record the decision, reason, alternative and reopening trigger. New evidence should update dependent decisions, not merely be appended to notes. A new supplier, for example, reopens qualification and applicability, not automatically the model algorithm. **Output:** a versioned context and decision register. [Operations](P1_ml_systems_helion.ipynb#helion-operations)

Before acting, ask: *Can I explain a typical case, distinguish evidence from assumptions, identify what could make my recommendation wrong, and name the evidence that would change it?* This checkpoint transfers to a new company, project or unfamiliar problem.

## 3. Decision register to defend

These are **proposed choices**, not implemented capabilities. Owners are roles to confirm and share within the existing four-engineer team.

| Decision | Rationale and rejected alternative | Reopen when / proposed owner |
|---|---|---|
| One regularised multi-label logistic artifact with seven sigmoid heads | A simple candidate for limited data. Softmax would wrongly force mutually exclusive faults; independent heads still do not model joint fault probabilities. | Audited evidence supports a material improvement from another candidate / model owner. |
| Nightly batch scores; immediate local policy updates | Fits nightly consolidated inputs while allowing findings to change eligible procedures. No new inference or Bayesian update follows each test. | Qualified data freshness or workflow requirements change / data owner and IT. |
| Coverage/time heuristic for eligible unperformed nondestructive tests | Transparent initial policy to examine. It is not optimal information gain or validated sensitivity. | Approved coverage/cost evidence changes / lab and quality owners. |
| No autonomous stop | Probability is not qualified negative evidence; coexisting faults matter. | Only through approved closure standards, not a convenient score threshold / quality owner. |
| Audit-based operational fitting and evaluation | Representative complete findings support interpretable negatives. Masking selective labels alone does not remove selection bias. | A validated bias-correction design and sufficient evidence exist / evaluation owner. |
| Exclude timing-margin shortcut initially | Availability after acceptance does not establish physical realism. | Qualified measurement evidence supports it / data and model owners. |
| Equal-input incumbent baseline | ML must add value beyond existing measurements and rules. Full-battery cost is not normal practice. | Qualified incumbent procedure changes / quality owner. |
| Reviewed, qualified releases with SOP fallback | Supports an air-gapped environment and unattended night shifts. No automatic promotion. | Fab qualification requirements change / quality and IT. |

Sources and detailed reasoning: [Policy](P1_ml_systems_helion.ipynb#helion-policy) · [Data](P1_ml_systems_helion.ipynb#helion-data) · [Evaluation](P1_ml_systems_helion.ipynb#helion-evaluation) · [Operations](P1_ml_systems_helion.ipynb#helion-operations).

## 4. Walk through the difficult cases

The following are **invented walkthroughs**, not observed investigations. Any probabilities are illustrative. Actual eligibility, coverage and closure require qualified SOP definitions that the package does not supply. [Worked cases](P1_ml_systems_helion.ipynb#helion-worked-cases)

**A. A straightforward suspected fault.** Suppose initial warpage probability is high and X-ray is eligible. The policy can recommend X-ray using its approved coverage, duration and inconclusive rate. The engineer follows the SOP; a qualified finding changes warpage to confirmed present. Other mechanisms remain unresolved until their evidence satisfies the closure standard. The engineer closes only under that standard. An accurate suggestion does not establish added value if the existing warpage rule would have chosen the same test.

The illustrative ranking is `R(t) = (1 − q_t) × Σ p_m / d_t`, summed only over unresolved mechanisms the eligible unperformed nondestructive procedure can resolve. Here `q_t` is the brief's inconclusive rate, not its false-negative rate; `d_t` must use comparable approved duration units. Equal mechanism weights are an assumption. Required steps override the ranking; ties follow incumbent order. Thermal/IR localisation alone cannot confirm absence. [Policy definition](P1_ml_systems_helion.ipynb#helion-policy)

**B. Coexisting TSV and microbump faults.** Electrical isolation confirms a TSV fault. Mark that finding present; do not reduce the microbump probability or treat it as disproved. The remaining state drives the next permitted procedure. If cross-section is required, preserve evidence, meet prerequisites and obtain engineer sign-off. Its “two days” is not converted into engineer-hours or inserted into the nondestructive ranking. The lesson: finding one plausible cause is not evidence of completeness. [Coexistence and procedure table](../../problem-statement/helion_semiconductor_client_brief.md)

**C. An inconclusive acoustic examination.** Record the procedure and its effort; delamination remains unresolved. Do not record a negative label or blindly repeat the same test. The next action is the qualified repeat or alternative pathway. The initial scores remain unchanged; the policy uses the updated state and eligibility. If an approved pathway or required procedure metadata is unavailable, abstain to SOP. The investigation remains in evaluation, including effort already spent and unresolved status. [Policy](P1_ml_systems_helion.ipynb#helion-policy) · [Evaluation](P1_ml_systems_helion.ipynb#helion-evaluation)

**D. Missing sampled metrology versus unavailable acceptance results.** A die not selected for detailed metrology is an expected sampling condition. Preserve its reason and measurement coverage; apply approved preprocessing with imputation fitted on training data. Instrument dropout and an inapplicable process stage are distinct states. By contrast, missing required acceptance observations means the checkpoint or feature contract is not established. Do not impute your way into a recommendation that assumes rejection has been confirmed: flag the case and use SOP until its inputs qualify. [Data boundary](P1_ml_systems_helion.ipynb#helion-data)

**E. Failed nightly import.** Suppose the batch fails validation or no successful batch exists by scheduled handover. Under the proposed default, produce no new ML recommendations, display the failure and SOP fallback, and route investigation to IT and the data owner. Do not silently carry stale scores forward. Versioned records support investigation of the failure; recovery requires a successful qualified input path. This response is a team proposal, not an observed outage or quoted client rule. [Operational defaults](P1_ml_systems_helion.ipynb#helion-operations)

**F. New supplier or tool.** A stack belongs to an unqualified tool/material combination. Apply affected-case fallback and request process/qualification review. A shift in input distribution alone does not prove model deterioration; audit outcomes may reveal a changed relationship between inputs and mechanisms. Candidate retraining requires confirmed model-related drift or a qualified process change **and** an owner-approved versioned audited dataset, split and evaluation protocol. Quality and IT approve promotion; rollback remains available. The brief anticipates both a new bonder and underfill supplier, but their future performance is unknown. [Client changes](../../problem-statement/helion_semiconductor_client_brief.md) · [Monitoring](P1_ml_systems_helion.ipynb#helion-operations)

## 5. Practice across all seven assessment dimensions

For each question, answer aloud first, then open the cited section. Explain the alternative as fairly as your chosen design. These answers describe proposals and evidence limits, not personal project experience.

**1 — Problem framing and fit: “Why does this need ML?”**

- **Short answer:** We have not established that it does. The hypothesis is that combined measurements improve next-procedure selection beyond incumbent rules, at unchanged approved completeness. A multi-label model is only a candidate component.
- **Source:** [Framing](P1_ml_systems_helion.ipynb#helion-context) and [equal-input comparison](P1_ml_systems_helion.ipynb#helion-evaluation).
- **Alternative:** Keep the qualified rules, perhaps improving their documentation and event capture.
- **What changes the decision:** Fresh evidence of useful incremental workflow benefit after overhead, with completeness maintained. If rules suffice, retain them.

**2 — Cost of error and metrics: “What would count as success?”**

- **Short answer:** Lower mean hands-on engineer diagnostic hours per eligible rejected case at the same client-approved completeness. Report elapsed/equipment time separately and track missed or incorrect findings, co-fault misses, unresolved cases, repeats and overrides. Include unclosed cases and effort-to-date. We have no justified fixed false-negative:false-positive cost ratio.
- **Source:** [Endpoints and economics](P1_ml_systems_helion.ipynb#helion-evaluation).
- **Alternative:** Optimise predictive average precision as an exploratory model measure; it cannot alone justify deployment.
- **What changes the decision:** Agreed completeness margin, trustworthy effort records, comparable baseline data and sufficient prospective evidence. Changing order alone does not establish summed-effort savings.

**3 — Data and pipeline: “Can you train on every diagnosis?”**

- **Short answer:** Not as fully observed truth. Untested and inconclusive labels remain unknown. The initial operational proposal uses independently selected complete audits pooled over quarters for fitting and evaluation; selective records support descriptive operations and audit comparison. Synthetic truth can illustrate the design, not qualify it.
- **Source:** [Label and feature contracts](P1_ml_systems_helion.ipynb#helion-data).
- **Alternative:** Use selectively observed labels with a carefully justified bias-correction method. Simply masking missing labels does not establish unbiased learning.
- **What changes the decision:** Sufficient provenance and a validated correction design. At 45 expected complete audits per quarter, rare-fault evidence is sparse; no rapid guarantee is justified.

For scale only: if synthetic rates transferred, 45 audits would contain approximately `45 × 47/916 = 2.3` die-crack cases and `45 × 21/916 ≈ 1` co-fault case. These are illustrative expectations, not observed audit counts; pooled evidence still needs time/lot-aware splits and uncertainty reporting. [Evidence limitations](P1_ml_systems_helion.ipynb#helion-evaluation)

Also rehearse the feature boundary: initial acceptance observations can be available here; closure annotations, later reliability, `fault_*` and simulator `p_*` cannot be predictors. Exclude the generated timing-margin shortcut initially. Preserve lot/time partitions and 21-day embargoes, fit preprocessing on training data only, and treat the previously examined test set as retrospective. [Data controls](P1_ml_systems_helion.ipynb#helion-data)

**4 — Serving and deployment: “Why batch when the engineer needs help now?”**

- **Short answer:** Initial inputs consolidate nightly. Batch inference creates versioned initial scores; the local interface can immediately update deterministic procedure ranking from current findings. This is not repeated model inference. Missing or unqualified inputs lead to visible SOP fallback.
- **Source:** [Architecture and blueprint](P1_ml_systems_helion.ipynb#helion-blueprint).
- **Alternative:** Qualified on-demand inference if sufficiently fresh inputs become available and workflow benefit justifies it.
- **What changes the decision:** Verified latency requirements and data availability. CPU-only local packaging is a proposal subject to IT qualification, not a demonstrated deployment.

**5 — Monitoring and feedback: “What if recommendations teach the model its own mistakes?”**

- **Short answer:** Recommendations affect which findings are recorded. Preserve independent full-battery audits, label provenance, procedures and overrides. A proposed trigger is to suspend the affected recommendation policy for quality review after any audit-confirmed missed co-fault potentially attributable to it. No automatic retraining or promotion follows.
- **Source:** [Feedback and monitoring controls](P1_ml_systems_helion.ipynb#helion-operations).
- **Alternative:** Retrain frequently on all observed labels; this could reinforce selective observation and is rejected initially.
- **What changes the decision:** Qualified process/drift evidence plus approved audited data and evaluation gates; release still requires quality and IT approval.

**6 — Trade-offs and prioritisation: “Why not reinforcement learning or an optimal test policy?”**

- **Short answer:** We lack reliable sequential procedure outcomes, qualified costs and sufficient complete labels. We prioritise validation, reliability and observability. The transparent heuristic is intentionally limited and must not be described as optimal information gain.
- **Source:** [Policy limitations](P1_ml_systems_helion.ipynb#helion-policy) and [readiness gates](P1_ml_systems_helion.ipynb#helion-evaluation).
- **Alternative:** A richer sequential policy after collecting representative transitions and consequences.
- **What changes the decision:** Evidence that current simplicity materially limits value, plus sufficient data, maintenance capacity and validation for added complexity.

**7 — Live defence: “You promised savings, but every required test still runs. Defend that.”**

- **Short answer:** That would invalidate a claim of reduced summed procedure effort. We claim no measured savings. Optional redundant work might eventually be avoided under an approved completeness standard; presently that is a hypothesis. Shadow results cannot prove causal savings.
- **Source:** [Evaluation and limits](P1_ml_systems_helion.ipynb#helion-evaluation).
- **Alternative:** Retain SOP and use shadow work solely to establish feasibility and collect evidence.
- **What changes the decision:** A sufficiently supported, approved, lot-block controlled pilot with prespecified completeness and economic evaluation. If underpowered or unresolved, hold deployment and state the limitation plainly.

## 6. Team rehearsal and ownership

- Rotate the ten-minute walkthrough and individual question roles; do not let knowledge reside only with the presenter.
- Have every member redraw the architecture and trace a case from nightly input through findings, audit, monitoring and reviewed release.
- Practise distinguishing brief facts, checked synthetic evidence and assumptions without reading a script.
- Reconcile every numeric claim and threshold with the notebook; remove claims of training, deployment or measured savings.
- Assign named team owners before submission for evidence checks, policy reasoning, evaluation and operations. These are shared responsibilities, not four additional jobs.
- Rehearse “we do not yet know” followed by the missing evidence, its consequence and the next check. Do not invent interviews, deployments or personal experience.
- Before submission, confirm the group can defend completeness, selective labels, scarcity, fallback and the conditions for retaining rules.

The target is shared ownership of the reasoning. A polished answer that a teammate cannot explain does not meet the spirit of the [oral-defence rubric](../../problem-statement/PRESENTATION_RUBRIC_APPRENTICE.md).
