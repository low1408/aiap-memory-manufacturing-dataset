# Synthetic staffing, cost and diagnostic-outcome assumptions

Version: SYN-OPS-001, 2026-09-21. Currency: USD, used as a common accounting unit without exchange-rate conversion.

This is an invented teaching scenario, not measured Helion data, vendor pricing or validated test performance. It supports a small decision/scheduling demonstration. It does not establish savings or production readiness. The companion [JSON](synthetic_operating_assumptions.json) contains the numeric inputs. No historical observations or trained predictions have been fabricated.

The [client brief](../../project/brief/helion_semiconductor_client_brief.md) supplies the five procedures, nominal durations, inconclusive rates, four-person Yield Engineering ownership team and independent 1-in-20 audit policy. All other quantities here are synthetic assumptions. The [candidate inspection rules](../../project/design/mock_engineering_inspection_rules.md) remain the exercise's comparator. Routine cases use concern-complete closure; independently selected audit cases use the complete battery. These assumptions do not turn the candidate rules into an approved client SOP.

## 1. Staff and capacity

| Pool | Headcount | Annual employment cost per person | Practical hours/person/year | Resource rate |
|---|---:|---:|---:|---:|
| Diagnostic technicians | 8 | $112,000 | 1,600 | $70/h |
| Diagnostic quality engineers | 8 | $176,000 | 1,600 | $110/h |
| Yield Engineering system owners | 4, from brief | Not estimated | Not estimated | Excluded from per-test rates |

The two diagnostic pools are invented shared fab laboratory staff, additional to the four system owners. Two technicians and two diagnostic engineers are SEM-qualified subsets of their respective pools, not additional headcount. Rates include employment benefits; salaries are not claimed to be local market benchmarks.

Nominal coverage is two technicians on the 08:00–16:00 shift, one on 16:00–00:00 and one on 00:00–08:00; one diagnostic engineer on each shift. SEM preparation and interpretation are day-shift-only in this scenario. People rotate: the same person does not work every day. This is a capacity assumption, not a completed labour-law-compliant roster.

Annual coverage checks: technician demand is 32 × 365 = 11,680 staff-hours versus 12,800 practical hours; engineer demand is 24 × 365 = 8,760 versus 12,800. This arithmetic permits coverage in aggregate; it does not prove every shift or specialist requirement can be staffed. Practical hours already deduct leave/training/unavailability, so do not deduct them again from these annual totals. Routine administration and breaks must fit outside explicitly available task intervals.

## 2. Equipment rates

One unit of each resource is assumed. These are shared resources, not dedicated solely to the approximately 900 rejected stacks per quarter.

| Equipment resource | Annual allocated cost | Practical annual capacity | Rate |
|---|---:|---:|---:|
| X-ray / CT | $120,000 | 1,500 h | $80/h |
| Acoustic microscope | $90,000 | 1,500 h | $60/h |
| Electrical isolation bench | $130,000 | 2,000 h | $65/h |
| Thermal / IR station | $67,500 | 1,000 h | $67.50/h |
| Cross-section preparation station | $60,000 | 1,200 h | $50/h |
| SEM | $225,000 | 1,500 h | $150/h |

Annual equipment costs combine depreciation/lease, service, facilities and utilities; they exclude the labour and consumables charged below. They are invented accounting allocations, not purchase prices. Practical capacity is usable capacity across the lab; do not divide by only this project's use. Availability calendars determine actual scheduling feasibility.

## 3. Dollar cost per attempt

Cost = technician hours × $70 + engineer hours × $110 + equipment hours × equipment rate + consumables.

| Procedure | Brief duration | Technician h | Engineer h | Equipment occupancy | Consumables | Total resource cost |
|---|---|---:|---:|---|---:|---:|
| X-ray / CT | 45 min | 0.25 | 0.25 | CT 0.75 h | $15 | **$120** |
| Acoustic microscopy | 1.5 h | 0.50 | 0.50 | Acoustic 1.50 h | $20 | **$200** |
| Electrical fault isolation | 4 h | 0.50 | 2.50 | Electrical bench 4.00 h | $30 | **$600** |
| Thermal / IR | 1 h | 0.25 | 0.50 | IR 1.00 h | $10 | **$150** |
| Cross-section + SEM | 2 days, destructive | 6.00 | 3.00 | Prep station 6.00 h + SEM 3.00 h | $300 | **$1,800** |

