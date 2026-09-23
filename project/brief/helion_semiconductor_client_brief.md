# Client Brief - Helion Semiconductor (HBM diagnostic-test selection)

**Group 8 - "Designing a Good ML System" week.** This is the client-side framing of your approved
problem. It gives you the business situation and the constraints you have to design inside; it does
**not** give you the ML spec. Framing, target, metric, serving pattern, monitoring and run cost are
yours to define and defend.

---

## Business Context

Helion assembles and tests high-bandwidth memory stacks - 8-high and 12-high HBM3E, a base die plus
core dies, bonded and molded as one package. Every assembled stack goes through **required acceptance
testing**, and that stays true whatever you build. Around **5%** fail it. At current volumes that is
roughly **900 rejected stacks a quarter**.

A rejected stack then goes to an **HBM quality engineer**, who has to work out *what* went wrong -
warpage, an underfill void, a microbump open, a TSV open or short, a die crack, delamination, a DRAM
or base-die electrical fault - by choosing which **additional diagnostic procedures** to run. Nobody
runs everything. The engineer picks a path, confirms or excludes, and stops when the investigation
meets the standard. The stack is scrapped either way; the value of the diagnosis is what it tells
process engineering, and how much lab time and engineer time it consumed getting there.

Procedures differ enormously in what they cost and what they can settle:

| Procedure | Can confirm / exclude | Time | Inconclusive rate |
|---|---|---|---|
| Package X-ray / CT | Warpage, underfill void, gross delamination | 45 min | 10% |
| Scanning acoustic microscopy | Delamination, void | 1.5 h | 15% |
| Electrical fault isolation | DRAM/base electrical, TSV open/short | 4 h | 20% |
| Cross-section and SEM | Microbump open/bridge, die crack, TSV | 2 days, destructive | 5% |
| Thermal / IR imaging | Electrical fault localisation | 1 h | 30% |

Two facts about the diagnosis matter. **Faults coexist** - about 1 in 40 rejected stacks has more
than one mechanism - so confirming the first thing you find is not a complete diagnosis. And
**stopping early is the current failure mode**: a confirmed TSV open does not rule out a microbump
open underneath it, and process engineering has twice chased a phantom recipe problem because a
coexisting mechanism was never looked for.

The incumbent is a set of **engineering inspection rules** and a fixed procedure order - if measured
warpage exceeds a threshold, start with X-ray; if the electrical signature looks like an open, go to
fault isolation. They are written down, they work, and they are the thing to beat. Note that the
rules already read the same inspection measurements you would: if your model's contribution is to
repeat what a warpage gauge already said, it has contributed nothing.

Two changes are in flight. A second bonder tool set comes online next quarter, and the underfill
material is being requalified to a new supplier - both of which move which mechanisms dominate, and
the inspection thresholds were tuned on the old process.

There is one clean source of truth. **One rejected stack in twenty** goes through the **complete
diagnostic battery** regardless of what the rules suggest, to keep the lab honest. Those cases have
confirmed findings for every mechanism, present or absent. Everything else only has findings for the
procedures somebody chose to run.

Whatever you build runs inside the fab. The **Yield Engineering team - four engineers**, strong in
statistics and JMP with some Python - would own it. Fab IT is **air-gapped from the corporate
network and from the internet**; metrology and assembly data lands in the MES on a **nightly
consolidation**, and anything that influences disposition of production material goes through
**change control and software qualification** before it may be used. The engineers who would use it
work **rotating shifts around the clock**, and at 3am there is nobody to call.

## The Ask

> "Every rejected stack costs me a day of somebody's week, and a cross-section costs me two days and
> the sample. My engineers are good at this, but a new engineer on nights follows the flowchart and
> sometimes that means four hours on fault isolation for something an X-ray would have settled in
> forty-five minutes.
>
> Be straight with me about two things. My rules already use the warpage and void numbers, so I need
> to know what you add beyond them. And I don't want a tool that tells my engineer to stop looking
> after the first hit - we've been burnt by that. Can AI help us pick the next test?"
> - HBM Quality Manager, Helion Semiconductor

## Objective (high level - not the ML spec)

