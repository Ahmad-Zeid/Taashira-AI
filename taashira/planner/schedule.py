"""Backward and forward scheduling over the requirement graph.

Deliberately ordinary critical-path scheduling, and deliberately not done by a model.
Date arithmetic is exactly the kind of thing an LLM does plausibly and wrongly, and a
wrong date here costs an academic year. The model decides *what is true about the
documents*; this decides *when things have to happen*.

p90 lead times drive the schedule, so plans are conservative by construction. p50 is
kept for display only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


class CyclicGraph(Exception):
    """The requirement graph contains a dependency cycle."""


@dataclass(frozen=True)
class ScheduledNode:
    requirement_id: str
    earliest_finish: date
    latest_finish: date
    slack_days: int

    @property
    def is_late(self) -> bool:
        return self.slack_days < 0


def topological_order(active: set[str], deps: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm, with the unresolved remainder reported as a cycle."""
    indegree = {n: 0 for n in active}
    successors: dict[str, list[str]] = {n: [] for n in active}
    for node in active:
        for dep in deps.get(node, []):
            if dep in active:
                indegree[node] += 1
                successors[dep].append(node)

    queue = sorted(n for n, d in indegree.items() if d == 0)
    order: list[str] = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for succ in successors[node]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)
        queue.sort()

    if len(order) != len(active):
        raise CyclicGraph(f"cycle among: {sorted(active - set(order))}")
    return order


def schedule(
    *,
    active: set[str],
    deps: dict[str, list[str]],
    lead_days: dict[str, int],
    satisfied: set[str],
    today: date,
    target_date: date,
    not_before: dict[str, date] | None = None,
    not_after: dict[str, date] | None = None,
) -> dict[str, ScheduledNode]:
    """Compute earliest finish, latest finish and slack for every active node."""
    not_before = not_before or {}
    not_after = not_after or {}

    order = topological_order(active, deps)
    successors: dict[str, list[str]] = {n: [] for n in active}
    for node in active:
        for dep in deps.get(node, []):
            if dep in active:
                successors[dep].append(node)

    def lead(node: str) -> int:
        # Work already done takes no time.
        return 0 if node in satisfied else lead_days.get(node, 0)

    # Forward: how soon can this realistically be finished?
    earliest_finish: dict[str, date] = {}
    for node in order:
        if node in satisfied:
            earliest_finish[node] = today
            continue
        upstream = [earliest_finish[d] for d in deps.get(node, []) if d in active]
        start = max([today, *upstream]) if upstream else today
        finish = start + timedelta(days=lead(node))
        if (floor := not_before.get(node)) is not None:
            finish = max(finish, floor)
        earliest_finish[node] = finish

    # Backward: how late can this finish without pushing the target date?
    latest_finish: dict[str, date] = {}
    for node in reversed(order):
        downstream = successors[node]
        if not downstream:
            latest = target_date
        else:
            latest = min(latest_finish[s] - timedelta(days=lead(s)) for s in downstream)
        if (ceiling := not_after.get(node)) is not None:
            latest = min(latest, ceiling)
        latest_finish[node] = latest

    return {
        node: ScheduledNode(
            requirement_id=node,
            earliest_finish=earliest_finish[node],
            latest_finish=latest_finish[node],
            slack_days=(latest_finish[node] - earliest_finish[node]).days,
        )
        for node in active
    }


def critical_path(
    scheduled: dict[str, ScheduledNode],
    deps: dict[str, list[str]],
    ignore: set[str] | None = None,
) -> list[str]:
    """The chain of tightest outstanding nodes, in dependency order.

    Everything at minimum slack is on it; ordering topologically makes it readable as
    a sequence rather than a set. `ignore` drops work that is already complete — a
    finished node cannot be on the critical path, however tight its arithmetic looks.
    """
    candidates = {k: v for k, v in scheduled.items() if k not in (ignore or set())}
    if not candidates:
        return []
    min_slack = min(n.slack_days for n in candidates.values())
    tightest = {n.requirement_id for n in candidates.values() if n.slack_days == min_slack}
    return [n for n in topological_order(set(scheduled), deps) if n in tightest]
