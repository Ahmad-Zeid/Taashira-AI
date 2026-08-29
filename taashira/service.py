"""Campaign service: plan, diff, persist, emit.

The one place that decides whether anything actually happened. Both the API and the
background worker go through here, so the rule "only raise an event when the plan
really changed" is enforced once rather than in every caller.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import date

from taashira.domain.campaign import Campaign, Event, EventKind
from taashira.domain.documents import Applicant
from taashira.domain.requirements import RequirementPack
from taashira.domain.temporal import Interval
from taashira.planner import PlanDiff, diff_plans, plan_campaign
from taashira.store.base import CampaignStore


def _idempotency_key(campaign_id: str, version: int, kind: str, detail: str = "") -> str:
    """Deterministic key for (campaign, version, event).

    Replaying the same tick produces the same key, so a redelivered message is
    recognised as a duplicate rather than acted on twice.
    """
    digest = hashlib.sha256(f"{campaign_id}|{version}|{kind}|{detail}".encode()).hexdigest()
    return f"{kind}-{digest[:24]}"


@dataclass
class ReplanResult:
    campaign: Campaign
    diff: PlanDiff
    changed: bool
    events: list[Event] = field(default_factory=list)

    def summary(self) -> str:
        if not self.changed:
            return f"{self.campaign.campaign_id}: no change"
        return f"{self.campaign.campaign_id} v{self.campaign.version}: {self.diff.summary()}"


def replan(
    *,
    store: CampaignStore,
    pack: RequirementPack,
    applicant: Applicant,
    program: Interval,
    today: date,
    campaign_id: str | None = None,
    target_date: date | None = None,
) -> ReplanResult:
    """Re-plan a campaign, persisting and announcing it only if something changed.

    A new version is written on every real change, never on a no-op tick. Silence is
    the correct output for most days; the value of the alert depends on it.
    """
    previous = store.get_campaign(campaign_id) if campaign_id else None
    identifier = campaign_id or f"cmp_{uuid.uuid4().hex[:12]}"
    next_version = (previous.version + 1) if previous else 1

    candidate = plan_campaign(
        pack=pack,
        applicant=applicant,
        program=program,
        today=today,
        target_date=target_date,
        campaign_id=identifier,
        version=next_version,
    )

    diff = diff_plans(previous, candidate)
    if previous is not None and diff.is_empty:
        return ReplanResult(campaign=previous, diff=diff, changed=False)

    store.save_campaign(candidate)
    events = _emit(store, candidate, diff)
    return ReplanResult(campaign=candidate, diff=diff, changed=True, events=events)


def _emit(store: CampaignStore, campaign: Campaign, diff: PlanDiff) -> list[Event]:
    """Announce what changed. Deduplicated by the store on idempotency key."""
    emitted: list[Event] = []

    def publish(kind: EventKind, detail: str, payload: dict) -> None:
        event = Event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            campaign_id=campaign.campaign_id,
            kind=kind,
            idempotency_key=_idempotency_key(
                campaign.campaign_id, campaign.version, kind.value, detail
            ),
            payload=payload,
        )
        if store.append_event(event):
            emitted.append(event)

    publish(
        EventKind.PLAN_CHANGED,
        diff.summary(),
        {
            "version": campaign.version,
            "summary": diff.summary(),
            "added": diff.added,
            "removed": diff.removed,
            "critical_path": campaign.critical_path,
        },
    )

    for node in campaign.at_risk_nodes:
        publish(
            EventKind.NODE_AT_RISK,
            node.requirement_id,
            {
                "requirement_id": node.requirement_id,
                "slack_days": node.slack_days,
                "latest_finish": str(node.latest_finish),
            },
        )

    if not campaign.feasible:
        publish(
            EventKind.CAMPAIGN_INFEASIBLE,
            campaign.binding_constraint or "",
            {"binding_constraint": campaign.binding_constraint},
        )

    return emitted
