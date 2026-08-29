"""Runtime configuration, read from the environment.

Nothing secret lives here. Cloud Run injects the project and region, and credentials
come from the attached service account via Application Default Credentials — no keys
are ever written to disk or passed through agent context.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

#: Verified reachable on Vertex AI in this project on 2026-08-28.
#: Gemini 3.5 Pro is not publicly released; Flash and Flash-Lite are the 3.5 tier.
DEFAULT_MODEL = "gemini-3.5-flash"

#: Cheap tier for classification and routing, where reasoning depth is not needed.
DEFAULT_FAST_MODEL = "gemini-3.5-flash-lite"

#: Gemini 3.5 is served from the `global` endpoint, not a regional one.
DEFAULT_MODEL_LOCATION = "global"


@dataclass(frozen=True)
class Settings:
    project_id: str
    region: str = "us-central1"
    model: str = DEFAULT_MODEL
    fast_model: str = DEFAULT_FAST_MODEL
    model_location: str = DEFAULT_MODEL_LOCATION

    topic_tick: str = "campaign-tick"
    topic_events: str = "campaign-events"
    topic_dead: str = "campaign-dead"

    #: When false the API uses an in-memory store, so the planner and endpoints can be
    #: exercised with no cloud credentials at all.
    use_firestore: bool = True

    labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Settings:
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or ""
        return cls(
            project_id=project,
            region=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            model=os.getenv("TAASHIRA_MODEL", DEFAULT_MODEL),
            fast_model=os.getenv("TAASHIRA_FAST_MODEL", DEFAULT_FAST_MODEL),
            model_location=os.getenv("TAASHIRA_MODEL_LOCATION", DEFAULT_MODEL_LOCATION),
            use_firestore=os.getenv("TAASHIRA_USE_FIRESTORE", "1") != "0",
        )


def settings() -> Settings:
    return Settings.from_env()
