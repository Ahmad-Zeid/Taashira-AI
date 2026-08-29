"""Deterministic campaign planning.

No model calls anywhere in this package. Constraint evaluation and date arithmetic are
pure functions over the domain kernel, which is what makes them testable — and what
lets the agent layer above be judged on interpretation rather than arithmetic.
"""

from taashira.planner.build import PlanningDidNotConverge, plan_campaign
from taashira.planner.context import PlanContext, UnresolvedTimeRef
from taashira.planner.diff import NodeChange, PlanDiff, diff_plans
from taashira.planner.evaluate import Evaluation, Outcome, evaluate
from taashira.planner.schedule import (
    CyclicGraph,
    ScheduledNode,
    critical_path,
    schedule,
    topological_order,
)

__all__ = [
    "CyclicGraph",
    "Evaluation",
    "NodeChange",
    "Outcome",
    "PlanContext",
    "PlanDiff",
    "PlanningDidNotConverge",
    "ScheduledNode",
    "UnresolvedTimeRef",
    "critical_path",
    "diff_plans",
    "evaluate",
    "plan_campaign",
    "schedule",
    "topological_order",
]
