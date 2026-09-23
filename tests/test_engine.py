"""Evidence/decision tests defend the business constraints, not model internals."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from helion_pipeline.engine import (
    MECHANISMS, PROCEDURE_ORDER, CaseSnapshot, InvestigationState, apply_report,
    evaluate_state, initial_state, potential_report, procedure_cost,
    procedure_resources, recommend, replay_case, trigger_rules,
)
from helion_pipeline.fixtures import base_case, scripted_report, walkthroughs

ROOT = Path(__file__).resolve().parents[1]
OPS = json.loads((ROOT / "synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.json").read_text())
TRUTH = {m: 0 for m in MECHANISMS}
PROBS = {m: 0.1 for m in MECHANISMS}


class EvidenceTests(unittest.TestCase):
    def test_gross_negative_does_not_exclude_general_delamination(self):
        state = InvestigationState()
        report = scripted_report(OPS, "XRAY")
        # Even a malformed positive absence-capability flag cannot widen CT.
        report["findings"][2]["negative_can_support_absence"] = True
        apply_report(state, report)
        self.assertEqual(state.states["warpage"], "confirmed_absent")
        self.assertEqual(state.states["underfill_void"], "confirmed_absent")
        self.assertEqual(state.states["delamination"], "untested")

    def test_region_negative_does_not_exclude_whole_sample(self):
        report = scripted_report(OPS, "SEM")
        report["findings"][1]["scope"] = "one_examined_region"
        state = InvestigationState()
        apply_report(state, report)
        self.assertEqual(state.states["die_crack"], "untested")

    def test_inconclusive_overlap_preserves_conclusive_evidence(self):
        state = InvestigationState()
        apply_report(state, scripted_report(OPS, "ELECTRICAL", ("tsv_open_short",)))
        apply_report(state, scripted_report(OPS, "SEM", inconclusive=True))
        self.assertEqual(state.states["tsv_open_short"], "confirmed_present")
        self.assertEqual(state.states["microbump_open_bridge"], "inconclusive")
        self.assertFalse(evaluate_state(state, TRUTH)["complete"])

    def test_contradiction_requires_review_and_blocks_destruction(self):
        state = InvestigationState()
        apply_report(state, scripted_report(OPS, "XRAY"))
        apply_report(state, scripted_report(OPS, "ACOUSTIC", ("underfill_void",)))
        apply_report(state, scripted_report(OPS, "ELECTRICAL"))
        recommendation = recommend(base_case(), state, PROBS, "mock", OPS)
        self.assertEqual(state.states["underfill_void"], "inconclusive")
        self.assertIn("underfill_void", state.contradictions)
        self.assertIsNone(recommendation["procedure"])
        self.assertTrue(any(r["procedure"] == "SEM" for r in recommendation["blocked"]))

    def test_ir_localisation_does_not_change_mechanism_states(self):
        state = InvestigationState()
        before = dict(state.states)
        apply_report(state, scripted_report(OPS, "IR"))
        self.assertTrue(state.localisation)
        self.assertEqual(before, state.states)
        with self.assertRaises(ValueError):
            apply_report(InvestigationState(), {"procedure": "IR", "status": "conclusive", "findings": [{"mechanism": "dram_electrical", "result": "present"}]})

    def test_one_bounded_nondestructive_repeat_after_inconclusive(self):
        state = InvestigationState()
        report = scripted_report(OPS, "XRAY", inconclusive=True)
        apply_report(state, report)
        case = {**base_case(), "package_warpage_um": 17}
        choice = recommend(case, state, PROBS, "mock", OPS)
        self.assertEqual(choice["procedure"], "XRAY")
        apply_report(state, report)
        choice = recommend(case, state, PROBS, "mock", OPS)
        self.assertIsNone(choice["procedure"])

    def test_tsv_first_positive_opens_microbump_safeguard(self):
        case = {**base_case(), "stack_assembly_pass": 1, "electrical_test_pass": 0,
                "detected_interconnect_failures": 1}
        state = InvestigationState()
        apply_report(state, scripted_report(OPS, "ELECTRICAL", ("tsv_open_short",)))
        recommendation = recommend(case, state, {m: 0.0 for m in MECHANISMS}, "heuristic", OPS)
        self.assertFalse(evaluate_state(state, {**TRUTH, "tsv_open_short": 1}, case)["complete"])
        self.assertEqual(recommendation["procedure"], "SEM")
        self.assertEqual(state.states["die_crack"], "untested")

    def test_hidden_truth_never_enters_case_snapshot(self):
        case = {**base_case(), "fault_delamination": 1, "latent_failure": 22,
                "observations": {**base_case(), "fault_delamination": 1}}
        snapshot = CaseSnapshot.from_dict(case)
        self.assertNotIn("fault_delamination", snapshot.observations)
        self.assertNotIn("latent_failure", snapshot.observations)

    def test_invalid_report_leaves_state_unchanged(self):
        state = InvestigationState()
        before = deepcopy(state)
        bad = scripted_report(OPS, "XRAY")
        bad["findings"][-1]["mechanism"] = "die_crack"
        with self.assertRaises(ValueError):
            apply_report(state, bad)
        self.assertEqual(state, before)

    def test_mechanism_evidence_distinct_from_audit_and_review_status(self):
        state = InvestigationState(audit=True)
        for procedure in ("XRAY", "ACOUSTIC", "ELECTRICAL", "SEM"):
            apply_report(state, scripted_report(OPS, procedure))
        apply_report(state, scripted_report(OPS, "IR", inconclusive=True))
        result = evaluate_state(state, TRUTH)
        self.assertTrue(result["mechanism_evidence_complete"])
        self.assertFalse(result["audit_complete"])
        self.assertFalse(result["complete"])


class SelectionTests(unittest.TestCase):
    def test_specific_interconnect_branch_does_not_add_unindicated_ct(self):
        case = {**base_case(), "stack_assembly_pass": 1, "electrical_test_pass": 0,
                "detected_interconnect_failures": 1}
        self.assertEqual(recommend(case, InvestigationState(), PROBS, "mock", OPS)["procedure"], "ELECTRICAL")
        self.assertEqual(recommend(case, InvestigationState(), PROBS, "ct_first", OPS)["procedure"], "ELECTRICAL")

    def test_mock_acoustic_before_electrical_competing_triggers(self):
        case = {**base_case(), "electrical_test_pass": 0, "delamination_area_pct": 0.4}
        self.assertEqual(recommend(case, InvestigationState(), PROBS, "mock", OPS)["procedure"], "ACOUSTIC")

    def test_missing_measurement_is_not_negative_trigger_or_label(self):
        case = {**base_case(), "package_warpage_um": None, "sampled_core_tsv_void_mean_pct": None,
                "n_dies_with_detailed_metrology": 0}
        rules = trigger_rules(CaseSnapshot.from_dict(case), InvestigationState())
        self.assertIn("R01", rules["not_evaluable"])
        self.assertIn("R06", rules["not_evaluable"])
        self.assertEqual(recommend(case, InvestigationState(), PROBS, "mock", OPS)["procedure"], "XRAY")

    def test_known_positive_or_trigger_can_use_one_missing_operand(self):
        case = {**base_case(), "electrical_test_pass": None, "uncorrected_error_count": 2}
        rules = trigger_rules(CaseSnapshot.from_dict(case), InvestigationState())
        self.assertIn("R05", rules["fired"])
        self.assertNotIn("R05", rules["not_evaluable"])

    def test_threshold_equality_and_product_height(self):
        for height, value in ((8, 15), (12, 18)):
            rules = trigger_rules(CaseSnapshot.from_dict({**base_case(), "stack_layer_count": height, "package_warpage_um": value}), InvestigationState())
            self.assertIn("R01", rules["fired"])

    def test_heuristic_uses_gross_fraction_not_completion_probability(self):
        case = {**base_case(), "package_warpage_um": 15, "delamination_area_pct": .30}
        result = recommend(case, InvestigationState(), {m: 1.0 for m in MECHANISMS}, "heuristic", OPS)
        scores = {r["procedure"]: r["score"] for r in result["eligible"]}
        self.assertAlmostEqual(scores["XRAY"], 0.9 / 120)
        self.assertAlmostEqual(scores["ACOUSTIC"], 0.85 / 200)

    def test_failed_import_falls_back_to_existing_rules(self):
        case = {**base_case(), "stack_assembly_pass": 1, "electrical_test_pass": 0,
                "availability": {"import_valid": False}}
        choice = recommend(case, InvestigationState(), PROBS, "heuristic", OPS)
        self.assertEqual(choice["procedure"], "ELECTRICAL")
        self.assertEqual(choice["effective_policy"], "mock")
        self.assertEqual(choice["fallback"], "invalid_import_or_scores")

    def test_unsupported_tool_and_supplier_require_manual_review(self):
        for flag in ("new_tool", "new_supplier"):
            case = {**base_case(), "qualification_flags": [flag]}
            summary, events = replay_case(case, TRUTH, PROBS, "heuristic", OPS, 42, 0, False)
            self.assertEqual(summary["spent_cost"], 0)
            self.assertEqual(events, [])
            self.assertTrue(summary["review_pending"])
            self.assertFalse(summary["complete"])


class PotentialReportTests(unittest.TestCase):
    def test_paired_reports_are_stable_and_policy_order_independent(self):
        a = potential_report("S1", TRUTH, "XRAY", OPS, 23, 7)
        potential_report("S9", TRUTH, "SEM", OPS, 23, 99)
        b = potential_report("S1", TRUTH, "XRAY", OPS, 23, 7)
        self.assertEqual(a, b)
        case = {**base_case("S1"), "electrical_test_pass": 0}
        left = replay_case(case, TRUTH, PROBS, "mock", OPS, 23, 7, False)[1]
        right = replay_case(case, TRUTH, PROBS, "ct_first", OPS, 23, 7, False)[1]
        left_reports = {e["procedure"]: e["report"] for e in left}
        right_reports = {e["procedure"]: e["report"] for e in right}
        for procedure in left_reports.keys() & right_reports.keys():
            self.assertEqual(left_reports[procedure], right_reports[procedure])

    def test_one_shared_inconclusive_event_per_procedure(self):
        ops = deepcopy(OPS)
        ops["procedures"][0]["inconclusive_probability"] = 1
        report = potential_report("S1", TRUTH, "XRAY", ops, 42, 0)
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual({f["result"] for f in report["findings"]}, {"inconclusive"})

    def test_gross_subtype_fixed_across_outcome_replications(self):
        ops = deepcopy(OPS)
        ops["procedures"][0]["inconclusive_probability"] = 0
        for row in ops["procedures"][0]["binary_outcomes"]:
            row["sensitivity_if_conclusive"] = 1
            row["specificity_if_conclusive"] = 1
        reports = [potential_report("S1", {**TRUTH, "delamination": 1}, "XRAY", ops, 42, r) for r in range(30)]
        self.assertEqual(len({report["findings"][2]["result"] for report in reports}), 1)

    def test_unknown_truth_is_not_silently_negative(self):
        with self.assertRaises(ValueError):
            potential_report("S1", {**TRUTH, "delamination": None}, "XRAY", OPS, 42, 0)
        with self.assertRaises(ValueError):
            evaluate_state(InvestigationState(), {})


class ReplayAndCostTests(unittest.TestCase):
    def test_exact_documented_costs_and_resource_components(self):
        expected = {"XRAY": 120, "ACOUSTIC": 200, "ELECTRICAL": 600, "IR": 150, "SEM": 1800}
        for name, value in expected.items():
            self.assertEqual(procedure_cost(name, OPS), value)
            r = procedure_resources(name, OPS)
            self.assertEqual(r["spent_cost"], r["labor_cost"] + r["equipment_cost"] + r["consumables_cost"])
        sem = procedure_resources("SEM", OPS)
        self.assertEqual(sem["technician_hours"], 6)
        self.assertEqual(sem["engineer_hours"], 3)
        self.assertEqual(sem["nominal_hours"], 48)

    def test_scripted_walkthrough_costs_and_coexisting_faults(self):
        examples = walkthroughs(OPS)
        self.assertEqual(examples["A"]["summary"]["spent_cost"], 120)
        self.assertTrue(examples["A"]["summary"]["complete"])
        self.assertEqual(examples["B"]["summary"]["spent_cost"], 920)
        self.assertEqual(examples["B"]["summary"]["pending_cost"], 1800)
        self.assertEqual(examples["B"]["summary"]["pending_procedures"], ["SEM"])
        self.assertFalse(examples["B"]["summary"]["complete"])
        c = examples["C"]["summary"]
        self.assertEqual(c["spent_cost"], 2720)
        self.assertTrue(c["correctly_complete"])
        self.assertEqual(c["missed_coexisting_faults"], 0)
        self.assertEqual(c["final_states"]["delamination"], "confirmed_present")
        self.assertEqual(c["final_states"]["tsv_open_short"], "confirmed_present")
        self.assertEqual(c["final_states"]["microbump_open_bridge"], "confirmed_present")
        self.assertEqual(examples["D_cost"]["two_CT_attempts"], 240)

    def test_inconclusive_sem_costs_same_but_leaves_work_unresolved(self):
        result = walkthroughs(OPS)["C_inconclusive"]["summary"]
        self.assertEqual(result["spent_cost"], 2720)
        self.assertFalse(result["complete"])
        self.assertEqual(result["unresolved_count"], 1)
        self.assertTrue(result["review_pending"])
        self.assertIsNone(result["manual_review_cost"])

    def test_ct_inconclusive_repeats_then_escalates_without_all_seven_work(self):
        reports = {p: scripted_report(OPS, p) for p in PROCEDURE_ORDER}
        reports["XRAY"] = scripted_report(OPS, "XRAY", inconclusive=True)
        result, events = replay_case(base_case(), TRUTH, PROBS, "mock", OPS, 42, 0, False, scripted_reports=reports)
        self.assertEqual(result["attempted_procedures"], ["XRAY", "ACOUSTIC", "SEM"])
        self.assertNotIn("ELECTRICAL", result["attempted_procedures"])
        self.assertFalse(result["complete"])

    def test_electrical_inconclusive_runs_ir_but_cannot_claim_absence(self):
        reports = {p: scripted_report(OPS, p) for p in PROCEDURE_ORDER}
        reports["ELECTRICAL"] = scripted_report(OPS, "ELECTRICAL", inconclusive=True)
        case = {**base_case(), "stack_assembly_pass": 1, "electrical_test_pass": 0}
        result, events = replay_case(case, TRUTH, PROBS, "mock", OPS, 42, 0, False, scripted_reports=reports)
        self.assertEqual(result["attempted_procedures"][:2], ["ELECTRICAL", "ELECTRICAL"])
        self.assertIn("IR", result["attempted_procedures"])
        self.assertNotIn("SEM", result["attempted_procedures"])
        self.assertEqual(result["final_states"]["dram_electrical"], "inconclusive")

    def test_evidence_complete_can_still_be_wrong(self):
        reports = {p: scripted_report(OPS, p) for p in PROCEDURE_ORDER}
        reports["ACOUSTIC"] = scripted_report(OPS, "ACOUSTIC", ("delamination",))
        result, _ = replay_case(base_case(), TRUTH, PROBS, "mock", OPS, 42, 0, False, scripted_reports=reports)
        self.assertTrue(result["complete"])
        self.assertFalse(result["correctly_complete"])
        self.assertEqual(result["false_positives"], 1)
        self.assertEqual(result["incorrectly_complete"], 1)

    def test_audit_all_five_and_inconclusive_audit_not_complete(self):
        reports = {p: scripted_report(OPS, p) for p in PROCEDURE_ORDER}
        result, _ = replay_case(base_case(), TRUTH, PROBS, "mock", OPS, 42, 0, True, scripted_reports=reports)
        self.assertEqual(set(result["attempted_procedures"]), set(PROCEDURE_ORDER))
        self.assertEqual(result["spent_cost"], 2870)
        self.assertTrue(result["audit_complete"])
        reports["IR"] = scripted_report(OPS, "IR", inconclusive=True)
        result, _ = replay_case(base_case(), TRUTH, PROBS, "mock", OPS, 42, 0, True, scripted_reports=reports)
        self.assertEqual(result["unresolved_count"], 2)
        self.assertNotIn("SEM", result["attempted_procedures"])
        self.assertFalse(result["audit_complete"])
        self.assertFalse(result["complete"])

    def test_audit_fixed_order_is_independent_of_policy_and_probabilities(self):
        reports = {p: scripted_report(OPS, p) for p in PROCEDURE_ORDER}
        case = {**base_case(), "electrical_test_pass": 0, "delamination_area_pct": 0.4}
        probabilities = {**PROBS, "delamination": 1, "warpage": 0, "underfill_void": 0}
        for policy in ("mock", "ct_first", "heuristic"):
            result, _ = replay_case(case, TRUTH, probabilities, policy, OPS, 42, 0, True, scripted_reports=reports)
            self.assertEqual(result["attempted_procedures"], list(PROCEDURE_ORDER))

    def test_package_first_can_retire_generic_electrical_branch(self):
        reports = {p: scripted_report(OPS, p) for p in PROCEDURE_ORDER}
        reports["XRAY"] = scripted_report(OPS, "XRAY", ("warpage",))
        case = {**base_case(), "package_warpage_um": 17, "electrical_test_pass": 0}
        result, _ = replay_case(case, {**TRUTH, "warpage": 1}, PROBS, "mock", OPS, 42, 0, False, scripted_reports=reports)
        self.assertEqual(result["attempted_procedures"], ["XRAY"])
        self.assertEqual(result["spent_cost"], 120)
        self.assertIn("R05_package_explanation", result["retired_rules"])

    def test_ct_positive_can_close_unexplained_assembly_branch(self):
        reports = {p: scripted_report(OPS, p) for p in PROCEDURE_ORDER}
        reports["XRAY"] = scripted_report(OPS, "XRAY", ("delamination",))
        result, _ = replay_case(base_case(), {**TRUTH, "delamination": 1}, PROBS, "mock", OPS, 42, 0, False, scripted_reports=reports)
        self.assertEqual(result["spent_cost"], 120)
        self.assertNotIn("ACOUSTIC", result["attempted_procedures"])
        self.assertTrue(result["complete"])


if __name__ == "__main__":
    unittest.main()
