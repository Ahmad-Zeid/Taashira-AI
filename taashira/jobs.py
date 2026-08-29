"""Work handed from the public API to the worker.

The API service account has no Vertex AI access — deliberately, so that compromising the
browser-facing service cannot spend on inference. That means the API cannot run an agent
itself. It publishes a job instead, and the worker, which holds the only identity allowed
to call a model, picks it up.

The security boundary and the async architecture are therefore the same decision, which is
why clicking "review" in the UI is a genuinely backgrounded operation rather than a
synchronous call dressed up as one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum


class JobKind(StrEnum):
    EXTRACT_DOCUMENT = "extract_document"
    REVIEW_CAMPAIGN = "review_campaign"


@dataclass(frozen=True)
class Job:
    kind: JobKind
    campaign_id: str
    payload: dict = field(default_factory=dict)

    def encode(self) -> bytes:
        return json.dumps(
            {"kind": self.kind.value, "campaign_id": self.campaign_id, "payload": self.payload}
        ).encode("utf-8")

    @classmethod
    def decode(cls, raw: dict) -> Job | None:
        try:
            return cls(
                kind=JobKind(raw["kind"]),
                campaign_id=raw["campaign_id"],
                payload=raw.get("payload", {}),
            )
        except (KeyError, ValueError):
            return None


def publish(job: Job, *, project: str, topic: str) -> str:
    """Publish a job. Import is local so the API image need not carry the client at rest."""
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    path = publisher.topic_path(project, topic)
    return publisher.publish(path, job.encode()).result(timeout=30)
