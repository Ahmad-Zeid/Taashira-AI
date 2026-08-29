"""Running agents.

A thin wrapper over the ADK runner so callers get a validated model back instead of
an event stream, and so every invocation goes through one place that knows how to
configure Vertex.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from google.adk.agents import BaseAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, ValidationError

from taashira.config import Settings


class AgentOutputInvalid(Exception):
    """The agent returned something its own output schema rejects."""


@dataclass(frozen=True)
class Attachment:
    """A document image or PDF handed to a multimodal agent.

    Bytes are passed inline to the model. This layer never writes them to disk — raw
    identity documents are the most consequential data the system touches.
    """

    data: bytes
    mime_type: str


def configure_vertex(config: Settings) -> None:
    """Point the GenAI SDK at Vertex AI using the ambient service account.

    Gemini 3.5 is served from the `global` endpoint, not a regional one — pointing at
    `us-central1` yields a 404 that reads like the model does not exist.
    """
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ["GOOGLE_CLOUD_PROJECT"] = config.project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = config.model_location


async def run_structured[T: BaseModel](
    agent: BaseAgent,
    prompt: str,
    schema: type[T],
    *,
    config: Settings,
    user_id: str = "taashira",
    attachments: Sequence[Attachment] = (),
) -> T:
    """Run a single agent to completion and validate its final response.

    `attachments` carries document images or PDFs for the multimodal agents.
    """
    configure_vertex(config)

    runner = InMemoryRunner(agent=agent, app_name="taashira")
    session = await runner.session_service.create_session(app_name="taashira", user_id=user_id)

    parts = [types.Part(text=prompt)]
    parts.extend(
        types.Part(inline_data=types.Blob(mime_type=a.mime_type, data=a.data)) for a in attachments
    )

    final = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=parts),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts)

    try:
        return schema.model_validate_json(final)
    except ValidationError as exc:
        raise AgentOutputInvalid(f"{agent.name} returned output its schema rejects: {exc}") from exc
