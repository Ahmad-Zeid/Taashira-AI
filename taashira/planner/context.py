"""Resolution context for symbolic time references.

Constraints anchor to points in time they cannot know yet — the finish date of another
node, for instance. The planner resolves those against this context on each pass, which
is why planning is a fixpoint loop rather than a single sweep.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from taashira.domain.documents import Applicant
from taashira.domain.temporal import Interval


class UnresolvedTimeRef(Exception):
    """A reference pointed at a node with no computed date yet."""


@dataclass(frozen=True)
class PlanContext:
    today: date
    target_date: date
    program: Interval
    applicant: Applicant
    node_finish: dict[str, date] = field(default_factory=dict)

    def resolve(self, ref: str) -> date:
        """Turn a symbolic reference into a concrete date.

        Raises `UnresolvedTimeRef` when the reference points at a node the current
        pass has not scheduled yet — the caller treats that as "unknown", not "failed".
        """
        if ref == "today":
            return self.today
        if ref == "campaign:target_date":
            return self.target_date
        if ref == "campaign:program_start":
            return self.program.start
        if ref == "campaign:program_end":
            return self.program.end
        if ref.startswith("node:"):
            node_id = ref.removeprefix("node:")
            if node_id not in self.node_finish:
                raise UnresolvedTimeRef(node_id)
            return self.node_finish[node_id]
        raise ValueError(f"unrecognised time reference: {ref!r}")

    def with_finishes(self, finishes: dict[str, date]) -> PlanContext:
        return PlanContext(
            today=self.today,
            target_date=self.target_date,
            program=self.program,
            applicant=self.applicant,
            node_finish=dict(finishes),
        )
