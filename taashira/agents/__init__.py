"""The agent layer.

Four LLM agents, each with a narrow job and a declared `output_schema`:

    DocumentExtractor  multimodal · reads dates off a photographed document
    IntakeAgent        turns a conversation into a typed CampaignSpec
    ConsularCritic     adversarial · argues for refusal
    CampaignCoach      turns findings and plan state into prioritised actions

Two things are deliberately **not** agents:

**Scheduling.** Constraint evaluation, backward scheduling, critical path and feasibility
are ordinary Python in `taashira.planner`. A model that is plausibly wrong about a date
costs an academic year, and there is no way to unit-test a prompt the way you can test
arithmetic.

**Routing.** Which agent runs is decided by a Pub/Sub job kind, not by a model choosing.
A deterministic router cannot hallucinate a step, cannot loop, and fails into a
dead-letter queue that can be inspected.

The agents are also not chained directly to one another. A deterministic grounding filter
sits between the critic and the coach, so a finding citing an invented regulation is
discarded before it can become advice. Chaining them through ADK session state would be
fewer lines and would let a fabricated rule propagate — the filter is the point.
"""

from taashira.agents.coach import build_coach, build_coach_prompt, ground_actions
from taashira.agents.critic import build_consular_critic, build_review_prompt, ground_findings
from taashira.agents.extract import (
    build_document_extractor,
    extract_document,
    needs_review,
    to_identity_document,
)
from taashira.agents.intake import build_intake_agent, run_intake
from taashira.agents.run import AgentOutputInvalid, Attachment, run_structured

__all__ = [
    "AgentOutputInvalid",
    "Attachment",
    "build_coach",
    "build_coach_prompt",
    "build_consular_critic",
    "build_document_extractor",
    "build_intake_agent",
    "build_review_prompt",
    "extract_document",
    "ground_actions",
    "ground_findings",
    "needs_review",
    "run_intake",
    "run_structured",
    "to_identity_document",
]
