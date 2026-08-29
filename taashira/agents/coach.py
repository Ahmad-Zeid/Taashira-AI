"""The advisor.

`ConsularCritic` argues for refusal. This one turns that plus the plan into what the
applicant should actually do next — the job a travel advisor does.

It runs through the same grounding filter as the critic: every recommendation must cite a
requirement `authority` that exists in the loaded pack. This agent deliberately does not
browse the web. An agent that invents an immigration rule with confidence is worse than no
agent, and the pack is the only source of truth it is given.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from taashira.agents.schemas import CoachPlan, GroundedCoachPlan
from taashira.config import Settings
from taashira.domain.campaign import Campaign
from taashira.domain.requirements import RequirementPack

INSTRUCTION = """\
You advise an applicant on a visa campaign that is already planned. You are given the plan,
any constraint violations, and the refusal grounds an adversarial reviewer raised.

Produce the next actions, most urgent first.

Rules:

1. Every action MUST cite, verbatim, one of the `authority` strings you were given. Anything
   citing something else is discarded before the applicant sees it.
2. Order by what is actually binding. A node with negative slack blocks everything downstream;
   a comfortable one does not, however alarming it sounds.
3. Be concrete and imperative. "Request a fresh Individual Civil Extract from General Security"
   is an action. "Ensure your documentation is in order" is noise.
4. Say what breaks if it slips, in one sentence, in real terms — a missed intake, a visa that
   cannot be issued for the full programme.
5. Do not promise an outcome. You do not know whether the visa will be granted, and saying so
   would be dishonest.
6. Where a requirement carries GUIDANCE, it overrides your general knowledge. This matters
   most for applicants with no nationality: the standard advice to "show ties to your home
   country" is not merely unhelpful to a stateless applicant, it is impossible to follow, and
   repeating it wastes the one rebuttal they get. Read the guidance and follow it.

The headline is one sentence on where the campaign stands.
"""


def build_coach(config: Settings) -> LlmAgent:
    return LlmAgent(
        name="CampaignCoach",
        model=config.model,
        description="Turns plan state and refusal grounds into prioritised next actions.",
        instruction=INSTRUCTION,
        output_schema=CoachPlan,
        output_key="coach_plan",
    )


def ground_actions(raw: CoachPlan, pack: RequirementPack) -> GroundedCoachPlan:
    """Drop recommendations citing an authority the pack does not contain."""
    permitted = pack.authorities
    kept, dropped = [], []
    for action in raw.actions:
        (kept if action.authority in permitted else dropped).append(action)
    return GroundedCoachPlan(headline=raw.headline, actions=kept, dropped=dropped)


def build_coach_prompt(campaign: Campaign, pack: RequirementPack, findings_summary: str) -> str:
    outstanding = [n for n in campaign.nodes if n.state not in ("satisfied",)]

    def describe(node) -> str:
        requirement = pack.by_id(node.requirement_id)
        line = (
            f"  - {node.requirement_id} [{node.state}] slack={node.slack_days}d"
            f"{' CRITICAL' if node.on_critical_path else ''}"
            f"{f' (spliced by {node.spliced_by})' if node.spliced_by else ''}"
        )
        if requirement.guidance:
            guidance = " ".join(requirement.guidance.split())
            line += f"\n      GUIDANCE: {guidance}"
        return line

    nodes = "\n".join(
        describe(n) for n in sorted(outstanding, key=lambda n: (n.slack_days is None, n.slack_days))
    )
    violations = (
        "\n".join(f"  - {v.requirement_id}: {v.detail}" for v in campaign.violations) or "  (none)"
    )
    authorities = "\n".join(f"  - {a}" for a in sorted(pack.authorities))

    return f"""\
CORRIDOR: {pack.corridor}
FEASIBLE: {campaign.feasible}
BINDING CONSTRAINT: {campaign.binding_constraint or "none"}
PROGRAMME: {campaign.program.start} to {campaign.program.end}

OUTSTANDING WORK (least slack first):
{nodes}

CONSTRAINT VIOLATIONS:
{violations}

ADVERSARIAL REVIEW:
{findings_summary}

AUTHORITIES YOU MAY CITE (verbatim, exactly one per action):
{authorities}
"""
