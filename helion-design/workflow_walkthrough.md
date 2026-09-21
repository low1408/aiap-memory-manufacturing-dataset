# Helion: a costed workflow walkthrough and next-step decisions

**21 September 2026 · Group 8 · Paper exercise using SYN-OPS-001**

This is the reading copy of [notebook Appendix I](P1_ml_systems_helion.ipynb#helion-workflow-review). It completes steps 1–4 at design level: exercise decisions, prioritise evidence, specify experiments and choose what to build next. The scenarios are separate paper examples, not simultaneous bookings or observed investigations. No model, simulator, scheduler or operational pipeline has been implemented. Arithmetic and resource feasibility checks are not a performance benchmark.

## 0. What the new assumptions let us do

| Source | What it supplies | What it does not establish |
|---|---|---|
| [Client brief](../problem-statement/helion_semiconductor_client_brief.md) | Objective, procedure catalogue, nominal times, inconclusive rates, four Yield Engineering owners and independent audits | Actual full SOP, dollar rates or diagnostic staff calendars |
| [MOCK-ENG-001](mock_engineering_inspection_rules.md) | Invented triggers, fixed order, exceptions and all-seven-mechanism closure rule | Helion's actual approved procedure or closure standard |
| [SYN-OPS-001 assumptions](../synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.md) and [JSON](../synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.json) | Invented staff, equipment calendars, resource costs and outcome distributions | Observed costs, validated test performance or measured savings |
| Supplied CSV audit | 916 synthetic rejects, seven labels, existing lot/time splits | Procedure histories, diagnostic effort, audit membership or resource events |

We can now calculate concrete hypothetical decisions. Missing operational evidence remains missing; replacing a blank with an assumption does not verify it.

### Use the same versioned operating inputs in every comparison

| Procedure | Resource cost per attempt, USD | Nominal duration from brief | Inconclusive probability |
|---|---:|---|---:|
| X-ray / CT | $120 | 45 minutes | 10% |
| Acoustic microscopy | $200 | 1.5 hours | 15% |
| Electrical isolation | $600 | 4 hours | 20% |
| Thermal / IR | $150 | 1 hour | 30% |
| Cross-section / SEM | $1,800 | 2 days, destructive | 5% |

Costs value technician labour at $70/h and diagnostic engineer labour at $110/h, plus equipment occupancy and consumables. Acoustic costs $35 technician + $55 engineer + $90 equipment + $20 supplies = $200. These are standard resource costs, not fully avoidable cash. Queue delay is not monetised, so waiting changes turnaround without automatically changing the dollar figure. SEM consumes six technician-hours and three engineer-hours; two days is not 48 attended labour-hours.

The invented shared laboratory has eight technicians and eight diagnostic engineers, separate from the four Yield Engineering owners in the brief. Headcount is not concurrent availability. At the 08:00 planning origin there are two day-shift technicians and one engineer; TECH-01 and QE-01 are occupied until 09:00, TECH-02 until 10:00. CT is reserved until 09:00 and electrical isolation until 12:00. The acoustic machine is free at 08:00, but its qualified preparation staff are not. Availability beyond the first 24 hours is unknown.

### Execute a decision event in this order

1. Check case identity, initial observations, current evidence, audit membership and source versions. Missing evidence stays unknown.
2. Apply mock triggers and remaining completeness obligations. Determine eligible procedures and preserve intact-sample evidence before destructive work.
3. Use the seven initial probabilities as optional priority inputs. They do not sum to one and are not updated posteriors after findings.
4. Check qualified staff phases, equipment, specimen conflicts and existing reservations. Return a feasible proposed slot or a blocked status.
5. Engineer approves the procedure; the designated dispatcher confirms the slot. Record resource use even if the result is inconclusive.
6. Update only questions supported by the report's scope. Reconsider future work; close only after the mock evidence standard is met and the engineer reviews it.

Track W = warpage, V = underfill void, D = delamination, E = DRAM/base electrical, T = TSV, M = microbump and C = die crack. Each is untested, confirmed present, confirmed absent or inconclusive. Untested/inconclusive remain unresolved. Here “confirmed” describes the mock evidence record: reports are fallible, and independent evaluation must still assess diagnostic errors against hidden truth. Process engineers use findings to investigate manufacturing causes; a delamination finding alone does not identify a particular faulty machine or recipe.

## 1. Exercise the decision workflow

### Case A: a strong rule, a priced test and a feasible slot

Assume an 8-high rejected stack has warpage 17 µm, so mock R01 fires at its invented 15 µm threshold. No competing initial trigger fires. Initial W/V/D/E/T/M/C probabilities are illustratively 0.70/0.10/0.05/0.10/0.10/0.05/0.02. The mock baseline and proposed policy both select CT.

| Checkpoint | Decision / evidence | Cost and pending work |
|---|---|---|
| 08:00 request | CT cannot start: machine and preparation staff occupied | No new attempt cost; one hour planned waiting |
| 09:00–09:45 | CT reserved; TECH-01 attends 09:00–09:15; QE-01 interprets 09:30–09:45 | $120 attempt; no resource overlap |
| Branch A1: qualified W positive, V negative, gross-D negative | Record W present and V absent; gross-D negative cannot exclude all D | D/E/T/M/C unresolved; closure not allowed |
| Branch A2: qualified W/V negative, gross-D negative | Record W/V absent | D/E/T/M/C unresolved; continue completeness review |
| Branch A3: procedure inconclusive | W/V/D remain unresolved | $120 still spent; review scoped alternative/repeat eligibility |

Branches are alternative reports, not three attempts. Under SYN-OPS-001, an inconclusive event is shared across questions examined by that procedure. After A1/A2, acoustic is the next mock completeness procedure for D; required electrical and microbump/crack work remains visible. A3 does not automatically rerun CT: acoustic can address V/D, while unresolved W needs a reviewed plan.

**Conclusion:** the rule already makes this choice. Pricing and scheduling make its consequences explicit; agreement does not show incremental ML value.

### Case B: acoustic-first can be correct and already match the baseline

Assume a prior qualified CT has settled W and V as absent and cost $120; its gross-D negative leaves D unresolved. Mock R03 fires from `delamination_area_pct = 0.40`, while R04 fires from `detected_interconnect_failures = 1`. The current illustrative D/E/T probabilities are 0.70/0.10/0.10. Required nondestructive work remains before SEM.

Both acoustic and electrical isolation are justified. **MOCK-ENG-001 chooses acoustic first**, because its fixed order puts acoustic before electrical among eligible procedures. The brief's electrical example does not establish a universal electrical-first rule. CT has no unresolved W/V question here and is not an automatic repeat candidate.

For comparison only, the earlier positive-coverage heuristic with equal weights gives:

| Eligible procedure | Calculation using current unresolved questions | Priority per resource dollar |
|---|---|---:|
| Acoustic | 0.85 × 0.70 / 200 | 0.002975 |
| Electrical isolation | 0.80 × (0.10 + 0.10) / 600 | 0.000267 |

This heuristic agrees with the mock baseline. It is not a probability of completing the investigation, does not fully value negative evidence and does not model the listed sensitivity/specificity. It is a candidate to evaluate, not an established cost-minimising policy.

| Action / illustrative report | Feasible slot in this separate scenario | Cumulative resource cost | Questions still unresolved |
|---|---|---:|---|
| Prior CT: W/V absent | Already completed before this snapshot | $120 | D/E/T/M/C |
| Acoustic: D present; no contradictory V finding | 09:00–10:30; TECH-01 09:00–09:30, QE-01 10:00–10:30 | $320 | E/T/M/C |
| Electrical: E absent, T present | 12:00–16:00; TECH-01 12:00–12:30, QE-01 13:30–16:00 | $920 | M/C |
| SEM requested after evidence preservation | Future qualified staff/calendar needed; no completion slot promised | $920 spent; $1,800 planned | M/C remain pending |

The real D finding is useful. Comparing the $800 acoustic-plus-electrical pair against $600 electrical-only would compare different evidence: electrical does not settle D. If both procedures are needed, either order costs $800. The $120 CT already performed is sunk for the next-action choice, but stays in the full-investigation total. Pending SEM is not counted as spent or omitted from planned obligations.

**Outcome probability is a separate calculation.** Using the invented acoustic sensitivity 0.97 and specificity 0.98 conditional on a conclusive examination, q = 0.15 and illustrative prior p(D) = 0.70:

- Positive report: `(1 − 0.15) × [0.70 × 0.97 + 0.30 × 0.02] = 58.225%`.
- Negative report: `(1 − 0.15) × [0.70 × 0.03 + 0.30 × 0.98] = 26.775%`.
- Inconclusive report: `15%`.

These sum to one. The 70% fault prior, 85% conclusiveness and 58.225% positive-report probability answer different questions. Neither positive nor negative guarantees truth. If acoustic is inconclusive, $320 has still been spent, D stays unresolved and a reviewed continuation is needed. Independent electrical work can proceed at its feasible slot; it cannot close D. These report probabilities alone do not give the cost of that continuation.

**Conclusion:** this case supports a useful acoustic examination, but no change in choice or saving attributable to ML.

### Case C: complete the evidence record, including the second fault

Continue Case B's conclusive branch after the lab obtains future calendars, preserves all required nondestructive evidence and authorises SEM. Its low initial microbump probability, say 0.05, cannot remove the unresolved M question. Assume a scoped conclusive SEM report confirms M and T and excludes C, without contradictions.

| Mechanism | Final mock evidence state | Supporting report |
|---|---|---|
| W | Confirmed absent | CT |
| V | Confirmed absent | CT; acoustic consistent |
| D | Confirmed present | Acoustic |
| E | Confirmed absent | Electrical isolation |
| T | Confirmed present | Electrical isolation and SEM |
| M | Confirmed present | SEM |
| C | Confirmed absent | SEM |

The engineer can now review closure against the mock all-seven standard. Total resource cost for this particular path is **$120 + $200 + $600 + $1,800 = $2,720**. SEM's invented package-wide exclusion scope is a strong assumption; a limited real section cannot automatically support C absence. Hidden truth, kept from the policy, is needed to assess whether the recorded findings are actually correct. This branch is a scripted illustration, not a simulated success rate.

An inconclusive SEM instead leaves M/C unresolved: the same $2,720 has been consumed without complete closure. Escalate the evidence gap; no automatic repeated destructive sampling or first-positive stopping. IR would add $150 when required by R07 or the independent audit battery; it does not directly establish a mechanism's absence. Running all five once costs $2,870 and still does not guarantee complete or correct findings.

Not every case requires all four core procedures: a qualified gross-D positive on CT may already settle D, and a procedure with no remaining required question may be skipped under the mock rules. CT + electrical + SEM would then cost $2,520 if no acoustic or IR obligation remains. Audits still require their battery. Any such omission must be available to the baseline too; $2,720 is a costed branch, not a universal minimum or fixed cost for every investigation.

### Case D: staffing and deadlines change scheduling, not fault probability

At the same 08:00 origin, two separate rejected stacks need CT: A has an underfill question with a milestone of 11:00; B has a warpage question due at 10:00. These are invented deadlines for scoped evidence, not whole-investigation closure. CT and TECH-01 first become available at 09:00. The described examinations are eligible; other obligations remain pending.

| Plan | First CT | Second CT | Milestone assessment if conclusive | Total resource cost |
|---|---|---|---|---:|
| A first | A 09:00–09:45 | B 09:45–10:30 | B misses 10:00 | $240 |
| B first | B 09:00–09:45 | A 09:45–10:30 | Both met | $240 |

For B-first, TECH-01 is needed 09:00–09:15 and 09:45–10:00; QE-01 is needed 09:30–09:45 and 10:15–10:30. These intervals fit the supplied staff commitments and do not overlap for either person. This checks more than machine availability. The model's initial fault probabilities need not change.

If B is inconclusive at 09:45, B remains unresolved and the $120 attempt is retained. An automatic repeat is not authorised. Even a hypothetically approved immediate 45-minute repeat cannot finish by 10:00 and would conflict with A's accepted slot. Preserve A's commitment and escalate B's milestone/continuation. Stale calendars or outages likewise require manual reconciliation, not invented availability.

Choosing acoustic for A solely because the machine is free would cost $200 rather than $120 and requires qualified staff; the B-first CT plan already meets both scoped milestones. No additional procedure is justified by machine idleness alone. Actual lab dispatch might already use B-first, so this is a feasibility demonstration, not a measured improvement.

### Exception walkthroughs

| Situation | Immediate action | Cost, evidence and continuation |
|---|---|---|
| Required measurement missing | Mark the affected trigger not evaluable; preserve missingness reason; continue other supported branches | Never fill with zero or infer absence; unresolved questions remain |
| Nightly import fails | Use existing rules and last valid case evidence; do not create fresh model scores | Manual dispatch if resource state is also unqualified; keep audits and obligations |
| Resource calendar stale or beyond 24-hour horizon | Stop new automatic slot promises; request current local availability | Keep consumed cost, findings and existing commitments; SEM's nominal 48 hours is not a guaranteed finish |
| New bonder or supplier | Flag the case outside qualified conditions; use reviewed SOP/manual handling and qualification review | Neither old thresholds nor invented sensitivities establish performance on the new process |

## 2. Prioritise the evidence still needed

The assumptions resolve a teaching exercise's inputs; they do not close the real evidence gaps. Requests below are specifications, not messages sent or client answers obtained.

| Topic | Available for the exercise | Evidence needed before operational claims; owner |
|---|---|---|
| Baseline / closure | MOCK-ENG-001 with seven separate states | Actual SOP, exceptions, closure and repeat standard; quality owner |
| Costs | SYN-OPS-001 staff/equipment rates and phases | Actual labour, occupancy, consumables and cost boundaries; finance/lab operations |
| Availability | One-day hypothetical roster and reservations | Qualified skills, live calendars, deadlines, setup/batching and current dispatch; shift lead |
| Test outcomes | Invented scoped sensitivity/specificity and brief q | Validated coverage, correlated errors, result histories and destructive limits; lab/quality |
| Fault prediction | 916 synthetic labels and existing splits | Decision-time availability, representative complete audits and fresh process evidence; data/quality |

Capture event time and information-availability time, initial inputs, evidence states, pending obligations, eligible alternatives, baseline and proposed choices, reasons/overrides, staff/equipment assignments, scoped reports, actual resource use and closure. Keep independent audit selection, pending audits and unresolved backlog visible. Do not request more metrology sampling or convert selectively unobserved labels into negatives. [Notebook evidence](P1_ml_systems_helion.ipynb#helion-evidence)

## 3. Specify two different experiments

**Prediction experiment, optional and not run:** ask whether allowed manufacturing context improves fault probabilities beyond inspection/acceptance inputs. Retain the 653/126/137 rejected lot/time partitions, training-only preprocessing, per-fault support/calibration and lot-aware uncertainty. Compare training prevalence, inspection-only logistic and the same regularised model family with allowed context. Exclude later annotations, simulator internals and `timing_margin_ps`. Previously examined synthetic holdout data supplies retrospective evidence only. The two logistic configurations are alternatives, not two deployed models.

**Decision experiment, proposed next:** exercise the mock rules, the earlier coverage heuristic and feasible schedules against identical operating assumptions. Use scripted branches before stochastic simulation. Fault priors are not procedure outcome labels; synthetic sensitivities are not a trained outcome predictor. Store hidden truth separately from policy inputs, preserve coexisting faults, and do not assume independent repeat-test successes. Unspecified continuation branches end in explicit unresolved/escalated states, not invented cost-free completion.

| Arm | Diagnostic selection | Dispatch |
|---|---|---|
| A | Mock engineering rules | Explicit synthetic reference dispatch |
| B | Qualified candidate policy | Same reference dispatch |
| C | Mock engineering rules | Candidate constrained dispatch |
| D | Candidate policy | Candidate constrained dispatch |

Actual Helion dispatch remains unknown. For Case D alone, A-first versus B-first is an explicit teaching contrast, not the real incumbent. A later broader reference dispatch must be specified and frozen before comparison. Separate selection, scheduling and their interaction. Include a rules-plus-evidence-checklist alternative so workflow discipline is not credited to ML.

A better decision objective than a greedy ratio is **immediate resource cost plus expected remaining cost to adequate completion**, subject to resource and evidence constraints. The cost table supplies the first term; scoped report probabilities supply some branches. The complete continuation model is not yet specified for every inconclusive result, so we cannot calculate a globally optimal policy or total expected savings from these inputs alone. The initial model remains the seven-output logistic candidate; no automatic Bayesian update or additional learned outcome model is claimed.

Report per-investigation resource cost, labour/equipment use, elapsed mean/p95 turnaround, missed milestones, overrides, pending cost/obligations, unresolved cases and missed mechanisms/co-faults. Compare cost at the same adequacy and diagnostic-error requirements; do not drop unfinished cases. Sensitivity-check rates ×0.75/1.25, equipment outages of 2/4 hours, q ±0.05 and worse sensitivity/specificity as defined in SYN-OPS-001. These are stress tests, not confidence intervals. A fixed same-test path has the same execution cost regardless of order; no current batch/setup or queue-dollar saving is assumed.

## 4. What to build next

| Stage | Concrete output | Gate / limitation |
|---|---|---|
| Completed here | Versioned, costed paper cases and presentation | Internally checked assumptions; no operational validation |
| Next educational step | Small deterministic replay of these cases, then a bounded stochastic simulator if useful | Freeze scope, continuation rules, comparison dispatch and evaluation metrics first; preserve unresolved endings |
| Optional prediction study | Inspection-versus-context experiment above | Demonstrate added predictive information without claiming operational savings |
| Operational discovery | Replace assumptions with reviewed SOP, rates, event history and resource feeds | Independent full-battery evidence and representative process coverage |
| Qualified shadow study | Record recommendations while engineers follow current practice | Qualified interfaces, fallbacks and monitoring; no realised-benefit claim from shadow recommendations alone |
| Controlled pilot / release | Evaluate justified changes with common follow-up and backlog accounting | Evidence of benefit at unchanged adequacy; reviewed release, never automatic deployment |

**Current decision:** the assumptions are sufficient for a concrete learning demonstration. Build that bounded replay before a production model pipeline if implementation is requested. Retain the option to use rules with better scheduling, or retain existing practice if additional complexity earns no benefit. Neither the new prices nor accurate fault predictions alone prove that a cheaper complete diagnostic path exists.
