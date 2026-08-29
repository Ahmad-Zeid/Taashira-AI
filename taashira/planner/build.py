"""Building a campaign: graph construction, remediation splicing, scheduling.

Planning is a fixpoint loop, not a single sweep. Constraints anchor to node dates,
node dates come from the schedule, the schedule depends on which nodes exist, and
which nodes exist depends on which constraints failed. So: schedule, evaluate, splice
whatever the failures demand, and go round again until nothing new is spliced.

That loop is the mechanism the product exists for. A travel document that does not
cover the programme splices a renewal; the renewal declares its own inputs; one of
those inputs carries a max-age rule that may splice another node in turn. Three
levels deep, entirely from data.
"""

from __future__ import annotations

import uuid
from datetime import date

from taashira.domain.campaign import (
    Campaign,
    CampaignNode,
    ConstraintViolation,
    NodeState,
    Severity,
)
from taashira.domain.constraints import NotAfter, NotBefore
from taashira.domain.documents import Applicant, DocumentKind
from taashira.domain.requirements import RequirementPack
from taashira.domain.temporal import Interval
from taashira.planner.context import PlanContext, UnresolvedTimeRef
from taashira.planner.evaluate import Outcome, evaluate
from taashira.planner.schedule import ScheduledNode, critical_path, schedule

MAX_PASSES = 8
"""Bound on the fixpoint loop. A pack whose remediations cycle would otherwise spin."""


class PlanningDidNotConverge(Exception):
    """Splicing was still adding nodes when the pass budget ran out."""


def _held_kinds(applicant: Applicant) -> set[DocumentKind]:
    return {d.kind for d in applicant.documents}


def _base_graph(pack: RequirementPack, applicant: Applicant) -> set[str]:
    held = _held_kinds(applicant)
    return {
        r.id
        for r in pack.requirements
        if not r.remediation_only
        and (r.applies_when is None or r.applies_when.matches(applicant.nationality_status, held))
    }


def _pull_in(
    requirement_id: str,
    pack: RequirementPack,
    applicant: Applicant,
    active: set[str],
    depth: dict[str, int],
    at_depth: int,
) -> None:
    """Add a requirement and everything it declares as an input, transitively."""
    held = _held_kinds(applicant)
    pending = [requirement_id]
    while pending:
        rid = pending.pop()
        if rid in active:
            continue
        req = pack.by_id(rid)
        if req.applies_when and not req.applies_when.matches(applicant.nationality_status, held):
            continue
        active.add(rid)
        depth[rid] = min(depth.get(rid, at_depth), at_depth)
        pending.extend(req.depends_on)


def _dependency_map(
    pack: RequirementPack, active: set[str], extra: dict[str, set[str]]
) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for rid in active:
        declared = [d for d in pack.by_id(rid).depends_on if d in active]
        spliced = [d for d in sorted(extra.get(rid, set())) if d in active]
        deps[rid] = sorted(set(declared + spliced))
    return deps


def _schedule_bounds(
    pack: RequirementPack, active: set[str], ctx: PlanContext
) -> tuple[dict[str, date], dict[str, date]]:
    """NotBefore / NotAfter constraints, resolved into concrete scheduler bounds."""
    floors: dict[str, date] = {}
    ceilings: dict[str, date] = {}
    for rid in active:
        for constraint in pack.by_id(rid).constraints:
            if not isinstance(constraint, NotBefore | NotAfter):
                continue
            try:
                when = ctx.resolve(constraint.at)
            except UnresolvedTimeRef:
                continue
            if isinstance(constraint, NotBefore):
                floors[rid] = max(floors.get(rid, when), when)
            else:
                ceilings[rid] = min(ceilings.get(rid, when), when)
    return floors, ceilings


def _satisfied(
    pack: RequirementPack, active: set[str], applicant: Applicant, spliced: set[str]
) -> set[str]:
    """Nodes whose output the applicant already holds.

    A spliced node is never satisfied by the document that triggered it — the renewal
    exists precisely because the travel document on file is inadequate, so the fact
    that a travel document exists must not mark the renewal done.
    """
    held = _held_kinds(applicant)
    return {
        rid
        for rid in active
        if rid not in spliced
        and (produces := pack.by_id(rid).produces) is not None
        and produces in held
    }


def _evaluate_pass(
    pack: RequirementPack, active: set[str], ctx: PlanContext
) -> tuple[list[ConstraintViolation], dict[str, str]]:
    """Evaluate every constraint on every active node.

    Returns the violations found and a mapping of remediation id → the node that
    demanded it.
    """
    violations: list[ConstraintViolation] = []
    demanded: dict[str, str] = {}

    for rid in sorted(active):
        req = pack.by_id(rid)
        for constraint in req.constraints:
            if isinstance(constraint, NotBefore | NotAfter):
                continue
            result = evaluate(constraint, ctx)
            if result.outcome is Outcome.PASS:
                continue

            severity = Severity.BLOCKING if result.failed else Severity.WARNING
            remediation = constraint.remediation if result.failed else None
            if remediation:
                demanded.setdefault(remediation, rid)

            violations.append(
                ConstraintViolation(
                    requirement_id=rid,
                    constraint_kind=constraint.kind,
                    description=constraint.note or constraint.describe(),
                    severity=severity,
                    authority=req.authority,
                    remediation_applied=remediation,
                    detail=result.detail,
                )
            )
    return violations, demanded


