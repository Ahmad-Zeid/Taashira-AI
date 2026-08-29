"""Planner tests.

These are the real safety net. Every date in a visa campaign is load-bearing, and the
planner is the only place in the system where dates are decided — so it is the only
place where a silent bug costs an academic year.
"""

from __future__ import annotations

from datetime import date

import pytest

from taashira.domain.campaign import NodeState, Severity
from taashira.domain.documents import DocumentKind
from taashira.domain.temporal import Interval
from taashira.fixtures import (
    MASTERS_PROGRAM,
    REFERENCE_TODAY,
    stateless_masters_applicant,
    well_documented_applicant,
)
from taashira.packs import load_pack_by_id
from taashira.planner import (
    CyclicGraph,
    diff_plans,
    plan_campaign,
    schedule,
    topological_order,
)


@pytest.fixture
def pack():
    return load_pack_by_id("lb-prtd__us-f1")


def _plan(pack, applicant, **kwargs):
    return plan_campaign(
        pack=pack,
        applicant=applicant,
        program=kwargs.pop("program", MASTERS_PROGRAM),
        today=kwargs.pop("today", REFERENCE_TODAY),
        **kwargs,
    )


# --------------------------------------------------------------- the cascade


def test_short_travel_document_splices_a_renewal(pack):
    """A one-year document cannot cover a two-year programme, so a renewal appears."""
    campaign = _plan(pack, stateless_masters_applicant())

    renewal = campaign.node("renew_travel_document")
    assert renewal is not None, "renewal was not spliced into the graph"
    assert renewal.spliced_by == "visa_interview"
    assert renewal.depth == 1


def test_stale_civil_extract_cascades_a_second_level(pack):
    """The renewal's own input is stale, which splices a third level.

    This is the whole thesis in one assertion: the remediation for one broken
    constraint carries a constraint of its own, and that one breaks too.
    """
    campaign = _plan(pack, stateless_masters_applicant())

    reissue = campaign.node("reissue_civil_extract")
    assert reissue is not None, "second-level remediation was not spliced"
    assert reissue.spliced_by == "civil_extract_current"
    assert reissue.depth == 2
    assert {n.depth for n in campaign.spliced_nodes} == {1, 2}


def test_cascade_is_driven_by_constraints_not_hardcoded(pack):
    """The same pack produces no remediation at all for an ordinary passport."""
    campaign = _plan(pack, well_documented_applicant())

    assert campaign.spliced_nodes == []
    assert campaign.node("renew_travel_document") is None
    assert [v for v in campaign.violations if v.severity is Severity.BLOCKING] == []


def test_renewal_becomes_a_dependency_of_the_node_that_needed_it(pack):
    """Splicing must reorder the graph, not just append to it."""
    campaign = _plan(pack, stateless_masters_applicant())

    renewal = campaign.node("renew_travel_document")
    interview = campaign.node("visa_interview")
    assert renewal is not None and interview is not None
    assert renewal.earliest_finish is not None and interview.earliest_finish is not None
    assert renewal.earliest_finish <= interview.earliest_finish


# ------------------------------------------------------------ violations


def test_covers_violation_cites_an_authority_and_a_remediation(pack):
    campaign = _plan(pack, stateless_masters_applicant())

    covers = [v for v in campaign.violations if v.constraint_kind == "covers"]
    assert len(covers) == 1
    violation = covers[0]
    assert violation.requirement_id == "visa_interview"
    assert violation.remediation_applied == "renew_travel_document"
    assert violation.authority in pack.authorities
    assert "2028-12-20" in (violation.detail or "")


def test_max_age_violation_is_measured_at_the_node_that_uses_it(pack):
    campaign = _plan(pack, stateless_masters_applicant())

    stale = [v for v in campaign.violations if v.constraint_kind == "max_age_at_use"]
    assert len(stale) == 1
    assert stale[0].requirement_id == "civil_extract_current"
    assert stale[0].remediation_applied == "reissue_civil_extract"


def test_every_violation_cites_a_known_authority(pack):
    """The critic may only cite these ids, so they must all resolve."""
    campaign = _plan(pack, stateless_masters_applicant())

    assert campaign.violations
    for violation in campaign.violations:
        assert violation.authority in pack.authorities


def test_holding_an_inadequate_document_does_not_read_as_satisfied(pack):
    """A stale civil extract is on file, but the node is not done."""
    campaign = _plan(pack, stateless_masters_applicant())

    node = campaign.node("civil_extract_current")
    assert node is not None
    assert node.state is not NodeState.SATISFIED


# ------------------------------------------------------------- scheduling


