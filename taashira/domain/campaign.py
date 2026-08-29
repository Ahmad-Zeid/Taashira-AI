"""The campaign: a planned graph, its state, and the audit trail behind it.

Campaigns are versioned and immutable once written. That is deliberate — "the agent
re-planned itself when a constraint broke" has to be *provable* from stored history,
not asserted in a voiceover.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from taashira.domain.temporal import Interval


class NodeState(StrEnum):
    BLOCKED = "blocked"  # upstream dependencies unmet
    READY = "ready"  # can be started now
    IN_PROGRESS = "in_progress"
    SATISFIED = "satisfied"
    AT_RISK = "at_risk"  # will miss its latest start if nothing changes
    NEEDS_HUMAN_REVIEW = "needs_human_review"  # low confidence or unknown dates
    FAILED = "failed"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class ConstraintViolation(BaseModel):
    """A constraint that failed, and what the planner did about it."""

    requirement_id: str
    constraint_kind: str
    description: str
    severity: Severity
    authority: str
    remediation_applied: str | None = Field(
        default=None,
        description="Requirement id spliced into the graph in response, if any.",
    )
    detail: str | None = None


class CampaignNode(BaseModel):
    requirement_id: str
    state: NodeState = NodeState.BLOCKED

    earliest_finish: date | None = None
    latest_finish: date | None = None
    slack_days: int | None = None
    on_critical_path: bool = False

    spliced_by: str | None = Field(
        default=None,
        description=(
            "Requirement whose failing constraint inserted this node. None for base-graph "
            "nodes. This is what makes a cascade legible after the fact."
        ),
    )
    depth: int = Field(
        default=0,
        description="How many remediation hops from the base graph. 0 = originally required.",
    )

    evidence_asset_ids: list[str] = Field(default_factory=list)
    violations: list[ConstraintViolation] = Field(default_factory=list)

    @property
    def is_late(self) -> bool:
        return self.slack_days is not None and self.slack_days < 0


class Campaign(BaseModel):
    campaign_id: str
    applicant_id: str
    pack_id: str
    pack_version: str
    corridor_id: str

    target_date: date = Field(description="The immovable date everything schedules backwards from.")
    program: Interval

    nodes: list[CampaignNode] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    violations: list[ConstraintViolation] = Field(default_factory=list)

    feasible: bool = True
    binding_constraint: str | None = Field(
        default=None,
        description=(
            "When infeasible, the specific constraint that makes it so. Never report "
            "'not enough time' without naming what is actually binding."
        ),
    )

    version: int = 1
    computed_at: datetime = Field(default_factory=lambda: datetime.now())

    def node(self, requirement_id: str) -> CampaignNode | None:
        for n in self.nodes:
            if n.requirement_id == requirement_id:
                return n
        return None

    @property
    def node_ids(self) -> list[str]:
        return [n.requirement_id for n in self.nodes]

    @property
    def at_risk_nodes(self) -> list[CampaignNode]:
        return [n for n in self.nodes if n.state == NodeState.AT_RISK or n.is_late]

    @property
    def spliced_nodes(self) -> list[CampaignNode]:
        """Nodes that exist only because a constraint failed — the cascade itself."""
        return [n for n in self.nodes if n.spliced_by is not None]


class EventKind(StrEnum):
    DOCUMENT_INGESTED = "document.ingested"
    PLAN_CHANGED = "plan.changed"
    NODE_AT_RISK = "node.at_risk"
    CAMPAIGN_INFEASIBLE = "campaign.infeasible"
    ACTION_REQUIRED = "action.required"


class Event(BaseModel):
    event_id: str
    campaign_id: str
    kind: EventKind
    occurred_at: datetime = Field(default_factory=lambda: datetime.now())
    idempotency_key: str = Field(
        description="(campaign_id, content hash). Redelivery must not double-act."
    )
    payload: dict = Field(default_factory=dict)


class ActionKind(StrEnum):
    WRITE_CALENDAR = "write_calendar"
    RENDER_PACK = "render_pack"
    DRAFT_REQUEST = "draft_request"
    NOTIFY = "notify"


class ActionStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"


class Action(BaseModel):
    action_id: str
    campaign_id: str
    kind: ActionKind
    status: ActionStatus = ActionStatus.PENDING
    idempotency_key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    target: str | None = None
    payload: dict = Field(default_factory=dict)
    result: dict | None = None
    error: str | None = None
