"""Domain kernel: documents, constraints, requirements, campaigns.

Pure data and predicates. No I/O, no model calls, no scheduling — the planner does
that, and keeping the split clean is what makes the scheduling logic testable.
"""

from taashira.domain.campaign import (
    Action,
    ActionKind,
    ActionStatus,
    Campaign,
    CampaignNode,
    ConstraintViolation,
    Event,
    EventKind,
    NodeState,
    Severity,
)
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
from taashira.domain.documents import (
    Applicant,
    DocumentKind,
    IdentityDocument,
    NationalityStatus,
    VerificationSource,
)
from taashira.domain.requirements import (
    Actor,
    Applicability,
    Corridor,
    Requirement,
    RequirementPack,
)
from taashira.domain.temporal import Interval, TimeRef

__all__ = [
    "Action",
    "ActionKind",
    "ActionStatus",
    "Applicability",
    "Applicant",
    "Actor",
    "Campaign",
    "CampaignNode",
    "ConstraintViolation",
    "Corridor",
    "CoveredPeriod",
    "Covers",
    "DocumentKind",
    "Event",
    "EventKind",
    "IdentityDocument",
    "Interval",
    "MaxAgeAtUse",
    "MinSeasoning",
    "NationalityStatus",
    "NodeState",
    "NotAfter",
    "NotBefore",
    "Requirement",
    "RequirementPack",
    "Severity",
    "TemporalConstraint",
    "TimeRef",
    "ValidAt",
    "VerificationSource",
]