def test_backward_pass_schedules_from_the_target_date():
    scheduled = schedule(
        active={"a", "b"},
        deps={"b": ["a"], "a": []},
        lead_days={"a": 10, "b": 5},
        satisfied=set(),
        today=date(2026, 1, 1),
        target_date=date(2026, 3, 1),
    )
    # b is terminal, so it may finish on the target date; a must finish 5 days earlier.
    assert scheduled["b"].latest_finish == date(2026, 3, 1)
    assert scheduled["a"].latest_finish == date(2026, 2, 24)


def test_forward_pass_accumulates_lead_times_along_the_chain():
    scheduled = schedule(
        active={"a", "b"},
        deps={"b": ["a"], "a": []},
        lead_days={"a": 10, "b": 5},
        satisfied=set(),
        today=date(2026, 1, 1),
        target_date=date(2026, 3, 1),
    )
    assert scheduled["a"].earliest_finish == date(2026, 1, 11)
    assert scheduled["b"].earliest_finish == date(2026, 1, 16)


def test_completed_work_consumes_no_lead_time():
    scheduled = schedule(
        active={"a", "b"},
        deps={"b": ["a"], "a": []},
        lead_days={"a": 10, "b": 5},
        satisfied={"a"},
        today=date(2026, 1, 1),
        target_date=date(2026, 3, 1),
    )
    assert scheduled["a"].earliest_finish == date(2026, 1, 1)
    assert scheduled["b"].earliest_finish == date(2026, 1, 6)


def test_negative_slack_marks_a_node_late():
    scheduled = schedule(
        active={"a"},
        deps={"a": []},
        lead_days={"a": 100},
        satisfied=set(),
        today=date(2026, 1, 1),
        target_date=date(2026, 2, 1),
    )
    assert scheduled["a"].is_late
    assert scheduled["a"].slack_days == -69


def test_dependency_cycles_are_rejected():
    with pytest.raises(CyclicGraph):
        topological_order({"a", "b"}, {"a": ["b"], "b": ["a"]})


# ------------------------------------------------------------ feasibility


def test_infeasible_plan_names_the_binding_node_not_a_platitude(pack):
    campaign = _plan(pack, stateless_masters_applicant())

    assert campaign.feasible is False
    assert campaign.binding_constraint is not None
    assert "days late" in campaign.binding_constraint
    # Must point at outstanding work, never at something already complete.
    named = campaign.binding_constraint.split(" ")[0]
    node = campaign.node(named)
    assert node is not None and node.state is not NodeState.SATISFIED


def test_a_distant_intake_is_feasible(pack):
    """Same applicant, more runway: the cascade remains, the infeasibility does not."""
    campaign = _plan(
        pack,
        stateless_masters_applicant(),
        program=Interval(start=date(2028, 1, 10), end=date(2029, 12, 20)),
    )
    assert campaign.feasible is True
    assert campaign.node("renew_travel_document") is not None


def test_completed_work_is_excluded_from_the_critical_path(pack):
    campaign = _plan(pack, stateless_masters_applicant())

    for requirement_id in campaign.critical_path:
        node = campaign.node(requirement_id)
        assert node is not None
        assert node.state is not NodeState.SATISFIED


# ------------------------------------------------------ unknown information


def test_missing_expiry_routes_to_human_review_rather_than_passing(pack):
    """An unknown expiry must never be treated as a pass."""
    applicant = stateless_masters_applicant()
    travel_doc = next(d for d in applicant.documents if d.kind == DocumentKind.TRAVEL_DOCUMENT)
    travel_doc.expires_on = None

    campaign = _plan(pack, applicant)
    interview = campaign.node("visa_interview")

    assert interview is not None
    assert interview.state is NodeState.NEEDS_HUMAN_REVIEW
    assert any(v.severity is Severity.WARNING for v in interview.violations)


# ------------------------------------------------------------- plan diffs


def test_first_plan_reports_every_node_as_added(pack):
    campaign = _plan(pack, stateless_masters_applicant())
    result = diff_plans(None, campaign)

    assert set(result.added) == set(campaign.node_ids)
    assert not result.is_empty


def test_identical_plans_produce_no_diff(pack):
    applicant = stateless_masters_applicant()
    first = _plan(pack, applicant)
    second = _plan(pack, applicant)

    assert diff_plans(first, second).is_empty


def test_renewing_the_document_removes_the_remediation_nodes(pack):
    """The plan heals when the underlying problem is fixed."""
    before = _plan(pack, stateless_masters_applicant())

    healed = stateless_masters_applicant()
    travel_doc = next(d for d in healed.documents if d.kind == DocumentKind.TRAVEL_DOCUMENT)
    travel_doc.expires_on = date(2030, 1, 1)
    extract = next(d for d in healed.documents if d.kind == DocumentKind.CIVIL_EXTRACT)
    extract.issued_on = date(2026, 8, 1)

    after = _plan(pack, healed, version=2)
    result = diff_plans(before, after)

    assert "renew_travel_document" in result.removed
    assert "reissue_civil_extract" in result.removed
    assert after.spliced_nodes == []
    assert not result.is_empty
