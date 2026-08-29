"""Date intervals and symbolic time references.

A visa campaign is scheduled against dates that are not all known up front: some are
fixed (the semester start), some are derived (when a node is planned to finish), and
some are relative (today). Constraints therefore refer to points in time *symbolically*
and are resolved against a concrete context at planning time.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from pydantic import BaseModel, StringConstraints, model_validator

# Symbolic references a constraint may anchor to. Resolved by the planner, never here.
#   today                    the day the plan is computed
#   campaign:target_date     the immovable date the whole campaign is scheduled backwards from
#   campaign:program_start   first day the applicant must be present
#   campaign:program_end     last day of the programme
#   node:<requirement_id>    the planned finish date of another node
TIME_REF_PATTERN = (
    r"^(today"
    r"|campaign:(target_date|program_start|program_end)"
    r"|node:[a-z0-9_]+)$"
)

TimeRef = Annotated[str, StringConstraints(pattern=TIME_REF_PATTERN)]


class Interval(BaseModel):
    """A closed date interval, both endpoints inclusive."""

    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> Interval:
        if self.end < self.start:
            raise ValueError(f"interval end {self.end} precedes start {self.start}")
        return self

    @property
    def days(self) -> int:
        """Length in days, counting both endpoints."""
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def covers(self, other: Interval) -> bool:
        """True when this interval fully contains `other`.

        This is the predicate behind the central rule of the whole product: a visa
        cannot be issued beyond the validity of the travel document it is stamped in,
        so the document's validity must *cover* the programme interval.
        """
        return self.start <= other.start and self.end >= other.end

    def shifted(self, days: int) -> Interval:
        delta = timedelta(days=days)
        return Interval(start=self.start + delta, end=self.end + delta)
