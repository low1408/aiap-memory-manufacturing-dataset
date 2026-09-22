"""Scoped diagnostic evidence, policies and paired synthetic potential reports.

Policies consume observations, model probabilities and recorded reports only.
Hidden synthetic fault truth is confined to ``potential_report`` and
``evaluate_state``. This module simulates nominal attempts, not appointments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Any


MECHANISMS = (
    "dram_electrical", "tsv_open_short", "microbump_open_bridge", "die_crack",
    "warpage", "underfill_void", "delamination",
)
PROCEDURE_ORDER = ("XRAY", "ACOUSTIC", "ELECTRICAL", "IR", "SEM")
RESOLVED = frozenset(("confirmed_present", "confirmed_absent"))
INTACT_MECHANISMS = ("warpage", "underfill_void", "delamination", "dram_electrical")


def uniform_draw(seed: int, *key: Any) -> float:
    """Order-independent deterministic pseudo-uniform; no global RNG state."""
    payload = json.dumps([int(seed), *key], separators=(",", ":"), sort_keys=True)
    integer = int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")
    return (integer + 0.5) / 2**64


def _value(values: dict, mechanism: str) -> Any:
    return values.get(mechanism, values.get(f"fault_{mechanism}"))


def _finite(value: Any) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def catalogue(ops: dict) -> dict[str, dict]:
    return {row["id"]: row for row in ops["procedures"]}


def procedure_resources(procedure: str, ops: dict) -> dict:
    """Charge attended labour, instrument occupancy and supplies once per attempt."""
    proc = catalogue(ops)[procedure]
    staff = {row["role"]: row["rate_per_hour"] for row in ops["staff_pools"]}
    equipment = {row["id"]: row["rate_per_hour"] for row in ops["equipment"]}
    technician = float(proc["technician_hours"])
    engineer = float(proc["engineer_hours"])
    instrument_hours = dict(proc["equipment_hours"])
    labour = technician * staff["technician"] + engineer * staff["quality_engineer"]
    instrument_cost = sum(hours * equipment[key] for key, hours in instrument_hours.items())
    supplies = float(proc["consumables"])
    return {
        "spent_cost": float(labour + instrument_cost + supplies),
        "labor_cost": float(labour), "equipment_cost": float(instrument_cost),
        "consumables_cost": supplies, "technician_hours": technician,
        "engineer_hours": engineer, "equipment_hours": float(sum(instrument_hours.values())),
        "equipment_hours_by_resource": instrument_hours,
        "nominal_hours": float(proc.get("nominal_envelope_hours", proc.get("minimum_start_to_report_hours", 0))),
    }


def procedure_cost(procedure: str, ops: dict) -> float:
    return procedure_resources(procedure, ops)["spent_cost"]


@dataclass(frozen=True)
class CaseSnapshot:
    stack_id: str
    observations: dict
    availability: dict = field(default_factory=dict)
    qualification_context: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, case: dict) -> "CaseSnapshot":
        # An explicit projection prevents target/simulator columns entering policy input.
        allowed = (
            "stack_layer_count", "package_warpage_um", "underfill_void_pct",
            "delamination_area_pct", "detected_interconnect_failures",
            "electrical_test_pass", "uncorrected_error_count", "stack_assembly_pass",
            "n_dies_with_detailed_metrology", "sampled_core_tsv_void_mean_pct",
        )
        observations = case.get("observations", case)
        context = dict(case.get("qualification_context") or {})
        flags = case.get("qualification_flags", [])
        if flags:
            context["flags"] = list(flags) if isinstance(flags, (list, tuple)) else [flags]
        for flag in ("new_tool", "new_supplier", "new_bonder", "unsupported_process"):
            if case.get(flag):
                context.setdefault("flags", []).append(flag)
        return cls(
            str(case["stack_id"]), {k: observations.get(k) for k in allowed},
            dict(case.get("availability") or {}), context,
        )


@dataclass
class InvestigationState:
    states: dict = field(default_factory=lambda: {m: "untested" for m in MECHANISMS})
    evidence: dict = field(default_factory=lambda: {m: [] for m in MECHANISMS})
    reports: list = field(default_factory=list)
    attempted: list = field(default_factory=list)
    review_flags: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    localisation: bool = False
    audit: bool = False

    @property
    def unresolved(self) -> list[str]:
        return [m for m in MECHANISMS if self.states[m] not in RESOLVED]


def initial_state(case: dict, audit: bool = False) -> InvestigationState:
    state = InvestigationState(audit=bool(audit))
    snapshot = CaseSnapshot.from_dict(case)
    context = snapshot.qualification_context
    if context.get("qualified") is False or context.get("status") in {"unqualified", "unsupported", "review_required"} or context.get("flags"):
        state.review_flags.append("qualification_review_required")
    for report in case.get("initial_reports", []):
        apply_report(state, report)
    return state


def apply_report(state: InvestigationState, report: dict) -> None:
    """Apply only reported scope, preserving earlier conclusive evidence after q.

    Every examination reports its full simulated validated catalogue, including
    overlap with already resolved questions. Contradiction cannot be hidden by
    dropping an inconvenient report or updating unresolved mechanisms only.
    """
    procedure = report["procedure"]
    if procedure not in PROCEDURE_ORDER:
        raise ValueError(f"Unknown procedure: {procedure}")
    if procedure in state.attempted:
        raise ValueError(f"A second {procedure} attempt requires manual review")
    if report.get("status") not in {"conclusive", "inconclusive"}:
        raise ValueError("Report status must be conclusive or inconclusive")
    if procedure == "IR" and report.get("findings"):
        raise ValueError("IR has localisation scope only")
    allowed_scope = {
        "XRAY": {"warpage", "underfill_void", "delamination"},
        "ACOUSTIC": {"delamination", "underfill_void"},
        "ELECTRICAL": {"dram_electrical", "tsv_open_short"},
        "SEM": {"microbump_open_bridge", "die_crack", "tsv_open_short"},
        "IR": set(),
    }[procedure]
    seen = set()
    for finding in report.get("findings", []):
        mechanism = finding["mechanism"]
        if mechanism not in allowed_scope or mechanism in seen:
            raise ValueError(f"Invalid/duplicate {procedure} report mechanism: {mechanism}")
        seen.add(mechanism)
        result = finding["result"]
        if result not in {"present", "absent", "inconclusive"}:
            raise ValueError(f"Invalid finding: {result}")
        if report["status"] == "inconclusive" and result != "inconclusive":
            raise ValueError("A shared inconclusive report cannot contain conclusive findings")
    # Validate the whole report before changing any evidence or attempt history.
    state.attempted.append(procedure)
    state.reports.append(report)
    if procedure == "IR":
        state.localisation = report["status"] == "conclusive" and bool(report.get("localisation", True))
        if not state.localisation:
            state.review_flags.append("localisation_unresolved_requires_review")
        return
    for finding in report.get("findings", []):
        mechanism = finding["mechanism"]
        result = finding["result"]
        evidence = {"procedure": procedure, **finding}
        state.evidence[mechanism].append(evidence)
        if result == "inconclusive":
            if state.states[mechanism] == "untested":
                state.states[mechanism] = "inconclusive"
            continue
        # CT addresses gross D only, regardless of malformed imported scope flags.
        if result == "absent" and (
            not finding.get("negative_can_support_absence", False)
            or finding.get("scope") not in {"whole_sample_assumption", "whole_sample_assumption_requires_qualification"}
            or (procedure == "XRAY" and mechanism == "delamination")
        ):
            continue
        incoming = f"confirmed_{result}"
        previous = state.states[mechanism]
        if mechanism in state.contradictions:
            continue
        if previous in RESOLVED and previous != incoming:
            state.states[mechanism] = "inconclusive"
            state.contradictions.append(mechanism)
            state.review_flags.append(f"contradictory_evidence:{mechanism}")
        else:
            state.states[mechanism] = incoming


def trigger_rules(case: CaseSnapshot, state: InvestigationState) -> dict:
    """Evaluate teaching thresholds; missing observations stay not evaluable."""
    obs = case.observations
    fired: list[str] = []
    unknown: list[str] = []
    triggers: dict[str, list[str]] = {p: [] for p in PROCEDURE_ORDER}
    unresolved = set(state.unresolved)

    def rule(rule_id: str, known: bool, condition: bool, procedure: str, questions: set[str]) -> None:
        if not known:
            unknown.append(rule_id)
        elif condition:
            fired.append(rule_id)
            if unresolved & questions:
                triggers[procedure].append(rule_id)

    layer = obs.get("stack_layer_count")
    warpage = obs.get("package_warpage_um")
    known = _finite(layer) and float(layer) in (8, 12) and _finite(warpage)
    rule("R01", known, bool(known and float(warpage) >= (15 if float(layer) == 8 else 18)), "XRAY", {"warpage"})
    void = obs.get("underfill_void_pct")
    known = _finite(void)
    rule("R02", known, bool(known and float(void) >= 0.50), "XRAY", {"underfill_void"})
    if "R02" in fired and "XRAY" in state.attempted and "underfill_void" in unresolved:
        triggers["ACOUSTIC"].append("R02_followup")
    delam = obs.get("delamination_area_pct")
    known = _finite(delam)
    rule("R03", known, bool(known and float(delam) >= 0.30), "ACOUSTIC", {"delamination"})
    interconnect = obs.get("detected_interconnect_failures")
    known = _finite(interconnect)
    rule("R04", known, bool(known and float(interconnect) >= 1), "ELECTRICAL", {"dram_electrical", "tsv_open_short"})
    electrical, errors = obs.get("electrical_test_pass"), obs.get("uncorrected_error_count")
    # Three-valued OR: an observed positive trigger suffices despite a missing other field.
    condition = (_finite(electrical) and float(electrical) == 0) or (_finite(errors) and float(errors) > 0)
    known = condition or (_finite(electrical) and _finite(errors))
    rule("R05", known, condition, "ELECTRICAL", {"dram_electrical", "tsv_open_short"})
    n_measured, tsv = obs.get("n_dies_with_detailed_metrology"), obs.get("sampled_core_tsv_void_mean_pct")
    known = _finite(n_measured) and float(n_measured) > 0 and _finite(tsv)
    rule("R06", known, bool(known and float(tsv) >= 0.80), "ELECTRICAL", {"tsv_open_short"})
    electrical_inconclusive = any(r["procedure"] == "ELECTRICAL" and r["status"] == "inconclusive" for r in state.reports)
    if electrical_inconclusive and not state.localisation:
        fired.append("R07")
        triggers["IR"].append("R07")
    if unresolved & {"microbump_open_bridge", "die_crack", "tsv_open_short"}:
        # Eligibility enforces the prior nondestructive evidence requirement.
        triggers["SEM"].append("R08_completeness")
    return {"fired": fired, "not_evaluable": unknown, "triggered_procedures": triggers}


def _useful_questions(state: InvestigationState, procedure: dict) -> list[str]:
    return [r["mechanism"] for r in procedure["binary_outcomes"] if r["mechanism"] in state.unresolved]


def procedure_candidates(case: CaseSnapshot, state: InvestigationState, ops: dict) -> tuple[list[dict], list[dict], dict]:
    """Return eligible and blocked known obligations, never hidden truth."""
    rules = trigger_rules(case, state)
    cat = catalogue(ops)
    eligible, blocked = [], []
    desired = []
    for name in PROCEDURE_ORDER:
        if name in state.attempted:
            continue
        questions = _useful_questions(state, cat[name])
        triggered = rules["triggered_procedures"][name]
        wanted = state.audit or bool(questions) or bool(triggered)
        if name == "IR":
            wanted = state.audit or bool(triggered)
        if wanted:
            desired.append({"procedure": name, "questions": questions,
                            "trigger_rules": triggered, "cost": procedure_cost(name, ops)})
    nondestructive_pending = [r["procedure"] for r in desired if r["procedure"] != "SEM"]
    for record in desired:
        reasons = []
        if "qualification_review_required" in state.review_flags:
            reasons.append("qualification_review_required")
        if record["procedure"] == "SEM":
            if state.review_flags:
                reasons.append("manual_review_before_destruction")
            missing = [m for m in INTACT_MECHANISMS if state.states[m] not in RESOLVED]
            if missing:
                reasons.append("unresolved_intact_sample_evidence:" + ",".join(missing))
            if nondestructive_pending:
                reasons.append("required_nondestructive_procedures_pending:" + ",".join(nondestructive_pending))
        if record["procedure"] == "IR" and "ELECTRICAL" not in state.attempted:
            reasons.append("electrical_examination_precedes_localisation")
        (blocked if reasons else eligible).append({**record, "blocked_reasons": reasons})
    return eligible, blocked, rules


def recommend(case: CaseSnapshot | dict, state: InvestigationState, probabilities: dict, policy: str, ops: dict) -> dict:
    """Select next procedure under shared eligibility; probabilities stay static."""
    if isinstance(case, dict):
        case = CaseSnapshot.from_dict(case)
    if policy not in {"mock", "ct_first", "heuristic"}:
        raise ValueError(f"Unknown policy {policy}")
    eligible, blocked, rules = procedure_candidates(case, state, ops)
    effective_policy = policy
    fallback = None
    if policy == "heuristic":
        if case.availability.get("import_valid") is False or case.availability.get("scores_valid") is False:
            effective_policy, fallback = "mock", "invalid_import_or_scores"
        elif any(not _finite(_value(probabilities, m)) or not 0 <= float(_value(probabilities, m)) <= 1 for m in MECHANISMS):
            effective_policy, fallback = "mock", "missing_or_invalid_probabilities"
    cat = catalogue(ops)
    ranked = []
    gross_fraction = float(ops["outcome_generation_contract"]["gross_fraction_given_delamination"])
    for choice in eligible:
        weighted_coverage = 0.0
        if effective_policy == "heuristic":
            for mechanism in choice["questions"]:
                weight = gross_fraction if choice["procedure"] == "XRAY" and mechanism == "delamination" else 1.0
                weighted_coverage += weight * float(_value(probabilities, mechanism))
        score = (1 - cat[choice["procedure"]]["inconclusive_probability"]) * weighted_coverage / choice["cost"]
        ranked.append({**choice, "score": score})
    order = {name: i for i, name in enumerate(PROCEDURE_ORDER)}
    if state.audit:
        # Audit selection and fixed battery order are independent of model scores.
        pool = sorted(ranked, key=lambda r: order[r["procedure"]])
    elif effective_policy == "mock":
        triggered = [r for r in ranked if r["trigger_rules"]]
        pool = triggered or ranked
        pool.sort(key=lambda r: order[r["procedure"]])
    elif effective_policy == "ct_first":
        pool = sorted(ranked, key=lambda r: order[r["procedure"]])
    else:
        pool = sorted(ranked, key=lambda r: (-r["score"], order[r["procedure"]]))
    choice = pool[0] if pool else None
    return {
        "procedure": choice["procedure"] if choice else None,
        "policy": policy, "effective_policy": effective_policy, "fallback": fallback,
        "reason": ("independent_audit_fixed_order" if state.audit and choice
                   else "triggered_branch" if effective_policy == "mock" and choice and choice["trigger_rules"]
                   else "coverage_cost_heuristic" if effective_policy == "heuristic" and choice
                   else "completeness_fixed_order" if choice else "no_eligible_procedure"),
        "selected": choice, "eligible": ranked, "blocked": blocked,
        "unresolved_mechanisms": state.unresolved, "rules": rules,
        "score_interpretation": "positive_unresolved_coverage_per_resource_dollar_not_completion_probability",
    }


def potential_report(stack_id: str, truths: dict, procedure: str, ops: dict, seed: int, replication: int) -> dict:
    """Draw the same potential report for this sample/procedure in every arm."""
    for mechanism in MECHANISMS:
        if _value(truths, mechanism) not in (0, 1, False, True):
            raise ValueError(f"Unknown or nonbinary simulator truth: {mechanism}")
    proc = catalogue(ops)[procedure]
    inconclusive = uniform_draw(seed, replication, str(stack_id), procedure, "conclusiveness") < proc["inconclusive_probability"]
    report = {"procedure": procedure, "status": "inconclusive" if inconclusive else "conclusive", "findings": []}
    if procedure == "IR":
        report["localisation"] = not inconclusive
        return report
    gross = bool(_value(truths, "delamination")) and uniform_draw(seed, str(stack_id), "gross_subtype") < ops["outcome_generation_contract"]["gross_fraction_given_delamination"]
    for outcome in proc["binary_outcomes"]:
        mechanism = outcome["mechanism"]
        if inconclusive:
            result = "inconclusive"
        else:
            truth = gross if outcome["scope"] == "gross_subtype_only" else bool(_value(truths, mechanism))
            p_positive = outcome["sensitivity_if_conclusive"] if truth else 1 - outcome["specificity_if_conclusive"]
            positive = uniform_draw(seed, replication, str(stack_id), procedure, mechanism, outcome["scope"]) < p_positive
            result = "present" if positive else "absent"
        report["findings"].append({
            "mechanism": mechanism, "result": result, "scope": outcome["scope"],
            "negative_can_support_absence": outcome["negative_can_support_absence"],
        })
    return report


def evaluate_state(state: InvestigationState, truths: dict) -> dict:
    """Evaluator-only truth comparison; an evidence-complete record can be wrong."""
    if any(_value(truths, m) not in (0, 1, False, True) for m in MECHANISMS):
        raise ValueError("Evaluation requires explicitly observed binary synthetic targets")
    false_absences = sum(state.states[m] == "confirmed_absent" and bool(_value(truths, m)) for m in MECHANISMS)
    false_positives = sum(state.states[m] == "confirmed_present" and not bool(_value(truths, m)) for m in MECHANISMS)
    missed = sum(bool(_value(truths, m)) and state.states[m] != "confirmed_present" for m in MECHANISMS)
    fault_count = sum(bool(_value(truths, m)) for m in MECHANISMS)
    mechanism_evidence_complete = not state.unresolved and not state.contradictions
    supported = mechanism_evidence_complete and not state.review_flags
    audit_complete = bool(state.audit and set(state.attempted) == set(PROCEDURE_ORDER) and all(r["status"] == "conclusive" for r in state.reports) and supported)
    complete = bool(supported and (not state.audit or audit_complete))
    return {
        "complete": complete, "evidence_complete": complete,
        "mechanism_evidence_complete": bool(mechanism_evidence_complete),
        "correctly_complete": complete and false_absences == 0 and false_positives == 0,
        "audit_complete": audit_complete, "false_absences": int(false_absences),
        "false_positives": int(false_positives), "missed_faults": int(missed),
        "missed_coexisting_faults": int(missed if fault_count > 1 else 0),
        "coexisting_fault_case": fault_count > 1, "truth_fault_count": fault_count,
        "incorrectly_complete": int(complete and (false_absences > 0 or false_positives > 0)),
        "unresolved_count": len(state.unresolved), "unresolved_mechanisms": state.unresolved,
    }


def replay_case(case: dict, truths: dict, probabilities: dict, policy: str, ops: dict,
                seed: int, replication: int, audit: bool, *, scripted_reports: dict | None = None,
                max_steps: int = 5) -> tuple[dict, list[dict]]:
    """Replay one nominal investigation, returning all-case summary and events.

    ``scripted_reports`` maps procedure IDs to qualified report dictionaries.
    ``case.initial_reports`` incurs its historical attempt costs in the full total.
    ``max_steps`` bounds NEW attempts; pending work remains separately visible.
    No calendar or actual turnaround is inferred from these nominal attempts.
    """
    snapshot = CaseSnapshot.from_dict(case)
    state = initial_state(case, audit)
    totals = {key: 0.0 for key in (
        "spent_cost", "labor_cost", "equipment_cost", "consumables_cost",
        "technician_hours", "engineer_hours", "equipment_hours", "nominal_hours",
    )}
    equipment_by_resource: dict[str, float] = {}
    events = []

    def account(procedure: str) -> dict:
        resources = procedure_resources(procedure, ops)
        for key in totals:
            totals[key] += resources[key]
        for key, hours in resources["equipment_hours_by_resource"].items():
            equipment_by_resource[key] = equipment_by_resource.get(key, 0.0) + hours
        return resources

    for report in state.reports:
        account(report["procedure"])
    initial_spent_cost = totals["spent_cost"]
    for step in range(max_steps):
        recommendation = recommend(snapshot, state, probabilities, policy, ops)
        procedure = recommendation["procedure"]
        if procedure is None:
            break
        report = (scripted_reports[procedure] if scripted_reports and procedure in scripted_reports
                  else potential_report(snapshot.stack_id, truths, procedure, ops, seed, replication))
        if report["procedure"] != procedure:
            raise ValueError("Scripted report does not match the selected procedure")
        before = dict(state.states)
        apply_report(state, report)
        resources = account(procedure)
        events.append({
            "stack_id": snapshot.stack_id, "policy": policy, "replication": replication,
            "step": step + 1, "procedure": procedure, "recommendation": recommendation,
            "report": report, "resources": resources, "cumulative_cost": totals["spent_cost"],
            "states_before": before, "states_after": dict(state.states),
            "unresolved_mechanisms": state.unresolved, "review_flags": list(state.review_flags),
        })
    terminal = recommend(snapshot, state, probabilities, policy, ops)
    pending_records = terminal["eligible"] + terminal["blocked"]
    pending = [p for p in PROCEDURE_ORDER if any(r["procedure"] == p for r in pending_records)]
    quality = evaluate_state(state, truths)
    inconclusive = sum(r["status"] == "inconclusive" for r in state.reports)
    review_pending = bool(state.review_flags or (not quality["complete"] and terminal["procedure"] is None))
    summary = {
        "stack_id": snapshot.stack_id, "policy": policy, "replication": replication,
        "audit": bool(audit), **totals, **quality,
        "initial_spent_cost": initial_spent_cost,
        "equipment_hours_by_resource": equipment_by_resource,
        "pending_cost": float(sum(procedure_cost(p, ops) for p in pending)),
        "pending_cost_basis": "unattempted_known_procedure_obligations_not_cost_to_completion",
        "pending_procedures": pending, "blocked_procedures": terminal["blocked"],
        "review_pending": review_pending, "review_flags": list(state.review_flags),
        "contradictions": list(state.contradictions), "attempts": len(state.attempted),
        "inconclusive_attempts": int(inconclusive), "repeated_attempts": 0,
        "engineer_overrides": None, "override_status": "not_observed_in_synthetic_replay",
        "attempted_procedures": list(state.attempted), "final_states": dict(state.states),
        "supporting_evidence": state.evidence, "initial_recommendation": events[0]["procedure"] if events else None,
        "terminal_recommendation": terminal, "not_evaluable_rules": terminal["rules"]["not_evaluable"],
        "ending": "evidence_complete_pending_engineer_review" if quality["complete"] else
                  "bounded_trace_with_pending_work" if terminal["procedure"] else "partial_unresolved_review_required",
        "time_basis": "sum_of_nominal_procedure_envelopes_not_actual_turnaround",
        "manual_review_cost": None,
    }
    return summary, events
