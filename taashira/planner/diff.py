"""Comparing two versions of a plan.

The daily watcher re-plans every active campaign, but must only raise an event when
something *actually changed*. Without this the agent becomes a source of daily noise,
and the one moment that matters — the plan repairing itself — gets lost in it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from taashira.domain.campaign import Campaign


@dataclass(frozen=True)
class NodeChange:
    requirement_id: str
    field_name: str
    before: str | None
    after: str | None

    def describe(self) -> str:
        return f"{self.requirement_id}.{self.field_name}: {self.before} → {self.after}"


@dataclass
class PlanDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[NodeChange] = field(default_factory=list)
    feasibility_changed: bool = False
    critical_path_changed: bool = False

    @property
    def is_empty(self) -> bool:
        return not (
            self.added
            or self.removed
            or self.changed
            or self.feasibility_changed
            or self.critical_path_changed
        )

    def summary(self) -> str:
        if self.is_empty:
            return "no change"
        parts: list[str] = []
        if self.added:
            parts.append(f"{len(self.added)} node(s) added: {', '.join(self.added)}")
        if self.removed:
            parts.append(f"{len(self.removed)} node(s) removed: {', '.join(self.removed)}")
        if self.feasibility_changed:
            parts.append("feasibility changed")
        if self.critical_path_changed:
            parts.append("critical path changed")
        if self.changed:
            parts.append(f"{len(self.changed)} field change(s)")
        return "; ".join(parts)


# Fields worth waking someone up for. Deliberately excludes computed_at and version.
_TRACKED = ("state", "latest_finish", "slack_days", "on_critical_path")


def diff_plans(before: Campaign | None, after: Campaign) -> PlanDiff:
    if before is None:
        return PlanDiff(added=sorted(after.node_ids), feasibility_changed=True)

    before_ids = set(before.node_ids)
    after_ids = set(after.node_ids)

    changes: list[NodeChange] = []
    for rid in sorted(before_ids & after_ids):
        old, new = before.node(rid), after.node(rid)
        assert old is not None and new is not None
        for name in _TRACKED:
            old_value, new_value = getattr(old, name), getattr(new, name)
            if old_value != new_value:
                changes.append(
                    NodeChange(
                        requirement_id=rid,
                        field_name=name,
                        before=str(old_value),
                        after=str(new_value),
                    )
                )

    return PlanDiff(
        added=sorted(after_ids - before_ids),
        removed=sorted(before_ids - after_ids),
        changed=changes,
        feasibility_changed=before.feasible != after.feasible,
        critical_path_changed=before.critical_path != after.critical_path,
    )
