"""Wait-time signal tests.

A wrong wait time silently moves every downstream date in a months-long plan, so the
rules that matter here are: never invent a number, and always be able to say where the
number came from.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from taashira.fixtures import MASTERS_PROGRAM, REFERENCE_TODAY, stateless_masters_applicant
from taashira.packs import load_pack_by_id
from taashira.planner import plan_campaign
from taashira.signals import observed_lead_days
from taashira.signals.wait_times import SnapshotSource, WaitTimeObservation


@pytest.fixture
def pack():
    return load_pack_by_id("lb-prtd__us-f1")


def test_snapshot_reading_carries_its_own_date_and_source():
    reading = SnapshotSource().fetch("Beirut", "student")
    assert reading is not None
    assert reading.days > 0
    assert reading.observed_on <= date.today()
    assert "travel.state.gov" in reading.source


def test_unknown_post_returns_nothing_rather_than_a_guess():
    assert SnapshotSource().fetch("Atlantis", "student") is None


def test_snapshot_file_is_missing_gracefully(tmp_path):
    assert SnapshotSource(tmp_path / "absent.json").fetch("Beirut") is None


def test_only_signal_bearing_requirements_get_overrides(pack):
    overrides = observed_lead_days(pack, allow_live=False)
    declared = {r.id for r in pack.requirements if r.wait_time_signal}
    assert set(overrides) <= declared
    assert "interview_appointment" in overrides


def test_a_longer_queue_makes_the_plan_worse(pack):
    """The whole point: an outside number moves the schedule."""
    applicant = stateless_masters_applicant()
    common = {
        "pack": pack,
        "applicant": applicant,
        "program": MASTERS_PROGRAM,
        "today": REFERENCE_TODAY,
    }
    quick = plan_campaign(**common, observed_lead_days={"interview_appointment": 14})
    slow = plan_campaign(**common, observed_lead_days={"interview_appointment": 180})

    quick_node = quick.node("interview_appointment")
    slow_node = slow.node("interview_appointment")
    assert quick_node is not None and slow_node is not None
    assert slow_node.slack_days < quick_node.slack_days


def test_observation_supersedes_the_pack_estimate(pack):
    """A measurement beats a guess made once."""
    estimate = pack.by_id("interview_appointment").lead_time_p90_days
    applicant = stateless_masters_applicant()
    common = {
        "pack": pack,
        "applicant": applicant,
        "program": MASTERS_PROGRAM,
        "today": REFERENCE_TODAY,
    }
    baseline = plan_campaign(**common)
    observed = plan_campaign(**common, observed_lead_days={"interview_appointment": estimate + 60})

    a = baseline.node("interview_appointment")
    b = observed.node("interview_appointment")
    assert a is not None and b is not None
    assert b.earliest_finish > a.earliest_finish


def test_observation_roundtrips_through_json():
    original = WaitTimeObservation(
        post="Beirut", visa_class="student", days=21, observed_on=date(2026, 8, 29), source="test"
    )
    assert WaitTimeObservation.from_dict(json.loads(json.dumps(original.to_dict()))) == original