Examples: X-ray = 17.50 + 27.50 + 60 + 15 = $120. SEM = 420 + 330 + 300 + 450 + 300 = $1,800. Running all five once costs $2,870, including 7.50 technician-hours, 6.75 engineer-hours, $1,227.50 of equipment allocation and $375 consumables. This is the cost of one battery, not a guarantee of complete findings: inconclusive or wrong reports can remain.

For a simple scheduling demonstration, interpret the four short durations as resource envelopes: technician preparation first, engineer analysis last, with equipment reserved throughout. X-ray: technician first 0.25 h, engineer last 0.25 h; acoustic: first/last 0.50 h; electrical: technician first 0.50 h, engineer last 2.50 h; IR: technician first 0.25 h, engineer last 0.50 h. These deliberately simplified phases require validation and may differ from actual bench practice.

For SEM, assume six attended preparation hours, an 18-hour passive hold, then three hours of SEM operation attended by a qualified engineer. Require a minimum 48-hour start-to-report interval as this scenario's interpretation of the brief's two days; resource closures may extend it. The remaining elapsed time is not charged as active labour or equipment. This phase breakdown is invented. All required intact-sample work precedes destructive preparation.

Costs are standard resource costs, not wholly avoidable cash. Consumables are assumed fully consumed even on an inconclusive attempt. Staff/equipment allocations represent consumed capacity; reducing tests need not reduce salaries or depreciation. No overtime, outsourcing, batch discounts or separately monetised queue penalty is included in the base case. Destruction adds no second charge for a stack already destined for scrap; evidence loss is handled as a feasibility constraint.

## 4. A concrete availability snapshot

Planning origin: Monday 2026-09-21, 08:00 Singapore time. All offsets below are hours from that origin; intervals include the start and exclude the end. A free machine alone is insufficient: the appropriate staff must also be available for their task phases.

| Staff | Qualifications | On-shift interval | Existing commitments |
|---|---|---|---|
| TECH-01 | CT, acoustic, electrical setup, IR | [0, 8) | [0, 1) |
| TECH-02 | Same plus destructive preparation | [0, 8) | [0, 2) |
| QE-01 | All report types, SEM operation | [0, 8) | [0, 1) |
| TECH-03 / QE-02 | Short nondestructive procedures | [8, 16) | None in this example |
| TECH-04 / QE-03 | Short nondestructive procedures | [16, 24) | None in this example |

| Equipment | Unavailable interval | Reason |
|---|---|---|
| CT | [0, 1) | Existing reservation |
| Acoustic | None in first 24 h | Available |
| Electrical bench | [0, 4) | Existing reservation |
| IR | None in first 24 h | Available |
| Prep station | [0, 2), [8, 24) | Reservation, then closed outside day shift |
| SEM | [0, 4), [8, 24) | Maintenance, then closed outside day shift |

Reservations and staff commitments are already in progress and must be preserved. Beyond 24 h, availability is unknown; obtain the next roster before committing a multi-day completion time. Do not turn this one-day snapshot into a repeating weekly schedule. The base rates remain unchanged by these queues; elapsed turnaround changes. Cases must supply a due date/urgency separately rather than receiving an invented universal deadline.

## 5. Outcome assumptions: keep three probabilities separate

The brief's inconclusive rates are scenario inputs, not measured estimates in the supplied CSVs. Sensitivity and specificity below are invented conditional on a conclusive examination with the stated scope. They are neither derived from 1 − q nor fitted model accuracy.

| Procedure and scoped question | Inconclusive probability q | Sensitivity given conclusive | Specificity given conclusive |
|---|---:|---:|---:|
| CT: warpage | 10% | 96% | 98% |
| CT: underfill void | 10% | 92% | 98% |
| CT: gross delamination only | 10% | 90% | 98% |
| Acoustic: delamination | 15% | 97% | 98% |
| Acoustic: underfill void | 15% | 95% | 98% |
| Electrical: DRAM/base electrical | 20% | 95% | 99% |
| Electrical: TSV | 20% | 93% | 99% |
| SEM: microbump | 5% | 98% | 99% |
| SEM: die crack | 5% | 96% | 99% |
| SEM: TSV | 5% | 96% | 99% |
| IR: localisation | 30% | Not a mechanism classification | Not a mechanism classification |

