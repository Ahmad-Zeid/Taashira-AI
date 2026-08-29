"""Agent-layer tests.

No model is called here. What is tested is the machinery around the model: the grounding
filters that discard invented rules, and the confidence handling that decides whether an
extraction is trusted. Those are the parts that must hold when the model misbehaves.
"""

from __future__ import annotations

from datetime import date

import pytest

from taashira.agents.coach import ground_actions
from taashira.agents.critic import ground_findings
from taashira.agents.extract import CONFIDENCE_FLOOR, needs_review, to_identity_document
from taashira.agents.schemas import (
    CoachPlan,
    ExtractedDocument,
    NextAction,
    RefusalFinding,
    RefusalFindings,
    Verdict,
)
from taashira.domain.documents import DocumentKind, VerificationSource
from taashira.packs import load_pack_by_id


@pytest.fixture
def pack():
    return load_pack_by_id("lb-prtd__us-f1")


@pytest.fixture
def real_authority(pack):
    return pack.by_id("visa_interview").authority


def _finding(authority: str) -> RefusalFinding:
    return RefusalFinding(
        requirement_id="visa_interview",
        authority=authority,
        ground="g",
        evidence_gap="gap",
        remedy="fix",
    )


# ------------------------------------------------------------- grounding


def test_critic_findings_citing_the_pack_are_kept(pack, real_authority):
    result = ground_findings(
        RefusalFindings(verdict=Verdict.REFUSE, findings=[_finding(real_authority)], summary="s"),
        pack,
    )
    assert len(result.findings) == 1
    assert result.dropped == []
    assert result.grounding_rate == 1.0


def test_critic_findings_citing_an_invented_rule_are_dropped(pack):
    """The concrete anti-hallucination mechanism, and it must be measurable."""
    result = ground_findings(
        RefusalFindings(
            verdict=Verdict.REFUSE,
            findings=[_finding("INA 999(z): the applicant seems untrustworthy")],
            summary="s",
        ),
        pack,
    )
    assert result.findings == []
    assert len(result.dropped) == 1
    assert result.grounding_rate == 0.0


def test_grounding_rate_is_reported_not_hidden(pack, real_authority):
    result = ground_findings(
        RefusalFindings(
            verdict=Verdict.REFUSE,
            findings=[_finding(real_authority), _finding("Regulation 12 of Nowhere")],
            summary="s",
        ),
        pack,
    )
    assert result.grounding_rate == 0.5


def test_coach_actions_are_grounded_the_same_way(pack, real_authority):
    plan = CoachPlan(
        headline="h",
        actions=[
            NextAction(
                requirement_id="visa_interview", title="t", why="w", authority=real_authority
            ),
            NextAction(requirement_id="visa_interview", title="t2", why="w", authority="invented"),
        ],
    )
    result = ground_actions(plan, pack)
    assert [a.title for a in result.actions] == ["t"]
    assert [a.title for a in result.dropped] == ["t2"]


def test_no_findings_is_full_grounding_not_zero(pack):
    result = ground_findings(
        RefusalFindings(verdict=Verdict.APPROVE, findings=[], summary="clean"), pack
    )
    assert result.grounding_rate == 1.0


# ------------------------------------------------------------ extraction


def test_unreadable_field_forces_review_whatever_the_confidence():
    extracted = ExtractedDocument(
        kind=DocumentKind.TRAVEL_DOCUMENT, confidence=1.0, unreadable_fields=["expires_on"]
    )
    assert needs_review(extracted)


def test_low_confidence_forces_review():
    assert needs_review(
        ExtractedDocument(kind=DocumentKind.TRAVEL_DOCUMENT, confidence=CONFIDENCE_FLOOR - 0.01)
    )


def test_confident_and_complete_extraction_passes():
    assert not needs_review(
        ExtractedDocument(
            kind=DocumentKind.TRAVEL_DOCUMENT,
            confidence=0.98,
            issued_on=date(2026, 3, 1),
            expires_on=date(2027, 3, 1),
        )
    )


def test_extraction_is_never_promoted_to_confirmed():
    """Promotion to confirmed is a human act, never a model's own verdict."""
    document = to_identity_document(ExtractedDocument(kind=DocumentKind.PASSPORT, confidence=1.0))
    assert document.verified_by is VerificationSource.EXTRACTED
    assert document.is_provisional


def test_unreadable_fields_survive_onto_the_record():
    document = to_identity_document(
        ExtractedDocument(
            kind=DocumentKind.CIVIL_EXTRACT, confidence=0.5, unreadable_fields=["issued_on"]
        )
    )
    assert "issued_on" in document.attributes["unreadable"]
