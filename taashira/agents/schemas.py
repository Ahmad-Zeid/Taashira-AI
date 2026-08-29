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
