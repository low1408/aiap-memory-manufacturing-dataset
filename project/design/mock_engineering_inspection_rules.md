# Candidate engineering inspection rules — Helion HBM diagnostics

**Version:** `MOCK-ENG-002`, v0.2
**Purpose:** a transparent, plausible non-ML comparator for choosing the next diagnostic procedure on an already-rejected HBM stack.

The [client brief](../brief/helion_semiconductor_client_brief.md) establishes that routine investigations are selective, that a first confirmed fault is not automatically a complete diagnosis, and that only the independent 1-in-20 audit cohort receives the complete diagnostic battery. The actual Helion SOP, thresholds, stopping standard and exception handling were not supplied. The numerical thresholds and detailed branches below are therefore candidate assumptions to validate with the quality owner, not manufacturer specifications or approved limits.

This version supersedes `MOCK-ENG-001` for future design work. The archived `research_v1` benchmark used `MOCK-ENG-001` and its all-seven closure rule; its results must not be relabelled as results for this version.

## 1. Decision boundary and evidence record

These rules apply after required acceptance testing when `stack_assembly_pass == 0` or `electrical_test_pass == 0`. They recommend one **next procedure** at a time. The on-duty engineer confirms the procedure, interprets its scoped report and approves closure or escalation.

Use only manufacturing/package measurements, initial acceptance observations and diagnostic findings available at the decision time. Do not use `defect_type`, `defect_severity`, `final_disposition`, simulator truth or `fault_*` labels to choose a procedure. The recommendation does not alter the rejected stack's disposition.

Track two separate things:

1. **Mechanism evidence state:** `untested`, `confirmed_present`, `confirmed_absent`, `inconclusive` or `contradictory` for each of the seven mechanisms.
2. **Open diagnostic concerns:** the smaller set of questions raised by the observed failure, a fired rule or a later finding. Routine closure resolves this set; it does not convert every untested mechanism into a confirmed absence.

A low measurement or model probability may leave a mechanism unindicated, but it is not negative diagnostic evidence. For the existing CSVs, use `stack_layer_count` to distinguish 8-high and 12-high. Join records by `stack_id`. The sampled TSV field is `sampled_core_tsv_void_mean_pct`, with coverage recorded in `n_dies_with_detailed_metrology`.

## 2. Candidate inspection triggers

Evaluate every applicable rule. Several concerns may be open at once, and confirmation on one branch does not cancel a different branch.

| ID | Available observation or finding | Open concern / candidate procedure | Required follow-up logic |
|---|---|---|---|
| R01 | `package_warpage_um >= 15` for 8-high, or `>= 18` for 12-high | Warpage; package X-ray / CT | Resolve the warpage concern. Review void and gross-delamination findings reported from the same examination, but do not infer more than its scope. |
| R02 | `underfill_void_pct >= 0.50` | Underfill void; package X-ray / CT | Use acoustic microscopy only if the void concern remains unresolved or finer interface evidence is needed. |
| R03 | `delamination_area_pct >= 0.30` | Delamination; scanning acoustic microscopy | A CT gross-delamination finding may support presence, but a negative CT does not exclude finer delamination. |
| R04 | `detected_interconnect_failures >= 1` or another qualified open/short signature | TSV and microbump differential; electrical fault isolation first | If TSV is confirmed, or the signature remains compatible with both TSV and microbump faults, retain a separate microbump concern for SEM. |
| R05 | Generic electrical rejection: `electrical_test_pass == 0` or `uncorrected_error_count > 0`, without the specific R04 signature | DRAM/base electrical or TSV; electrical fault isolation | Package procedures with active R01–R03 concerns take priority. A conclusive package finding may explain a nonspecific electrical rejection and allow the engineer to retire this generic branch, but never a specific R04 interconnect branch. |
| R06 | At least one core die was measured and `sampled_core_tsv_void_mean_pct >= 0.80` | TSV; electrical fault isolation | If TSV is confirmed or cannot be distinguished from a microbump fault, add the microbump safeguard under R09. |
| R07 | Electrical fault isolation is inconclusive and the electrical concern remains unlocalised | Thermal / IR imaging | IR may localise the next examination but does not itself confirm or exclude a mechanism. |
| R08 | `stack_assembly_pass == 0` and no R01–R03 concern explains the rejection | Unexplained structural/assembly branch; package X-ray / CT as the broad first examination | If conclusive CT does not explain the rejection, escalate deliberately to acoustic or SEM based on its findings and preserved sample evidence; do not automatically run both. |
| R09 | Confirmed TSV fault, unresolved R04 differential, or other qualified evidence specifically implicating microbumps | Microbump co-fault; cross-section / SEM after required nondestructive evidence | This is the explicit safeguard against stopping at a TSV first hit. SEM is not added merely because microbump and crack states began as `untested`. |
| R10 | Package imaging, localisation or physical handling evidence specifically suggests a crack; or an assembly rejection remains unexplained after appropriate nondestructive work | Die crack; cross-section / SEM | Destructive work requires the engineer to confirm that useful nondestructive evidence has been preserved. |

