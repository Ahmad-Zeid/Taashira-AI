"""Constraint evaluation.

Three outcomes, not two. `UNKNOWN` is what happens when a document's dates were never
captured or a referenced node has no date yet, and it must never be silently treated as
a pass — it routes the node to human review instead. Quietly passing an unknown expiry
is precisely the failure that loses a visa.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from taashira.domain.constraints import (
    CoveredPeriod,
    Covers,
    MaxAgeAtUse,
    MinSeasoning,
    NotAfter,
    NotBefore,
    TemporalConstraint,
    ValidAt,
)
from taashira.domain.documents import Applicant, DocumentKind
from taashira.domain.temporal import Interval
from taashira.planner.context import PlanContext, UnresolvedTimeRef


class Outcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Evaluation:
    outcome: Outcome
    detail: str

    @property
    def failed(self) -> bool:
        return self.outcome is Outcome.FAIL


def _missing(applicant: Applicant, kind: DocumentKind) -> Evaluation | None:
    """A document the applicant does not hold yet is unknown, not failed.

    It is presumably the output of some node still to run; failing it here would
    report the whole campaign infeasible on day one.
    """
    if not applicant.holds(kind):
        return Evaluation(Outcome.UNKNOWN, f"no {kind} on file yet")
    return None


def _period_interval(period: CoveredPeriod, ctx: PlanContext) -> Interval:
    """Resolve a named period against the campaign.

    One member today; grace periods will arrive here when a pack encodes them.
    """
    if period is CoveredPeriod.PROGRAM:
        return ctx.program
    raise ValueError(f"unhandled covered period: {period!r}")


def evaluate(constraint: TemporalConstraint, ctx: PlanContext) -> Evaluation:
    applicant = ctx.applicant

    match constraint:
        case ValidAt():
            if (missing := _missing(applicant, constraint.document)) is not None:
                return missing
            try:
                when = ctx.resolve(constraint.at)
            except UnresolvedTimeRef as exc:
                return Evaluation(Outcome.UNKNOWN, f"{constraint.at} not scheduled yet ({exc})")
            doc = applicant.best_document(constraint.document)
            assert doc is not None
            valid = doc.is_valid_at(when)
            if valid is None:
                return Evaluation(Outcome.UNKNOWN, f"{constraint.document} has no recorded expiry")
            if valid:
                return Evaluation(Outcome.PASS, f"{constraint.document} valid on {when}")
            return Evaluation(
                Outcome.FAIL,
                f"{constraint.document} expires {doc.expires_on}, before {when}",
            )

        case Covers():
            if (missing := _missing(applicant, constraint.document)) is not None:
                return missing
            doc = applicant.best_document(constraint.document)
            assert doc is not None
            validity = doc.validity
            if validity is None:
                return Evaluation(
                    Outcome.UNKNOWN, f"{constraint.document} has incomplete validity dates"
                )
            period = _period_interval(constraint.period, ctx)
            if validity.covers(period):
                return Evaluation(
                    Outcome.PASS,
                    f"{constraint.document} valid to {validity.end}, covers {constraint.period}",
                )
            shortfall = (period.end - validity.end).days
            return Evaluation(
                Outcome.FAIL,
                (
                    f"{constraint.document} expires {validity.end}, "
                    f"{shortfall} days before the {constraint.period} ends {period.end}"
                ),
            )

        case MaxAgeAtUse():
            if (missing := _missing(applicant, constraint.document)) is not None:
                return missing
            try:
                when = ctx.resolve(constraint.at)
            except UnresolvedTimeRef as exc:
                return Evaluation(Outcome.UNKNOWN, f"{constraint.at} not scheduled yet ({exc})")
            doc = applicant.best_document(constraint.document)
            assert doc is not None
            age = doc.age_days_at(when)
            if age is None:
                return Evaluation(
                    Outcome.UNKNOWN, f"{constraint.document} has no recorded issue date"
                )
            if age <= constraint.max_age_days:
                return Evaluation(
                    Outcome.PASS, f"{constraint.document} is {age}d old at {when}, within limit"
                )
            return Evaluation(
                Outcome.FAIL,
                (
                    f"{constraint.document} would be {age}d old at {when}, "
                    f"over the {constraint.max_age_days}d limit"
                ),
            )

        case MinSeasoning():
            if (missing := _missing(applicant, constraint.document)) is not None:
                return missing
            try:
                when = ctx.resolve(constraint.at)
            except UnresolvedTimeRef as exc:
                return Evaluation(Outcome.UNKNOWN, f"{constraint.at} not scheduled yet ({exc})")
            doc = applicant.best_document(constraint.document)
            assert doc is not None
            held = doc.age_days_at(when)
            if held is None:
                return Evaluation(
                    Outcome.UNKNOWN, f"{constraint.document} has no recorded opening date"
                )
            if held >= constraint.min_days:
                return Evaluation(Outcome.PASS, f"funds seasoned {held}d by {when}")
            return Evaluation(
                Outcome.FAIL,
                (
                    f"funds would be seasoned only {held}d by {when}, "
                    f"short of {constraint.min_days}d"
                ),
            )

        case NotBefore() | NotAfter():
            # Bounds on the node's own schedule; applied by the scheduler, not here.
            return Evaluation(Outcome.PASS, "schedule bound applied during scheduling")

    raise ValueError(f"unhandled constraint: {constraint!r}")
