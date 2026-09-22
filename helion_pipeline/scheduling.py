"""Deterministic finite-calendar scheduling of the existing paper fixtures.

This is not a simulator of quarterly arrivals or a production dispatcher.
Times are hours from SYN-OPS-001's origin; all fixture phases use 15-minute units.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math

from .common import write_json


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


@dataclass(frozen=True)
class Task:
    case_id: str
    procedure: str
    ready: float = 0.0
    deadline: float | None = None


@dataclass
class Booking:
    case_id: str
    procedure: str
    start: float
    end: float
    equipment: str
    staff: list[dict]
    deadline: float | None
    status: str = "proposed"


class Scheduler:
    """Reserve only supplied calendar intervals; never extrapolate them."""

    def __init__(self, ops: dict, *, stale: bool = False):
        self.ops = deepcopy(ops)
        self.stale = stale
        self.horizon = float(ops["availability_horizon_hours"])
        self.staff = {s["id"]: s for s in self.ops["roster_snapshot"]}
        self.equipment = {e["id"]: e for e in self.ops["equipment"]}
        self.procedures = {p["id"]: p for p in self.ops["procedures"]}
        self.bookings: list[Booking] = []

    def _free(self, task: Task, start: float):
        p = self.procedures[task.procedure]
        end = start + p["nominal_envelope_hours"]
        equipment = next(iter(p["equipment_hours"]))
        if start < task.ready or end > self.horizon:
            return None
        if any(overlaps((start, end), busy) for busy in self.equipment[equipment]["unavailable_intervals"]):
            return None
        for b in self.bookings:
            if (b.equipment == equipment or b.case_id == task.case_id) and overlaps((start, end), (b.start, b.end)):
                return None
        assignments = []
        for phase in p["staff_phases"]:
            interval = (start + phase["start_offset"], start + phase["start_offset"] + phase["hours"])
            chosen = None
            for staff_id, person in sorted(self.staff.items()):
                if person["role"] != phase["role"] or phase["skill"] not in person["skills"]:
                    continue
                if not any(s <= interval[0] and interval[1] <= e for s, e in person["on_shift"]):
                    continue
                busy = list(person["busy"])
                busy += [(a["start"], a["end"]) for b in self.bookings for a in b.staff if a["id"] == staff_id]
                busy += [(a["start"], a["end"]) for a in assignments if a["id"] == staff_id]
                if any(overlaps(interval, b) for b in busy):
                    continue
                chosen = {"id": staff_id, "role": phase["role"], "skill": phase["skill"], "start": interval[0], "end": interval[1]}
                break
            if chosen is None:
                return None
            assignments.append(chosen)
        return Booking(task.case_id, task.procedure, start, end, equipment, assignments, task.deadline)

    def propose(self, task: Task, *, now: float = 0.0):
        if self.stale:
            return {"status": "manual_review", "reason": "stale_calendar"}
        if task.procedure == "SEM":
            return {"status": "blocked", "reason": "future_calendar_required", "pending_procedure": "SEM"}
        if task.procedure not in self.procedures:
            return {"status": "blocked", "reason": "unknown_procedure"}
        start = math.ceil(max(now, task.ready) * 4 - 1e-9) / 4
        while start < self.horizon:
            result = self._free(task, start)
            if result is not None:
                return result
            start += 0.25
        return {"status": "blocked", "reason": "no_qualified_slot_within_calendar"}

    def commit(self, booking: Booking, *, now: float = 0.0):
        if self.stale or booking.start < now or booking.status != "proposed":
            raise ValueError("Cannot confirm a stale or past proposal")
        task = Task(booking.case_id, booking.procedure, booking.start, booking.deadline)
        checked = self._free(task, booking.start)
        if checked is None or asdict(checked) != asdict(booking):
            raise ValueError("Proposal conflicts with current resource commitments")
        confirmed = deepcopy(booking)
        confirmed.status = "confirmed"
        self.bookings.append(confirmed)
        return deepcopy(confirmed)

    def replan(self, tasks: list[Task], *, now=0.0, order="reference"):
        """Plan new requests only; committed bookings are never removed."""
        if order not in {"reference", "earliest_deadline"}:
            raise ValueError("Unknown dispatch order")
        indexed = list(enumerate(tasks))
        if order == "earliest_deadline":
            indexed.sort(key=lambda item: (math.inf if item[1].deadline is None else item[1].deadline, item[0]))
        results = []
        for _, task in indexed:
            result = self.propose(task, now=now)
            if isinstance(result, Booking):
                result = self.commit(result, now=now)
                results.append(asdict(result))
            else:
                results.append({"case_id": task.case_id, "procedure": task.procedure, **result})
        return results


def _cost(ops, procedure):
    p = next(p for p in ops["procedures"] if p["id"] == procedure)
    staff = {s["role"]: s["rate_per_hour"] for s in ops["staff_pools"]}
    equipment = {e["id"]: e["rate_per_hour"] for e in ops["equipment"]}
    return (p["technician_hours"] * staff["technician"] + p["engineer_hours"] * staff["quality_engineer"]
            + sum(h * equipment[e] for e, h in p["equipment_hours"].items()) + p["consumables"])


def fixture_schedules(ops: dict):
    results = {}
    a = Scheduler(ops)
    results["A"] = {"bookings": a.replan([Task("A", "XRAY")]), "planned_resource_cost": _cost(ops, "XRAY")}
    b = Scheduler(ops)
    sam = b.replan([Task("B", "ACOUSTIC")])[0]
    electrical = b.replan([Task("B", "ELECTRICAL", ready=sam["end"])])[0]
    results["B"] = {"bookings": [sam, electrical], "prior_spent_cost": 120,
                    "planned_resource_cost": _cost(ops, "ACOUSTIC") + _cost(ops, "ELECTRICAL"),
                    "SEM": b.propose(Task("B", "SEM", ready=electrical["end"]))}
    for order in ("reference", "earliest_deadline"):
        scheduler = Scheduler(ops)
        bookings = scheduler.replan([Task("A", "XRAY", deadline=3), Task("B", "XRAY", deadline=2)], order=order)
        scheduled = [x for x in bookings if "end" in x]
        results[f"D_{order}"] = {
            "bookings": bookings, "planned_resource_cost": len(scheduled) * _cost(ops, "XRAY"),
            "milestones_missed_if_conclusive": sum(b["end"] > b["deadline"] for b in scheduled),
            "unbooked": len(bookings) - len(scheduled),
            "milestone_basis": "scoped_evidence_if_conclusive_not_full_investigation_closure",
            "mean_wait_hours": sum(b["start"] for b in scheduled) / max(1, len(scheduled)),
            "latest_report_hours": max((b["end"] for b in scheduled), default=None),
        }
    results["C"] = {"status": "conditional_cost_trace_only", "resource_cost_if_qualified_conclusive_path": 2720,
                    "SEM_status": "future_calendar_required", "completion_time": None}
    return results


def run_scheduling(root: Path, out: Path, config: dict):
    ops = json.loads((root / config["operating_assumptions"]).read_text())
    result = {"origin": ops["origin"], "horizon_hours": 24,
              "basis": "existing_separate_paper_scenarios_not_observed_dispatch_or_cohort_turnaround",
              "base": fixture_schedules(ops), "outage_stress": {}}
    for duration in (2, 4):
        stressed = deepcopy(ops)
        ct = next(e for e in stressed["equipment"] if e["id"] == "CT")
        ct["unavailable_intervals"].append([1, 1 + duration])
        result["outage_stress"][f"CT_extra_{duration}h"] = {
            "assumption": f"Extend the existing CT reservation with {duration} hours of unavailability from hour 1; no calendar extension.",
            "scenarios": fixture_schedules(stressed),
        }
    result["exceptions"] = {
        "stale_calendar": Scheduler(ops, stale=True).propose(Task("A", "XRAY")),
        "beyond_horizon": Scheduler(ops).propose(Task("A", "XRAY", ready=24)),
        "inconclusive_result": "retain spent cost and unresolved evidence; no repeat is authorised; preserve other confirmed bookings",
    }
    write_json(out / "scheduling.json", result)
    return result