Threshold equality fires the rule. Values below a threshold mean only that the rule did not fire. The percentage fields have different denominators: underfill void is a percentage of inspected underfill cross-section area; delamination is a percentage of inspected package interface area; TSV copper void is a per-via copper-fill void-volume surrogate. `0.50` means **0.50%**, not 50%.

## 3. Choosing the next procedure

First construct the eligible set from currently open concerns. Do not insert an earlier procedure merely because it appears earlier in the catalogue. Among simultaneously eligible procedures, use this provisional priority:

1. **Package X-ray / CT** — 45 minutes.
2. **Scanning acoustic microscopy** — 1.5 hours.
3. **Electrical fault isolation** — 4 hours.
4. **Thermal / IR imaging** — 1 hour, conditional on R07.
5. **Cross-section and SEM** — 2 days, destructive.

This is a priority among useful candidates, not a complete battery. For example:

- If R01 and generic R05 fire, start with CT. A conclusive package explanation can prevent unnecessary fault isolation when no independent electrical signature remains.
- If only R04 fires, start with electrical isolation; do not add CT merely because it is cheaper or earlier in the list.
- If R03 and R04 fire, acoustic and electrical branches both remain open. Resolve both in priority order unless a later scoped finding legitimately changes one branch.

After every report, update only the mechanisms within its documented scope, add any required co-fault concern, remove concerns that now have adequate evidence, and select again. Combine duplicate questions into one examination when its qualified scope permits. Preserve required nondestructive evidence before destructive preparation.

## 4. Routine stopping standard and co-fault safeguard

The candidate routine stopping standard is **concern-complete**, not all-seven complete. Close as `routine_diagnostically_complete` only when:

1. every concern opened by the initial observations, fired rules and subsequent findings is resolved by supported evidence or explicitly retired by the engineer with a recorded explanation;
2. each failed acceptance branch has a supported explanation, or the case is recorded as `unexplained_after_standard_path` and escalated rather than silently closed;
3. the co-fault review below has been performed after every confirmed mechanism;
4. no unresolved contradiction or required procedure remains pending; and
5. the engineer approves closure and records the residual untested mechanisms as **untested**, not absent.

### Mandatory co-fault review

A first positive result triggers a review; it never triggers automatic closure.

- A confirmed TSV fault opens or retains the microbump concern under R09. Resolve it with qualified evidence before routine closure.
- A confirmed microbump fault requires the TSV concern to be resolved if it is not already covered by electrical isolation or SEM evidence.
- A confirmed void does not cancel a separately triggered delamination concern, and a confirmed delamination does not cancel a separately triggered void concern.
- When both assembly and electrical acceptance branches failed, a finding that explains only one branch does not close the other.
- Any additional concern supported by the diagnostic report must be added even if it was not apparent in the initial measurements.

Mechanisms that never became concerns may remain untested in a routine case. The independent audit cohort, not routine closure, measures how often this standard misses an unindicated mechanism or co-fault.

If a required report is inconclusive, contradictory or too narrowly scoped, record `partial_unresolved` and continue a qualified alternative/repeat path or escalate for review. This candidate SOP does not impose an artificial one-attempt limit. Destructive repeat work requires explicit engineer authorisation and sufficient remaining specimen.

## 5. Audit and exception handling