def _node_state(
    rid: str,
    scheduled: ScheduledNode,
    deps: list[str],
    satisfied: set[str],
    violations: list[ConstraintViolation],
) -> NodeState:
    mine = [v for v in violations if v.requirement_id == rid]
    if any(v.severity is Severity.WARNING for v in mine):
        return NodeState.NEEDS_HUMAN_REVIEW
    if any(v.severity is Severity.BLOCKING for v in mine):
        # Holding the document is not the same as the document being adequate. A stale
        # civil extract or a too-short travel document must never read as satisfied.
        return NodeState.AT_RISK if scheduled.is_late else NodeState.BLOCKED
    if rid in satisfied:
        return NodeState.SATISFIED
    if scheduled.is_late:
        return NodeState.AT_RISK
    if all(d in satisfied for d in deps):
        return NodeState.READY
    return NodeState.BLOCKED


def plan_campaign(
    *,
    pack: RequirementPack,
    applicant: Applicant,
    program: Interval,
    today: date,
    target_date: date | None = None,
    campaign_id: str | None = None,
    version: int = 1,
) -> Campaign:
    """Build a scheduled, constraint-checked campaign.

    `target_date` defaults to the first day of the programme — the immovable date the
    entire graph is scheduled backwards from.
    """
    target = target_date or program.start
    active = _base_graph(pack, applicant)
    extra_deps: dict[str, set[str]] = {}
    spliced_by: dict[str, str] = {}
    depth: dict[str, int] = dict.fromkeys(active, 0)

    scheduled: dict[str, ScheduledNode] = {}
    violations: list[ConstraintViolation] = []
    converged = False

    for _ in range(MAX_PASSES):
        deps = _dependency_map(pack, active, extra_deps)
        satisfied = _satisfied(pack, active, applicant, set(spliced_by))
        lead_days = {rid: pack.by_id(rid).lead_time_p90_days for rid in active}

        ctx = PlanContext(today=today, target_date=target, program=program, applicant=applicant)
        floors, ceilings = _schedule_bounds(pack, active, ctx)

        scheduled = schedule(
            active=active,
            deps=deps,
            lead_days=lead_days,
            satisfied=satisfied,
            today=today,
            target_date=target,
            not_before=floors,
            not_after=ceilings,
        )

        ctx = ctx.with_finishes({rid: s.earliest_finish for rid, s in scheduled.items()})
        violations, demanded = _evaluate_pass(pack, active, ctx)

        new = {r: by for r, by in demanded.items() if r not in active}
        if not new:
            converged = True
            break

        for remediation_id, demanded_by in new.items():
            _pull_in(
                remediation_id,
                pack,
                applicant,
                active,
                depth,
                at_depth=depth.get(demanded_by, 0) + 1,
            )
            if remediation_id in active:
                spliced_by[remediation_id] = demanded_by
                # The node that failed now waits on its own remedy.
                extra_deps.setdefault(demanded_by, set()).add(remediation_id)

    if not converged:
        raise PlanningDidNotConverge(
            f"still splicing after {MAX_PASSES} passes; check the pack for a remediation cycle"
        )

    deps = _dependency_map(pack, active, extra_deps)
    satisfied = _satisfied(pack, active, applicant, set(spliced_by))

    # Holding a document is not the same as that document being adequate. A node with a
    # blocking violation is not done, whatever is on file, and nothing downstream may
    # treat it as a met dependency.
    inadequate = {v.requirement_id for v in violations if v.severity is Severity.BLOCKING}
    settled = satisfied - inadequate

    path = critical_path(scheduled, deps, ignore=settled)

    nodes = [
        CampaignNode(
            requirement_id=rid,
            state=_node_state(rid, scheduled[rid], deps[rid], settled, violations),
            earliest_finish=scheduled[rid].earliest_finish,
            latest_finish=scheduled[rid].latest_finish,
            slack_days=scheduled[rid].slack_days,
            on_critical_path=rid in path,
            spliced_by=spliced_by.get(rid),
            depth=depth.get(rid, 0),
            violations=[v for v in violations if v.requirement_id == rid],
        )
        for rid in sorted(active)
    ]

    # Feasibility is judged on outstanding work only. Completed nodes carry stale
    # arithmetic — the backward pass happily reports that something already done was
    # "needed three weeks ago", which is true and useless.
    outstanding = [s for rid, s in scheduled.items() if rid not in settled]
    min_slack = min((s.slack_days for s in outstanding), default=0)
    blocking = [v for v in violations if v.severity is Severity.BLOCKING]
    unremedied = [v for v in blocking if v.remediation_applied is None]
    feasible = min_slack >= 0 and not unremedied

    binding: str | None = None
    if not feasible:
        if unremedied:
            first = unremedied[0]
            binding = f"{first.requirement_id}: {first.detail or first.description}"
        else:
            # Ties broken by id so the same inputs always name the same node — a
            # plan that reports a different bottleneck on each run is not trustworthy.
            tightest = min(outstanding, key=lambda s: (s.slack_days, s.requirement_id))
            binding = (
                f"{tightest.requirement_id} is {abs(tightest.slack_days)} days late: "
                f"cannot finish before {tightest.earliest_finish} "
                f"but is needed by {tightest.latest_finish}"
            )

    return Campaign(
        campaign_id=campaign_id or f"cmp_{uuid.uuid4().hex[:12]}",
        applicant_id=applicant.applicant_id,
        pack_id=pack.pack_id,
        pack_version=pack.version,
        corridor_id=pack.corridor.id,
        target_date=target,
        program=program,
        nodes=nodes,
        critical_path=path,
        violations=violations,
        feasible=feasible,
        binding_constraint=binding,
        version=version,
    )
