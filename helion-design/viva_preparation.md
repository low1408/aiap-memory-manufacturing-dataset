# Helion: guided understanding and viva preparation

**Group 8 · Broader design proposal, revised 21 September 2026 · No implemented model or scheduler, or measured savings**

Use this guide to defend the [canonical notebook](P1_ml_systems_helion.ipynb#helion-context). These are **team practice questions, not the mentor question bank**. Every member should understand the whole proposal. The assessment rewards design reasoning and individual oral defence; building is optional. [Assessment rubric](../../problem-statement/PRESENTATION_RUBRIC_APPRENTICE.md)

**Objective:** minimise expected operational cost of completing diagnostically adequate investigations across rejected stacks, subject to completeness, safety, evidence preservation, resource feasibility and approved turnaround/maximum-wait constraints. Report turnaround separately. Until comparable costs exist, report engineer time, equipment time and elapsed time separately; do not claim total-cost improvement.

The user requested this broader framing on 21 September 2026. It introduces **two coordinated decisions**: eligible next-test alternatives for each stack, and equipment/time assignments across stacks. One proposed seven-output model supports selection; a deterministic constraint-based scheduler allocates work. This expands the original brief's “one model, one decision” boundary; mentor/client acceptance of the expansion remains unconfirmed. [Original scope](../../problem-statement/helion_semiconductor_client_brief.md#constraints--scope) · [Proposed scheduling](P1_ml_systems_helion.ipynb#helion-scheduling)

Keep **brief facts**, **verified synthetic-file evidence**, **proposed assumptions** and **unknowns** distinct. The package contains 17,793 synthetic stacks, including 916 rejected cases split 653/126/137 for training/validation/test; 21 rejected cases have coexisting faults and 47 have die crack. Procedure history, diagnostic hours and the full-battery flag are absent. Operational scheduling records are also missing; assembly tool IDs are not a diagnostic-resource inventory. The older binary benchmark proves neither selection nor scheduling benefit. [Package scope](../../README.md) · [Evidence inventory](P1_ml_systems_helion.ipynb#helion-evidence)

The current action is to retain qualified practice, collect the missing evidence, and assess readiness for a qualified shadow study. The integrated design is a proposal, not evidence that either component is needed.

## 1. Vocabulary that changes the design

| Term | Meaning and consequence |
|---|---|
| Acceptance testing | Required for every assembled stack. Our workflow begins after rejection. |
| Diagnostic procedure | Investigates why a rejected stack failed. The stack is scrapped regardless; findings inform process engineering. |
| Failure mechanism | Physical/electrical fault category. Confirmation does not establish its manufacturing root cause. |
| Multi-label prediction | Faults can coexist. Seven probabilities need not sum to one; one positive does not eliminate others. |
| Initial probability | Model output from the initial snapshot. Results update qualified evidence and state, not these probabilities; no posterior model is proposed. |
| Mechanism state | Untested, confirmed present, confirmed absent or inconclusive. Untested and inconclusive both belong to the unresolved set. |
| Inconclusive rate | Chance of consuming resources without resolving the diagnostic question; not sensitivity, specificity or fault probability. |
| Diagnostic policy | Produces justified eligible alternatives, unresolved coverage and mandatory obligations for each stack. |
| Scheduler | Assigns selected alternatives to compatible resources and time slots, respecting shared constraints. |
| Rolling horizon | Replan future assignments as results and resource conditions change; protect work already underway and accepted frozen reservations. |
| Selective labels | Only chosen procedures produce findings. Uninvestigated mechanisms are unknown, not negative labels. |
| Independent full-battery audit | Complete findings from cases selected independently of recommendations. Protect its work from scheduling priority effects. |
| Shadow study / qualification | Shadow recommendations do not control work or establish causal savings. Qualification authorises a version for fab use. |

Procedure context and audit obligations come from the [brief](../../problem-statement/helion_semiconductor_client_brief.md); state handling, coupling and qualification workflow are [proposed design](P1_ml_systems_helion.ipynb#helion-policy).

## 2. An onboarding algorithm: update context around decisions

1. **Name the decisions and boundaries.** Identify who chooses tests and who allocates scarce equipment. Distinguish the requested broader objective from the original assignment. Acceptance prediction, repair and recipe control remain outside this proposal. **Output:** objective, scope and decision owners.
2. **Map people and competing goals.** Quality owns completeness; engineers validate procedures and closure; an existing lab coordinator or designated shift lead approves dispatch; IT/data owners maintain records. These are proposed responsibilities, not completed interviews or additional hires. **Output:** owners and disagreements to resolve.
3. **Trace actual cases and resource handoffs.** Follow rejection, test eligibility, queues, reservations, findings, repeats and closure. Contrast written procedure with practice. Here, examples are invented because event history is absent. **Output:** workflow, timestamps and evidence boundaries.
4. **Inventory supported claims.** Record source, date, evidence type and limitation. “916 rejected cases” is file evidence; “900 quarterly” is the scenario; “45 quarterly audits” is arithmetic from the scenario. **Output:** versioned claim register. [Evidence](P1_ml_systems_helion.ipynb#helion-evidence)
5. **Find missing links.** Complete simulator labels do not reproduce selectively observed production labels. Manufacturing tool identities do not describe lab capacity. A classifier alone chooses neither a qualified diagnostic path nor a feasible schedule. **Output:** prioritized unknowns.
6. **Investigate what could change the recommendation.** Establish closure rules, qualified coverage, prerequisites, capacity and costs before algorithm sophistication. Record the smallest useful next check, its owner and consequence. **Output:** evidence collection and qualification prerequisites.
7. **Explain back and refresh dependent decisions.** Ask owners to check your interpretation; record decision, alternative and reopening trigger. A new supplier reopens applicability; an outage reopens allocation. **Output:** maintained context and decision register. [Operations](P1_ml_systems_helion.ipynb#helion-operations)

Before acting: *Can I trace a case, separate evidence from assumptions, explain what could invalidate the recommendation, and name the next useful check?* This algorithm transfers to unfamiliar projects and organisations.

## 3. Decision register to defend

All entries are proposed and require qualified evidence and ownership.

| Decision | Rationale and alternative | Reopen when / owner |
|---|---|---|
| One regularised multi-label logistic artifact, seven sigmoid outputs | Simple starting candidate; softmax falsely enforces exclusivity. Independent heads do not model joint fault probabilities. | Audited evidence justifies complexity / model owner. |
| Nightly initial scores; current local findings and resource state | MES consolidates nightly, but dispatch needs timely calendars, outages and results. No new inference after each result. | Qualified freshness requirements change / data owner and IT. |
| Eligible alternatives plus cost-aware coverage ranking | Transparent heuristic; it incompletely values negative findings and is not information gain. Mandatory evidence overrides ranking. | Coverage, cost or outcome evidence changes / quality owner. |
| Deterministic constrained scheduling | Explicit capacity, prerequisites, specimen conflicts and waiting limits. Current manual dispatch remains the comparison and fallback. | Complexity or operational evidence changes / coordinator. |
| Rolling horizon with frozen commitments | React to uncertainty without repeatedly moving accepted work. Fixed full-path schedules assume unknown future results. | Qualification establishes useful horizon/freeze settings / coordinator. |
| No automatic closure; protect required expensive work | Low probability is not qualified absence. Maximum waits and escalation prevent indefinite postponement. | Approved completeness rules change / quality owner. |
| Independent audits and time/lot-aware model evaluation | Complete findings support meaningful negatives. Masking selective labels alone does not remove bias. | Validated correction method and sufficient evidence exist / evaluation owner. |
| Reviewed releases and qualified fallbacks | Fits air-gapped operation and night shifts. Model and scheduling changes require qualification. | Requirements change / quality and IT. |

Detailed sources: [Policy](P1_ml_systems_helion.ipynb#helion-policy) · [Scheduling](P1_ml_systems_helion.ipynb#helion-scheduling) · [Data](P1_ml_systems_helion.ipynb#helion-data).

## 4. Explain the coupled policy

For stack `i`, eligible procedure `t`, and candidate slot `s`:

`R_i(t, s) = (1 − q_t) × Σ[w_m × p_im] / c_it(s)`

Sum only over unresolved mechanisms within the procedure's **validated** coverage. `q_t` is inconclusiveness, `p_im` the unchanged initial probability, and `w_m` an approved importance weight; equal weights are illustrative. `c_it(s)` must be positive, comparable, approved expected incremental cost. The scheduler supplies feasible slots and their setup/delay implications. Unknown costs mean no numerical ranking and a manual SOP/coordinator path, not exclusion of necessary tests.

This numerator is **weighted fault-coverage priority**, not the probability of finding any fault, all uncertainty resolved, or information gain. It rewards likely positives and incompletely values exclusion. A single procedure-level inconclusive rate simplifies potentially partial, mechanism-specific findings. Required evidence and waiting constraints override cheap-test preference. [Policy limitations](P1_ml_systems_helion.ipynb#helion-policy)

Do not add dollars, hours and destructiveness. Use approved non-overlapping monetary components when available; do not count duration again after pricing its labour/equipment use. Queue delay depends on the proposed schedule; treat turnaround as a constraint and separate outcome unless an explicit delay price is approved. Destruction primarily constrains eligibility and evidence preservation. A duration-only denominator is an explicitly simplified teaching proxy.

The policy sends **all justified eligible alternatives**, current state, prerequisites and closure obligations. The scheduler considers equipment and skilled-staff calendars, queues, specimen compatibility, setup sequences, batching, deadlines and maximum waits. It returns feasible slots and explanations; engineer/coordinator confirmation reserves one selected alternative, not all substitutes. An infeasible plan reports the blocked obligation for manual escalation. Precedence and resource non-overlap are standard scheduling constraints. [Primary scheduling reference](https://developers.google.com/optimization/scheduling/job_shop)

New results, arrivals, outages, overruns or urgency changes trigger rolling replanning. Protect started nonpreemptive work and accepted frozen reservations, except authorised outage handling. Horizon, freeze window and duration assumptions require qualification. Missing resource freshness prevents new automated slot promises. Independent audit obligations retain protected capacity and overdue reporting.

Expected total completion cost is the business objective; the deterministic planner approximates it using currently eligible work because future results and routes are unknown. Bound the planning run and distinguish a feasible proposal from proven optimality or a timeout. Low immediate cost must not produce an empty schedule or push required work beyond the horizon: every due case needs a feasible action or explicit blocked/escalated status. Carry unfinished closure obligations and terminal backlog into the next plan and evaluation. [Scheduling contract](P1_ml_systems_helion.ipynb#helion-scheduling)

## 5. Walk through the difficult cases

These are **invented illustrations**, not observed investigations. Their eligibility and closure conditions depend on qualified SOPs absent from the package. [Worked cases](P1_ml_systems_helion.ipynb#helion-worked-cases)

**A. Straightforward suspected warpage.** If X-ray is eligible and justified, offer it with its reason, unresolved coverage and feasible resource options. Qualified evidence can confirm warpage; other mechanisms remain unresolved. X-ray's delamination scope is gross delamination, and thermal/IR localisation is not proof of absence. Close only under the standard. An existing warpage rule might make the same choice, so agreement alone is not incremental ML value.

**B. Coexisting TSV and microbump faults.** Electrical isolation confirms TSV. Record that finding without reducing the initial microbump score or marking it absent. If cross-section is required, preserve prior evidence, satisfy prerequisites and obtain engineer approval. Once eligible, schedule the necessary expensive procedure within capacity and waiting constraints. “Two days” does not establish engineer-hours, equipment occupancy or monetary cost. [Procedure descriptions](../../problem-statement/helion_semiconductor_client_brief.md)

**C. Inconclusive acoustic examination and rescheduling.** Log effort; delamination remains inconclusive/unresolved. The engineer identifies a qualified repeat or alternative. Recompute future eligible work and release a no-longer-justified tentative reservation through the approved process. Keep underway work and accepted frozen commitments intact. No blind repeat, negative label or posterior probability update follows. Include spent effort and unresolved status in evaluation.

**D. Missing sampled metrology versus required acceptance results.** Not-sampled metrology is expected; retain its reason and coverage, with preprocessing fitted only on training data. Instrument dropout differs from nonapplicable process stages. Missing required acceptance observations means the checkpoint is unqualified: use SOP, not imputation that assumes rejection is confirmed. A scheduler may allocate SOP-defined work only if independently qualified for that mode; otherwise use manual dispatch. [Data boundary](P1_ml_systems_helion.ipynb#helion-data)

**E. Failed nightly import or scheduler outage.** Do not produce new ML advice from silently stale scores. Preserve current findings, work underway and accepted commitments. If resource state is stale or scheduling fails, make no new automated slot promises; the designated coordinator follows approved manual dispatch. IT/data owners investigate. Diagnostic SOP remains usable. Recovery requires valid inputs and reconciliation of reservations, not automatic replay of obsolete recommendations.

**F. New supplier or tool.** Unqualified process combinations trigger affected-case fallback and qualification review. Input drift alone does not prove outcome deterioration. Candidate retraining needs justified change evidence, approved audited data and evaluation; quality/IT approve release. Scheduling also needs qualified procedure durations/compatibility if the change affects them. The brief anticipates a bonder and underfill supplier change; their future effects are unknown. [Client changes](../../problem-statement/helion_semiconductor_client_brief.md)

**G. Two stacks compete for one scanner.** Both A and B have eligible X-ray work; A approaches an approved maximum wait, while B also has a justified acoustic alternative. Check qualified staff, resources, prerequisites and deadlines. Reserve X-ray for A and acoustic for B only if both choices are justified and feasible. Do not create an alternative merely to fill idle capacity or reserve both substitutes for B. If no feasible plan exists, escalate the unmet constraint rather than quietly violating it.

**H. An expensive case keeps losing priority.** An older case requires cross-section for adequate closure, while new cheap procedures keep arriving. Once preservation and approval conditions are met, maximum-wait/ageing controls force a planned reservation or escalation. Report its age, pending obligations and incurred effort. Deferring expensive work past the evaluation window is not a saving.

**I. Equipment fails inside the frozen window.** An authorised coordinator assesses safe handling of active work, records the outage and releases affected reservations through the approved process. Replan feasible future work and notify affected owners. Do not preempt started work automatically or silently move accepted reservations; ordinary replanning preserves them. Record overruns and changed plans for review.

## 6. Practice across all seven assessment dimensions

Each answer should identify evidence, an alternative and a condition that changes the choice. These are preparation prompts, not claims of personal experience.

**1 — Framing: “Why ML, and did you change the client's scope?”**

**Answer:** ML value is unproved. The user requested integrated selection and scheduling, broader than the original one-decision assignment. One model estimates faults; deterministic policies make two operational decisions. **Evidence:** [Framing](P1_ml_systems_helion.ipynb#helion-context). **Alternative:** incumbent selection with improved dispatch, or the original narrower assignment. **Reconsider when:** mentor/client scope review or comparative evidence favours a smaller system.

**2 — Metrics: “What counts as success, and can costs be added?”**

**Answer:** Lower expected operational cost under unchanged approved completeness, safety and turnaround constraints. Use agreed non-overlapping cost components. Until rates exist, separate engineer/equipment hours and turnaround; report mean/p95 turnaround, deadline misses, open-case age, repeats, setup effort and co-fault misses. Include overhead and pending obligations. **Evidence:** [Economics](P1_ml_systems_helion.ipynb#helion-evaluation). **Alternative:** optimise labour alone. **Reconsider when:** client-approved costs, constraints and sufficiently supported prospective results exist.

**3 — Data: “What can these files actually support?”**

**Answer:** Synthetic illustration, not deployment qualification. Untested/inconclusive operational labels remain unknown. Independently selected complete audits support initial operational learning and evaluation; around 45 quarterly audits implies scarce rare-fault evidence. If synthetic rates transferred, expected die-crack/co-fault counts would be approximately 2.3/1 per quarter—illustration only. Preserve time/lot partitions and embargoes, train-only preprocessing, and prospective evidence beyond previously examined test data. Exclude post-investigation annotations, simulator internals and the initial timing-margin shortcut. **Evidence:** [Data controls](P1_ml_systems_helion.ipynb#helion-data). **Alternative:** validated bias correction for selective labels. **Reconsider when:** suitable evidence supports it.

Also collect proposed operational records: equipment/staff calendars and freshness, eligibility, processing/setup/cleanup times, costs, queue/reservation/start/end events, batching rules, deadlines/urgency/maximum waits, prerequisites, audit work, forecast versus actual durations, and plan/override reasons. None is manufactured here.

**4 — Serving: “How can nightly scores support live scheduling?”**

**Answer:** Initial predictive scores are nightly; local findings, equipment availability and queue state update inside the fab between batches. Qualified deterministic selection/scheduling uses those current records. A stale resource view cannot promise a slot. **Evidence:** [Architecture](P1_ml_systems_helion.ipynb#helion-blueprint). **Alternative:** manual coordination with nightly advice. **Reconsider when:** data freshness, coordination burden or qualified fallback requirements favour it.

**5 — Feedback: “Could the scheduler contaminate your audits?”**

**Answer:** Yes: delaying difficult audits changes which outcomes appear complete. Protect independent sampling and full-battery obligations; report pending/overdue audits and common follow-up. Monitor qualified misses, resource-state freshness, blocked work, age, overruns and overrides. No automatic retraining or promotion. **Evidence:** [Monitoring](P1_ml_systems_helion.ipynb#helion-operations). **Alternative:** priority-dependent sampling, which would need validated correction. **Reconsider when:** documented evidence justifies a qualified alternative.

**6 — Trade-offs: “Why not one optimal learned policy?”**

**Answer:** We lack sequential outcomes, costs and resource histories. Separate interpretable candidates, constraints and human approval expose limitations. The heuristic incompletely values negative findings; a deterministic scheduler adds maintenance and coordination costs and guarantees neither global optimality nor benefit. **Evidence:** [Scheduling](P1_ml_systems_helion.ipynb#helion-scheduling). **Alternative:** qualified manual dispatch or a richer sequential policy. **Reconsider when:** evidence shows a material limitation and supports additional complexity.

**7 — Defence: “Every test still runs. Where are the savings?”**

**Answer:** Fixed procedure runtime has not fallen. Scheduling might reduce queue delays or setup costs; that is distinct from avoided diagnostics and ML value. No measured benefit is claimed. **Evidence:** [Evaluation](P1_ml_systems_helion.ipynb#helion-evaluation). **Alternative:** retain SOP and use shadow operation only to learn. **Reconsider when:** a qualified prospective comparison supports the claimed outcome, including overhead and unfinished work.

**Scheduler critique: “How would you separate effects without corrupting the comparison?”**

Compare A: incumbent selection/current dispatch; B: new selection/current dispatch; C: incumbent selection/new scheduler; D: both. B versus A estimates selection benefit; C versus A scheduling benefit; D versus A combined benefit, with interaction assessed. Hold workload, resources, completeness and cost conventions comparable. Shared queues create interference, so prospective comparisons need lab shift/time blocks, backlog/carryover handling and prespecified contrasts—not independent stack randomisation that ignores shared resources. Four benchmark configurations do not require an underpowered four-arm live pilot. Simulation and shadow outcomes do not establish real causal savings. **Alternative:** a narrower, adequately supported prospective contrast. **Reconsider when:** available operational evidence and power support the chosen design. [Evaluation plan](P1_ml_systems_helion.ipynb#helion-evaluation)

## 7. Team rehearsal

Rotate the ten-minute presentation and individual questions. Each person should redraw the two-layer architecture, trace the nine cases, explain scope expansion and separate facts from proposals. Assign named evidence, policy, scheduling/evaluation and operations responsibilities within the team. Reconcile claims with the notebook and rehearse “we do not yet know” followed by consequence, owner and next check. Retaining qualified rules or manual dispatch must remain a defensible outcome.