| Situation | Candidate handling |
|---|---|
| `full_battery_sample == 1` | Perform all five procedures regardless of routine triggers, with destructive work last. Audit selection is independent of rules and model scores. All seven mechanisms require supported present/absent findings; inconclusive or contradictory audits remain incomplete. |
| Required measurement missing, invalid or mismatched | Mark the affected trigger `not_evaluable`. Continue independent concerns with valid evidence. Use the failed acceptance branch and existing SOP fallback to select a broad first examination; do not impute a negative. |
| Detailed die metrology is `not_sampled` or `instrument_dropout` | Preserve the reason and observed coverage. R06 is not evaluable without a valid measurement. Do not request a change to the fixed sampling plan or use an observed mean to exclude defects in unmeasured dies. |
| X-ray inconclusive | Retain only the affected package concerns. Use acoustic microscopy where its scope is suitable; otherwise seek a qualified repeat/review. |
| Acoustic microscopy inconclusive | Retain the void/delamination concern and choose a qualified repeat or alternative. Do not assume SEM automatically resolves interface-wide questions. |
| Electrical isolation inconclusive | Apply R07 where localisation would change the next examination. Keep DRAM/base, TSV and microbump concerns separate. |
| IR inconclusive | Keep the electrical concern unresolved and escalate; IR does not create a negative mechanism finding. |
| SEM inconclusive or limited in scope | Retain only the unresolved structural concerns. Do not claim package-wide absence from an unrepresentative section. |
| Findings conflict | Preserve both reports, mark the mechanism `contradictory`, and require engineer review before closure or destructive escalation. |
| Required instrument unavailable | Record the pending concern and procedure. Another independent branch may proceed, but equipment unavailability does not resolve the original concern. |
| New bonder, supplier or unqualified process version | Flag the provisional thresholds as outside their qualified context and use engineer review/current approved SOP. Do not extrapolate a fault-specific rule from the new identity alone. |

## 6. Worked routine examples

These examples illustrate the candidate logic; they are not measured Helion outcomes.

| Case | Initial observations | Candidate path | Routine stopping implication |
|---|---|---|---|
| A: package-only signal | 8-high; warpage 17 µm; void 0.20%; delamination 0.10%; no specific electrical signature | CT from R01 | If CT conclusively confirms warpage and reports no additional scoped concern, the engineer may close without acoustic, electrical isolation or SEM. Untested mechanisms remain recorded as untested. |
| B: generic electrical rejection plus package signal | Warpage 17 µm; generic electrical failure; no R04 interconnect signature | CT before the R05 candidate | If CT confirms a package mechanism that adequately explains the nonspecific rejection, the engineer may retire R05 and avoid four-hour fault isolation. If it does not, electrical isolation remains next. |
| C: specific interconnect signature | `detected_interconnect_failures >= 1`; no assembly/package concern | Electrical isolation from R04 | If TSV is confirmed, resolve the retained microbump concern with SEM. Do not add CT or acoustic without a package concern. |
| D: two independent branches | Delamination above threshold and a specific interconnect signature | Acoustic from R03, then electrical from R04 | Confirmation of delamination does not cancel the interconnect branch. SEM is added only if the TSV/microbump differential remains open. |
| E: unexplained assembly rejection | Assembly failed; package readings below thresholds; no electrical failure | CT from R08 | A conclusive negative CT does not close the case. Escalate based on the report and intact-sample review; do not automatically perform the entire battery. |

## 7. Decision record and comparison boundary

For every recommendation, record `stack_id`, decision time, input snapshot, rule version, fired/not-evaluable rules, open concerns, seven evidence states, eligible procedures, selected next procedure and reason. After execution, record the actual procedure, override, scoped findings, elapsed time, engineer time, equipment time, repeat/escalation reason and closure status. Preserve independent audit membership separately.

Compare an ML-assisted policy with this candidate SOP using the same input availability, procedure catalogue, concern-opening rules, co-fault safeguards and stopping standard. Give both policies the same opportunity to avoid work. Primary decision metrics should include resource cost and elapsed time to routine closure, unresolved/escalated cases, repeat work and engineer overrides. Use independently selected complete audits to estimate missed mechanisms and missed co-faults; outside that cohort, an untested mechanism is unknown rather than negative.

The delivered v1 CSVs do not contain the diagnostic histories, actual incumbent actions or full-battery flags needed to measure this procedure. Before treating it as a client baseline, validate the thresholds, branch-retirement authority, co-fault pairs, repeat rules and closure outcomes with the quality owner. If the approved SOP differs, replace this candidate rather than tuning it until the model appears beneficial.