Define q as a procedure-level event for this small simulator: draw one inconclusive event shared by all examined questions. Otherwise generate each scoped binary report conditional on its hidden fault truth using the listed sensitivity/specificity. Assume conditional independence between scoped reports given truth and the shared inconclusive event, solely to make the toy generator explicit. The bounded replay permits one repeat of CT, acoustic or electrical isolation after an inconclusive first attempt and draws a new conditional report; IR and destructive SEM are not repeated. This repeat model is an added candidate assumption, not observed client practice. Set unexamined questions to unchanged, not negative.

For CT, additionally assume 60% of true delamination cases are gross. This invented subtype is fixed for the sample, not redrawn per examination. A gross positive can support the delamination question; a gross negative cannot exclude non-gross delamination. The qualified scope must be recorded. For the other binary rows, package-wide scope is a simplifying simulation assumption, especially strong for destructive cross-sections; real limited sampling cannot establish package-wide absence without qualification.

For IR, the 70% non-inconclusive outcome means a useful localisation report only. It changes the examination plan, not a fault present/absent state. Do not assume a reduction in later electrical/SEM duration until a separate experiment justifies one.

For a scoped mechanism with prior probability p, sensitivity Se and specificity Sp:

`P(positive report) = (1 − q) × [p × Se + (1 − p) × (1 − Sp)]`

`P(negative report) = (1 − q) × [p × (1 − Se) + (1 − p) × Sp]`

`P(inconclusive report) = q`

These sum to one, but neither a report nor a conclusive result guarantees truth. For acoustic delamination with an illustrative p = 0.70: positive 58.225%, negative 26.775%, inconclusive 15%. The fault prior is 70%, not 58.225% or 85%. The positive-report probability includes false positives; a negative report can miss a true fault. The example p is not an output from a fitted model.

In a simulation, keep hidden mechanism truth available only to the evaluator; the policy sees measurements and reports. The mock evidence checklist may record a qualified report as supported present/absent, but evaluation must separately count false reports and missed coexisting faults. More errors cannot be traded for lower cost without violating the comparison's diagnostic-quality requirement. Faults can coexist: do not draw one mutually exclusive fault category or normalise the seven probabilities to sum to one.

## 6. How to use and challenge the assumptions

1. Load a rejected sample's initial observations, separate hidden truth, current evidence state and deadline. Use the existing mock rules to determine obligations.
2. Generate eligible procedures from scope, prerequisites and evidence-preservation rules. Keep audit cases independent and retain every required unresolved mechanism.
3. Apply the staff qualifications, phase requirements, equipment calendars and existing reservations. Unknown future availability remains unknown.
4. Calculate standard resource cost using the table. Compare expected complete investigation paths, including inconclusive tests and follow-up work; update the calendar and evidence after each actual outcome.
5. Compare against the same mock baseline under identical resources, truth, outcome assumptions and completeness requirements. Report cost, capacity use, turnaround, unresolved cases and diagnostic errors separately. Do not claim savings from this assumption table alone.

Sensitivity scenarios are stress tests, not confidence intervals: multiply staff/equipment rates by 0.75 or 1.25; add 0/2/4 hours of equipment unavailability; test q at base ± 0.05; test sensitivity at base − 0.05 and specificity at base − 0.02, with probabilities bounded to [0,1]. Also test correlated errors and reduced examination scope before trusting any apparent gain.

Under concern-complete routine closure, procedures are required only by observed triggers, failed acceptance branches and dynamically added co-fault safeguards. A policy can therefore change cost when an earlier finding legitimately retires a generic branch. Audit cases still receive the complete battery. Apparent savings must be reported together with missed mechanisms, missed co-faults, unresolved escalations and repeat effort.

Before replacing assumptions: lab operations supplies skills/rosters and task phases; finance supplies costs/rate definitions; equipment owners supply calendars; quality/process engineering qualifies coverage, report interpretation and closure; independent audits supply evidence about errors and coexisting faults. This package adds an explicit hypothetical operating environment, not the missing empirical evidence.
