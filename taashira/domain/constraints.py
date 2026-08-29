"""Temporal constraints — the part of the model that is actually novel.

A checklist asks "do you have document X?". This asks *when* document X is valid,
how old it is at the moment it is used, and whether its validity window covers the
period it has to cover. Those are the questions that decide real applications, and
they are the questions a checklist cannot express.

Every constraint may declare a `remediation`: the id of a requirement to splice into
the graph when the constraint fails. That single field is the cascade mechanism —
a travel document that does not cover the programme inserts a renewal, the renewal
declares its own inputs, and one of those inputs carries a max-age rule that may
insert another node in turn.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from taashira.domain.documents import DocumentKind
from taashira.domain.temporal import TimeRef


class CoveredPeriod(StrEnum):
    """Named intervals a document may be required to span.

    Only the programme itself is modelled today. Destinations also grant grace periods
    either side of it — F-1 allows entry before the start date and a departure window
    after the end — but those vary by destination and belong in the pack, so they get
    their own member when they are actually encoded rather than a placeholder now.
    """

    PROGRAM = "program"  # first to last day of study


class _Base(BaseModel):
    remediation: str | None = Field(
        default=None,
        description="Requirement id to splice into the graph when this constraint fails.",
    )
    note: str | None = Field(
        default=None,
        description="Human-readable explanation, surfaced in the UI and to the critic.",
    )


class ValidAt(_Base):
    """The document must be valid on a given date."""

    kind: Literal["valid_at"] = "valid_at"
    document: DocumentKind
    at: TimeRef

    def describe(self) -> str:
        return f"{self.document} must be valid at {self.at}"


class Covers(_Base):
    """The document's validity must span an entire named period.

    The central rule: a visa is not issued beyond the validity of the travel document
    it is placed in, so a two-year programme needs a travel document that survives it.
    For a Lebanese travel document issued for one year, this fails by construction —
    which is exactly the case the product exists to handle.
    """

    kind: Literal["covers"] = "covers"
    document: DocumentKind
    period: CoveredPeriod = CoveredPeriod.PROGRAM

    def describe(self) -> str:
        return f"{self.document} validity must cover the whole {self.period}"


class MaxAgeAtUse(_Base):
    """The document must be no older than `max_age_days` when it is used.

    Lebanon's Individual Civil Extract must have been issued within the last three
    years to support a travel-document application. A document that was fine last year
    can therefore silently go stale and block the chain.
    """

    kind: Literal["max_age_at_use"] = "max_age_at_use"
    document: DocumentKind
    max_age_days: int = Field(gt=0)
    at: TimeRef

    def describe(self) -> str:
        years = self.max_age_days / 365.25
        return f"{self.document} must be less than {years:.1f} years old at {self.at}"


class MinSeasoning(_Base):
    """Funds must have been held for a minimum period before the application.

    Consular officers trace the origin of money. A lump sum deposited days before
    applying is a documented refusal trigger, so the balance has to have *aged*.
    """

    kind: Literal["min_seasoning"] = "min_seasoning"
    document: DocumentKind = DocumentKind.FINANCIAL_STATEMENT
    min_days: int = Field(gt=0)
    at: TimeRef

    def describe(self) -> str:
        return f"funds must be held at least {self.min_days} days before {self.at}"


class NotBefore(_Base):
    """This node cannot complete before a given date."""

    kind: Literal["not_before"] = "not_before"
    at: TimeRef

    def describe(self) -> str:
        return f"cannot complete before {self.at}"


class NotAfter(_Base):
    """This node must complete by a given date — an externally imposed deadline."""

    kind: Literal["not_after"] = "not_after"
    at: TimeRef

    def describe(self) -> str:
        return f"must complete by {self.at}"


TemporalConstraint = Annotated[
    ValidAt | Covers | MaxAgeAtUse | MinSeasoning | NotBefore | NotAfter,
    Field(discriminator="kind"),
]
