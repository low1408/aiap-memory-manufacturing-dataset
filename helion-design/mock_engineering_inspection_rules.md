# Mock engineering inspection rules — Helion HBM diagnostics

**Version:** `MOCK-ENG-001`, v0.1  
**Purpose:** a transparent, non-ML baseline for choosing the next diagnostic procedure on an already-rejected HBM stack.

The [client brief](../problem-statement/helion_semiconductor_client_brief.md) supplies the scenario, procedure catalogue and examples of incumbent rules. **All numerical trigger thresholds, priorities, fallback logic and closure rules below are invented teaching assumptions.** They are not Helion's actual SOP, manufacturer specifications or validated acceptance limits. The earlier workflow review correctly records the actual incumbent SOP as unavailable; this document supplies a mock comparator only.

## 1. When these rules apply

- Required acceptance testing has finished, and `stack_assembly_pass == 0` **or** `electrical_test_pass == 0`.
- Use manufacturing/package measurements and initial acceptance observations available at the decision time. Later diagnostic findings can update subsequent decisions only after they become available.
- Do not use `defect_type`, `defect_severity`, `final_disposition`, simulator truth or `fault_*` labels to choose a test. In a simulation, truth labels belong in the evaluator only.
- The output is a recommended **next procedure**, its triggering rule(s), and the questions still unresolved. These rules do not alter the rejected stack's disposition.

For the existing CSVs, use `stack_layer_count` to distinguish 8-high and 12-high. Join records by `stack_id`. The sampled TSV field is `sampled_core_tsv_void_mean_pct`, with coverage recorded in `n_dies_with_detailed_metrology`.

## 2. Mock inspection triggers

Evaluate every rule independently. Several can fire for the same stack; a positive result from one branch does not cancel another branch.

| ID | If the available observation is… | Recommend / add to the investigation | Question to resolve |
|---|---|---|---|
| R01 | `package_warpage_um >= 15` for 8-high, or `>= 18` for 12-high | Package X-ray / CT | Is package warpage a confirmed mechanism? Review voids and gross delamination within the same examination's scope. |
| R02 | `underfill_void_pct >= 0.50` | Package X-ray / CT; acoustic microscopy if the void question remains unresolved | Is underfill voiding present? |
| R03 | `delamination_area_pct >= 0.30` | Scanning acoustic microscopy | Is interface delamination present? An X-ray finding about gross delamination does not exclude finer delamination. |
| R04 | `detected_interconnect_failures >= 1` | Electrical fault isolation; retain a separate microbump question for cross-section / SEM | Does the interconnect failure involve TSVs, microbumps, or both? This count alone cannot distinguish them. |
| R05 | `electrical_test_pass == 0` or `uncorrected_error_count > 0` | Electrical fault isolation | Is there a DRAM/base electrical or TSV mechanism? Do not infer its identity from acceptance failure alone. |
| R06 | At least one core die was measured, and `sampled_core_tsv_void_mean_pct >= 0.80` | Electrical fault isolation focused on the TSV hypothesis | Does the sampled copper-fill observation correspond to a functional TSV fault? |
| R07 | Electrical fault isolation is inconclusive and the electrical fault remains unlocalised | Thermal / IR imaging, once, before considering destructive examination | Can localisation guide the next examination? Localisation alone does not confirm or exclude a mechanism. |
| R08 | Microbump or die-crack questions remain unresolved after the relevant nondestructive examinations; or `stack_assembly_pass == 0` remains unexplained after package imaging | Cross-section and SEM, after preserving required nondestructive evidence | Is there a microbump open/bridge, die crack or unresolved TSV defect? Report the actual examined scope. |

Threshold equality triggers the rule. Values below a threshold mean **the rule does not fire**, not that the corresponding fault is absent. R08 also applies through the completeness review below, even when no initial measurement points to a crack or microbump fault.

The percentage fields have different denominators: underfill void is a percentage of inspected underfill cross-section area; delamination is a percentage of inspected package interface area; TSV copper void is a per-via copper-fill void-volume surrogate. `0.50` means **0.50%**, not 50%. Do not combine these readings into one percentage or reuse a threshold across them.

## 3. Fixed order and competing triggers

For an ordinary case, choose the first eligible, still-useful procedure in this fixed order:

1. **Package X-ray / CT** — 45 minutes.
2. **Scanning acoustic microscopy** — 1.5 hours.
3. **Electrical fault isolation** — 4 hours.
4. **Thermal / IR imaging** — 1 hour, conditional on R07.
5. **Cross-section and SEM** — 2 days, destructive.

Durations come from the brief. They are not interchangeable with attended engineer-hours; record elapsed time, equipment use and engineer time separately.

“Eligible, still-useful” means a trigger or completeness obligation calls for the procedure, it can address an outstanding question, and its prerequisites are satisfied. After each result, update the evidence states and evaluate the rules again. Combine duplicate requests for the same procedure into one examination with all relevant questions listed.

For example, if both R01 and R04 fire, start with X-ray and retain the electrical-isolation obligation. If only R04 fires, start with electrical isolation. The fixed order is a priority among eligible procedures, not a requirement to run every earlier procedure first.

Skip a procedure only if it has no remaining required question, or that question has already been resolved by evidence with sufficient scope. A generic negative finding or another confirmed fault is not a reason to skip it. Complete any outstanding nondestructive work that requires an intact sample before cross-sectioning.

## 4. Findings, coexisting faults and stopping

Track seven separate mechanism states:

