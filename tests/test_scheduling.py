import json
from dataclasses import asdict
from pathlib import Path

import pytest

from helion_pipeline.scheduling import Booking, Scheduler, Task, fixture_schedules

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ops():
    return json.loads((ROOT / "synthetic-data-assumptions/operation-assumptions/synthetic_operating_assumptions.json").read_text())


def test_original_assignments_and_equal_cost(ops):
    fixtures = fixture_schedules(ops)
    assert fixtures["A"]["bookings"][0]["start"] == 1
    assert fixtures["A"]["bookings"][0]["end"] == 1.75
    sam, electrical = fixtures["B"]["bookings"]
    assert (sam["start"], sam["end"]) == (1, 2.5)
    assert (electrical["start"], electrical["end"]) == (4, 8)
    assert electrical["staff"][1]["start"] == 5.5
    assert fixtures["B"]["prior_spent_cost"] + fixtures["B"]["planned_resource_cost"] == 920
    assert fixtures["D_reference"]["planned_resource_cost"] == fixtures["D_earliest_deadline"]["planned_resource_cost"] == 240
    assert fixtures["D_reference"]["milestones_missed_if_conclusive"] == 1
    assert fixtures["D_earliest_deadline"]["milestones_missed_if_conclusive"] == 0


def test_free_machine_is_not_sufficient(ops):
    scheduler = Scheduler(ops)
    booking = scheduler.propose(Task("B", "ACOUSTIC"))
    assert booking.start == 1  # the machine is free at 0, both technicians are not
    assert booking.staff[0]["id"] == "TECH-01"


def test_commitment_preserved_after_inconclusive_result(ops):
    scheduler = Scheduler(ops)
    committed = scheduler.replan([Task("B", "XRAY", deadline=2), Task("A", "XRAY", deadline=3)])
    frozen = asdict(scheduler.bookings[1])
    # Even an explicitly reviewed new request could not steal A's confirmed slot.
    proposed = scheduler.propose(Task("review_request", "XRAY", ready=1.75), now=1.75)
    assert proposed.start >= 2.5
    assert asdict(scheduler.bookings[1]) == frozen
    assert len(scheduler.bookings) == 2  # merely proposing does not book a repeat


def test_horizon_and_staleness_block_promises(ops):
    assert Scheduler(ops).propose(Task("A", "SEM"))["reason"] == "future_calendar_required"
    assert Scheduler(ops).propose(Task("A", "XRAY", ready=24))["status"] == "blocked"
    assert Scheduler(ops, stale=True).propose(Task("A", "XRAY"))["reason"] == "stale_calendar"


def test_double_booking_or_forged_staff_rejected(ops):
    scheduler = Scheduler(ops)
    booking = scheduler.propose(Task("A", "XRAY"))
    other = scheduler.propose(Task("B", "XRAY"))
    scheduler.commit(booking)
    with pytest.raises(ValueError):
        scheduler.commit(other)
    proposal = scheduler.propose(Task("B", "ACOUSTIC"))
    proposal.staff[0]["id"] = "unqualified"
    with pytest.raises(ValueError):
        scheduler.commit(proposal)


def test_forged_geometry_rejected_and_confirmed_copy_is_independent(ops):
    scheduler = Scheduler(ops)
    proposal = scheduler.propose(Task("A", "XRAY"))
    proposal.end = 1.01
    with pytest.raises(ValueError):
        scheduler.commit(proposal)
    proposal = scheduler.propose(Task("A", "XRAY"))
    proposal.equipment = "ACOUSTIC"
    with pytest.raises(ValueError):
        scheduler.commit(proposal)
    proposal = scheduler.propose(Task("A", "XRAY"))
    returned = scheduler.commit(proposal)
    proposal.end = 100
    returned.staff[0]["id"] = "nobody"
    assert scheduler.bookings[0].end == 1.75
    assert scheduler.bookings[0].staff[0]["id"] == "TECH-01"
