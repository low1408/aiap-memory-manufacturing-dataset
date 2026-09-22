"""Scripted teaching branches; these are not measured or stochastic results."""
from __future__ import annotations

from .engine import MECHANISMS, catalogue, procedure_cost, replay_case


def scripted_report(ops: dict, procedure: str, positives: tuple[str, ...] = (), *, inconclusive: bool = False) -> dict:
    proc = catalogue(ops)[procedure]
    report = {
        "procedure": procedure,
        "status": "inconclusive" if inconclusive else "conclusive",
        "findings": [
            {"mechanism": row["mechanism"],
             "result": "inconclusive" if inconclusive else "present" if row["mechanism"] in positives else "absent",
             "scope": row["scope"], "negative_can_support_absence": row["negative_can_support_absence"]}
            for row in proc["binary_outcomes"]
        ],
    }
    if procedure == "IR":
        report["localisation"] = not inconclusive
    return report


def base_case(stack_id: str = "SCRIPTED") -> dict:
    return {
        "stack_id": stack_id, "stack_layer_count": 8, "package_warpage_um": 0,
        "underfill_void_pct": 0, "delamination_area_pct": 0,
        "detected_interconnect_failures": 0, "electrical_test_pass": 1,
        "uncorrected_error_count": 0, "stack_assembly_pass": 0,
        "n_dies_with_detailed_metrology": 1, "sampled_core_tsv_void_mean_pct": 0,
    }


def walkthroughs(ops: dict) -> dict:
    """A, B and C evidence/cost traces; D's appointments belong to scheduler.

    C conditionally authorizes nominal SEM after a future calendar has been
    obtained. This routine never promises an actual SEM start/report time.
    """
    negative_truth = {m: 0 for m in MECHANISMS}
    probabilities = dict(zip(
        ("warpage", "underfill_void", "delamination", "dram_electrical", "tsv_open_short", "microbump_open_bridge", "die_crack"),
        (0.70, 0.10, 0.05, 0.10, 0.10, 0.05, 0.02),
    ))
    a = {**base_case("CASE-A"), "package_warpage_um": 17}
    a_summary, a_events = replay_case(
        a, {**negative_truth, "warpage": 1}, probabilities, "mock", ops, 0, 0, False,
        scripted_reports={"XRAY": scripted_report(ops, "XRAY", ("warpage",))}, max_steps=1,
    )
    a_negative_summary, a_negative_events = replay_case(
        {**a, "stack_id": "CASE-A-NEGATIVE"}, negative_truth, probabilities, "mock", ops, 0, 0, False,
        scripted_reports={"XRAY": scripted_report(ops, "XRAY")}, max_steps=1,
    )
    a_inc_summary, a_inc_events = replay_case(
        {**a, "stack_id": "CASE-A-INCONCLUSIVE"}, {**negative_truth, "warpage": 1}, probabilities, "mock", ops, 0, 0, False,
        scripted_reports={"XRAY": scripted_report(ops, "XRAY", inconclusive=True)}, max_steps=1,
    )
    b = {
        **base_case("CASE-B"), "delamination_area_pct": 0.40,
        "detected_interconnect_failures": 1, "electrical_test_pass": 0,
        "initial_reports": [scripted_report(ops, "XRAY")],
    }
    b_truth = {**negative_truth, "delamination": 1, "tsv_open_short": 1, "microbump_open_bridge": 1}
    b_probabilities = {**probabilities, "warpage": 0.05, "delamination": 0.70}
    reports = {
        "ACOUSTIC": scripted_report(ops, "ACOUSTIC", ("delamination",)),
        "ELECTRICAL": scripted_report(ops, "ELECTRICAL", ("tsv_open_short",)),
        "SEM": scripted_report(ops, "SEM", ("microbump_open_bridge", "tsv_open_short")),
        "IR": scripted_report(ops, "IR"),
    }
    b_summary, b_events = replay_case(b, b_truth, b_probabilities, "mock", ops, 0, 0, False, scripted_reports=reports, max_steps=2)
    c_summary, c_events = replay_case({**b, "stack_id": "CASE-C"}, b_truth, b_probabilities, "mock", ops, 0, 0, False, scripted_reports=reports)
    c_inc_summary, c_inc_events = replay_case(
        {**b, "stack_id": "CASE-C-INCONCLUSIVE"}, b_truth, b_probabilities, "mock", ops, 0, 0, False,
        scripted_reports={**reports, "SEM": scripted_report(ops, "SEM", inconclusive=True)},
    )
    return {
        "A": {"summary": a_summary, "events": a_events, "boundary": "first_CT_attempt_only"},
        "A_negative": {"summary": a_negative_summary, "events": a_negative_events, "boundary": "first_CT_negative_gross_D_does_not_exclude_D"},
        "A_inconclusive": {"summary": a_inc_summary, "events": a_inc_events, "boundary": "first_CT_inconclusive_same_cost_evidence_unresolved"},
        "B": {"summary": b_summary, "events": b_events, "boundary": "prior_CT_plus_two_new_attempts_SEM_pending"},
        "C": {"summary": c_summary, "events": c_events, "boundary": "conditional_nominal_SEM_no_calendar_claim"},
        "C_inconclusive": {"summary": c_inc_summary, "events": c_inc_events, "boundary": "SEM_spent_without_complete_evidence"},
        "D_cost": {"two_CT_attempts": 2 * procedure_cost("XRAY", ops), "boundary": "scheduler_checks_appointments_separately"},
    }