| Mechanism | Target name used by the project | Procedure that can contribute evidence in this mock catalogue |
|---|---|---|
| Warpage | `fault_warpage` | X-ray / CT |
| Underfill void | `fault_underfill_void` | X-ray / CT; acoustic microscopy |
| Delamination | `fault_delamination` | Acoustic microscopy; X-ray / CT for gross findings only |
| DRAM/base electrical | `fault_dram_electrical` | Electrical fault isolation |
| TSV open/short | `fault_tsv_open_short` | Electrical fault isolation; cross-section / SEM |
| Microbump open/bridge | `fault_microbump_open_bridge` | Cross-section / SEM |
| Die crack | `fault_die_crack` | Cross-section / SEM |

Each state starts as `untested` and can become `confirmed_present`, `confirmed_absent` or `inconclusive`. Conflicting findings remain unresolved pending review. Record the report and examined scope supporting each state. Running a procedure does not automatically update every mechanism it could potentially inspect. A negative result limited to one region cannot establish package-wide absence.

**Mock completeness rule:** close as `diagnostically_complete` only when all seven mechanisms have a supported present/absent finding and there are no unresolved contradictions. After the triggered branches, use the catalogue above to add investigations for remaining unresolved mechanisms, in the same fixed order. If the available procedures cannot settle a question, record `partial_unresolved` with the evidence and reason; do not silently convert it to absence or report complete closure.

This deliberately conservative closure rule is an assumption for the exercise. It will often require cross-section / SEM even after another fault is found. It therefore provides no automatic claim of fewer tests or saved time; a less intensive closure standard would need its own evidence and explicit definition, applied equally to rules and ML.

**Example:** fault isolation confirms a TSV open. Record TSV as present. Microbump remains unresolved until separately addressed; the TSV finding is not permission to stop. If SEM subsequently confirms a microbump open, retain both positive findings.

## 5. Exceptions and fallback rules

| Situation | Mock handling |
|---|---|
| `full_battery_sample == 1` | Perform all five procedures regardless of triggers, with cross-section last. Preserve the independent 1-in-20 audit selection from the brief; do not let rules or model scores deselect a case. Any inconclusive mechanism still needs resolution before this is a complete reference case. |
| Required measurement missing, invalid or mismatched to the stack | Mark the affected rule `not_evaluable`; continue independent branches with valid evidence. Do not fill the missing value with zero or call it a negative. The unresolved mechanism remains on the completeness checklist. |
| Detailed die metrology is `not_sampled` or `instrument_dropout` | Preserve the reason and observed coverage. If no dies have valid measurements, R06 is not evaluable. Do not request a change to the fixed sampling plan, or use an observed mean to exclude faults in unmeasured dies. |
| X-ray is inconclusive | Keep affected mechanisms unresolved. Use acoustic microscopy for void/delamination questions. Unresolved warpage requires lab review of the existing evidence or repeat eligibility. |
| Acoustic microscopy is inconclusive | Keep void/delamination unresolved and refer for a scoped alternative or repeat plan; do not assume SEM resolves those questions under this catalogue. |
| Electrical isolation is inconclusive | Apply R07. Use any localisation to plan remaining work; keep unresolved DRAM/base, TSV and microbump questions separate. |
| IR or SEM is inconclusive, or findings conflict | Retain unresolved states and the effort already spent. Refer for review; do not automatically loop through tests or declare the case complete. |
| Required instrument is unavailable | Record the pending procedure and delay. Another independent nondestructive branch may proceed; unavailability does not resolve the original question. |
| New bonder or underfill supplier/process version | Flag that the mock thresholds are outside their assumed process context. Retain evidence-based completeness checks and route threshold applicability for review. Do not invent a fault-specific rule from a new tool ID alone. |

## 6. Worked examples

These observations and outcomes are invented, not sampled records or measured performance.

| Case | Initial observations | First recommendation | What happens next |
|---|---|---|---|
| A: package signal | 8-high; warpage 17 µm; underfill void 0.70%; delamination 0.10%; no electrical trigger | X-ray / CT, from R01 and R02 | A confirmed void does not settle warpage or the other mechanisms. Update only supported findings, then review outstanding obligations. |
| B: competing signals | 12-high; warpage 14 µm; delamination 0.40%; detected interconnect failures = 1 | Acoustic microscopy, from R03; retain R04/R05 if applicable | A delamination confirmation does not cancel electrical isolation. Separately investigate possible microbump involvement. |
| C: no threshold trigger | Acceptance rejected; all three package readings below thresholds; no electrical or sampled-TSV trigger | X-ray / CT, as the first eligible completeness investigation | Low measurements do not establish absence. Continue through unresolved mechanisms; record partial status if the available evidence cannot resolve them. |

## 7. Minimal decision record and comparison boundary

For each decision, record `stack_id`, decision time, input snapshot, rule version, fired/not-evaluable rule IDs, seven evidence states, recommended next procedure and reason. After execution, record the actual procedure, engineer override if any, findings and scope, elapsed time, engineer time, equipment time, and closure status. Keep audit membership independent of the recommendation.

Compare an ML-assisted policy with this version using the same input availability, procedure catalogue and completeness rule. Count inconclusive tests, repeat work and unresolved cases. Use complete audit findings to assess missed mechanisms, including second faults; untested mechanisms outside that cohort are not negative labels. Reordering a set of procedures that all still run does not reduce their summed procedure time.

The delivered v1 CSVs do not contain the diagnostic histories or full-battery flags needed to measure these outcomes. No rule execution, benchmark result or savings estimate is claimed here. The existing synthetic `detected_interconnect_failures` is generated from realised fault states, so performance based on that field would also need an explicit realism caveat.
