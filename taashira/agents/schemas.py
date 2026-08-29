"""Structured outputs for the agent layer.

Every LLM agent declares one of these as its `output_schema`. Free-text answers are
not accepted anywhere: an agent either produces a value that validates against the
schema or its turn is a failure the orchestrator can see and retry.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from taashira.domain.documents import DocumentKind


class ExtractedDocument(BaseModel):
    """What the vision model believes it read off an uploaded document."""

    kind: DocumentKind
    issuer: str | None = Field(default=None, description="Authority that issued it.")
    issued_on: date | None = None
    expires_on: date | None = None
    reference_redacted: str | None = Field(
        default=None,
        description="Last four characters of any document number ONLY. Never the full number.",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="0 when a field could not be read.")
    unreadable_fields: list[str] = Field(
        default_factory=list,
        description="Fields visible but not legible. Drives routing to human review.",
    )
    notes: str | None = None


class Verdict(StrEnum):
    REFUSE = "refuse"
    APPROVE_WITH_RISK = "approve_with_risk"
    APPROVE = "approve"


class RefusalFinding(BaseModel):
    """One ground on which this application could be refused."""

    requirement_id: str = Field(description="Requirement in the pack this concerns.")
    authority: str = Field(
        description=(
            "Verbatim `authority` string of a requirement in the pack. A finding whose "
            "authority does not appear in the pack is discarded before it is shown."
        )
    )
    ground: str = Field(description="Why an officer could refuse, in one sentence.")
    evidence_gap: str = Field(description="What is missing or contradictory.")
    remedy: str = Field(description="The concrete thing that would close the gap.")


class RefusalFindings(BaseModel):
    verdict: Verdict
    findings: list[RefusalFinding] = Field(default_factory=list)
    summary: str = Field(description="Two sentences maximum.")


class GroundedFindings(BaseModel):
    """Critic output after the grounding filter has run.

    `dropped` is reported rather than hidden: how often the critic invents an authority
    is a property of the system worth measuring, not an embarrassment to bury.
    """

    verdict: Verdict
    findings: list[RefusalFinding]
    summary: str
    dropped: list[RefusalFinding] = Field(default_factory=list)

    @property
    def grounding_rate(self) -> float:
        total = len(self.findings) + len(self.dropped)
        return 1.0 if total == 0 else len(self.findings) / total


class CampaignSpec(BaseModel):
    """Structured result of the intake conversation.

    The chat exists to produce this and then get out of the way. Everything downstream
    consumes typed state, never the transcript.
    """

    pack_id: str = Field(description="Requirement pack id for the corridor, e.g. lb-prtd__us-f1.")
    program_start: date | None = Field(default=None, description="First day of the programme.")
    program_end: date | None = Field(default=None, description="Last day of the programme.")
    nationality_status: str | None = Field(
        default=None,
        description="One of: national, stateless, refugee_travel_document, contested.",
    )
    residence_country: str | None = Field(default=None, description="ISO-2 country code.")
    documents_held: list[DocumentKind] = Field(
        default_factory=list, description="Document kinds the applicant says they already hold."
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="What still has to be asked before a campaign can be planned.",
    )
    ready_to_plan: bool = Field(
        default=False,
        description="True only when pack_id and both programme dates are known.",
    )
    reply: str = Field(description="What to say to the applicant next. One short paragraph.")


class NextAction(BaseModel):
    """One thing the applicant should do next, traceable to a rule."""

    requirement_id: str
    title: str = Field(description="Imperative and concrete: 'Request a fresh civil extract'.")
    why: str = Field(description="What breaks if this slips, in one sentence.")
    authority: str = Field(
        description="Verbatim `authority` from the pack. Ungrounded items are dropped."
    )
    urgency_days: int | None = Field(
        default=None, description="Days of slack before this becomes the binding constraint."
    )


class CoachPlan(BaseModel):
    """The advisor's answer: what to do, in order."""

    headline: str = Field(description="One sentence on where the campaign stands.")
    actions: list[NextAction] = Field(default_factory=list)


class GroundedCoachPlan(BaseModel):
    """Coach output after the same grounding filter the critic passes through."""

    headline: str
    actions: list[NextAction]
    dropped: list[NextAction] = Field(default_factory=list)

    @property
    def grounding_rate(self) -> float:
        total = len(self.actions) + len(self.dropped)
        return 1.0 if total == 0 else len(self.actions) / total
