"""Intake.

The conversation exists to produce a `CampaignSpec` and then get out of the way. It is
not the product; it is the door. Everything downstream consumes typed state, never the
transcript — which is the structural reason this is an agent system with a chat front
door rather than a chatbot with agents bolted on.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from taashira.agents.run import run_structured
from taashira.agents.schemas import CampaignSpec
from taashira.config import Settings
from taashira.packs import available_packs, load_pack_by_id

INSTRUCTION = """\
You are the intake step for a student visa planning system. Your only job is to establish
four things and then stop:

  1. which corridor applies — the document the applicant travels on, and where they are going
  2. when the programme starts and ends
  3. what the applicant's status is: national, stateless, refugee_travel_document, contested
  4. which documents they already hold

How to behave:

- Ask about ONE thing at a time. A person filling this in is already tired.
- Never invent a date. If they say "next September", ask which year and get the exact dates —
  the entire plan is scheduled backwards from the programme start, so an approximate date
  produces an approximate plan, which is worthless.
- If they hold a travel document, a laissez-passer or a certificate of identity rather than a
  passport, that is `refugee_travel_document` or `stateless`. Ask; do not assume. It changes
  which requirements apply.
- Do not ask for document numbers, and do not ask them to type dates off their documents.
  They will upload the documents and those get read automatically.
- Set `ready_to_plan` true only once you have a pack id and both programme dates.
- `reply` is what the applicant sees. One short paragraph, plain language, no jargon and no
  bullet lists.

Never speculate about whether a visa will be granted. You are collecting facts.
"""


def build_intake_agent(config: Settings) -> LlmAgent:
    corridors = "\n".join(
        f"  - {pack_id}: {load_pack_by_id(pack_id).corridor}" for pack_id in available_packs()
    )
    return LlmAgent(
        name="IntakeAgent",
        model=config.model,
        description="Turns a conversation into a structured campaign specification.",
        instruction=f"{INSTRUCTION}\nCorridors currently supported:\n{corridors}\n",
        output_schema=CampaignSpec,
        output_key="campaign_spec",
    )


async def run_intake(
    history: list[tuple[str, str]], message: str, *, config: Settings
) -> CampaignSpec:
    """Advance the intake conversation by one turn.

    History is replayed into the prompt rather than held in ADK session state: intake is
    short, and a stateless call is far easier to reason about across a serverless service
    that scales to zero between messages.
    """
    transcript = "\n".join(f"{role}: {text}" for role, text in history)
    prompt = f"{transcript}\napplicant: {message}" if transcript else f"applicant: {message}"
    return await run_structured(build_intake_agent(config), prompt, CampaignSpec, config=config)