Help the on-duty quality engineer decide **which diagnostic procedure to run next on a rejected
stack**, given the procedures cost what they cost and the diagnosis has to be complete enough to be
useful. How you frame that as an ML problem - the target, the task type, what the output actually
drives, the metric, and what the engineer still decides - is yours to define.

## Data

Roughly **900 rejected stacks a quarter**, drawn from the assembly and test records. Available at the
point the engineer chooses a procedure:

| Field | How it is stored |
|---|---|
| `stack_id`, `lot_id`, `product` | Identifiers; 8-high or 12-high |
| `assembly_tool_id`, `bond_recipe_id`, `reflow_profile_id`, `mold_cure_id` | Tool and recipe identities for the build |
| Constituent-die aggregates | Summaries over the dies in the stack, from wafer-level metrology |
| `tsv_copper_void_pct`, `die_thickness_um` | Detailed die metrology - sampled on 25% of dies, with a further 2% instrument dropout; blank cells distinguish `not_sampled` from `instrument_dropout` |
| `package_warpage_um`, `underfill_void_pct`, `delamination_area_pct` | Package inspection, 100% coverage. The three percentages use different denominators |
| `stack_assembly_pass`, `electrical_test_pass` | Acceptance verdicts |
| `uncorrected_error_count`, `bit_error_rate`, `ecc_corrected_errors`, `detected_interconnect_failures` | Error and interconnect observations from acceptance test |
| `max_pass_data_rate_gbps`, `measured_bandwidth_gb_s`, `timing_margin_ps` | Speed and timing observations. `timing_margin_ps` takes its sign from the electrical pass/fail result |
| `power_consumption_w`, `thermal_resistance_c_w` | Power and thermal, under a fixed 85C / 1.1V test condition |
| `test_temperature_c`, `test_voltage_v`, `offered_data_rate_gbps`, `bus_width_bits`, `test_program_id` | Initial test conditions; several are constant across the cohort |
| `defect_type`, `defect_severity`, `final_disposition` | Summary annotations written onto the test record after the investigation closed |
| `procedures_run`, `diagnostic_hours` | Which procedures were performed, and the effort spent |
| `full_battery_sample` | Whether this stack went through the complete diagnostic battery |
| Seven `fault_*` indicators | **The targets.** Confirmed mechanism findings - complete for full-battery stacks, and otherwise only for procedures someone chose to run. The rarest, die crack, has about 47 positives in 900 |

Note that stacks in one `lot_id` share material, tools and process excursions, and a single
excursion can take out most of a lot.

If you take the optional pipeline stretch, generate a **small synthetic dataset** with your LLM in
roughly this shape. Realism is not graded; plausible is enough.

## Constraints & scope

- **You have about 900 cases a quarter, not 900,000.** Hold back validation and test and the
  training cohort is a few hundred, against seven mechanisms of which the rarest has roughly 47
  positives.
- **The value is avoided lab time, not accuracy.** A ranking helps only if it changes which
  procedures get run, at an unchanged standard of diagnostic completeness. Reordering procedures that
  all get run anyway saves nothing, and a probability over mechanisms is not the same thing as
  knowing which test is most informative next.
- **A complete diagnosis includes the second fault.** Faults coexist, and stopping at the first
  confirmation has already sent process engineering after a phantom cause twice. A design that
  optimises for finding *something* fast is the failure mode, not the goal.
- **The rules already read your best inputs.** Inspection rules and a fixed procedure order use the
  same warpage, void and delamination numbers. Beating them means adding information they do not
  already have - and if they suffice, the honest recommendation is to keep them.
- **You cannot ask for more measurement.** The metrology sampling plan is set by the process, not by
  this project: detailed die metrology exists for a quarter of dies and that is not changing, and
  process fields are simply absent where the recipe stage does not apply.
- **Only the procedures you run produce findings.** Follow the ranking and the record of confirmed
  mechanisms becomes a record of what the ranking suggested looking for. The 1-in-20 full battery is
  the only cohort where absence of a fault means something.
- **It runs in the fab, for whoever is on shift.** Air-gapped from the corporate network and the
  internet, fed by a nightly MES consolidation, under change control and software qualification
  because it touches production material - and used at 3am by an engineer with nobody to call.
- **Scope: one model, one decision.** A good system, not a big one.
