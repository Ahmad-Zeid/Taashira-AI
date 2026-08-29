"""Worker service: Pub/Sub push endpoint and the daily tick.

Cloud Scheduler publishes to `campaign-tick` once a day. Pub/Sub pushes that message
here. For every active campaign we re-evaluate constraints, re-plan, and diff against
the stored version — emitting events only when the plan really changed.

Every handler is idempotent on `(campaign_id, version, event)`. Pub/Sub guarantees
at-least-once delivery, so a redelivered tick is normal traffic, not an error, and it
must not produce a second set of alerts or a second action.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
from datetime import date
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from taashira import __version__
from taashira.config import settings
from taashira.fixtures import MASTERS_PROGRAM, REFERENCE_TODAY, stateless_masters_applicant
from taashira.packs import load_pack_by_id
from taashira.service import replan
from taashira.store import build_store

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("taashira.worker")


def emit(event: str, **fields: Any) -> None:
    """Structured log line, keyed so a whole campaign can be traced in Cloud Logging."""
    log.info(json.dumps({"event": event, **fields}))


app = FastAPI(title="Taashira worker", version=__version__)


@app.get("/")
@app.get("/api/health")
def health() -> dict:
    config = settings()
    return {
        "status": "ok",
        "role": "worker",
        "version": __version__,
        "project": config.project_id or "(unset)",
        "model": config.model,
    }


def _decode(envelope: dict) -> dict:
    """Unwrap a Pub/Sub push envelope into the payload we published."""
    message = envelope.get("message") or {}
    raw = message.get("data")
    if not raw:
        return {}
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return {}


@app.post("/pubsub/tick")
async def tick(request: Request) -> JSONResponse:
    """Re-plan every active campaign.

    Always returns 200, even on a payload we cannot parse. A non-2xx tells Pub/Sub to
    redeliver, and redelivering a message that will never parse is an infinite loop —
    the dead-letter topic is for that, not the retry queue.
    """
    try:
        envelope = await request.json()
    except (json.JSONDecodeError, ValueError):
        emit("tick.bad_envelope")
        return JSONResponse({"status": "dropped", "reason": "unparseable envelope"})

    payload = _decode(envelope)
    as_of = date.fromisoformat(payload["today"]) if payload.get("today") else REFERENCE_TODAY

    config = settings()
    store = build_store(config)
    campaigns = store.list_campaigns()
    emit("tick.start", campaigns=len(campaigns), as_of=str(as_of))

    if not campaigns:
        # Nothing stored yet: seed one so a fresh deployment has something to tick.
        result = replan(
            store=store,
            pack=load_pack_by_id("lb-prtd__us-f1"),
            applicant=stateless_masters_applicant(),
            program=MASTERS_PROGRAM,
            today=as_of,
        )
        emit(
            "campaign.seeded",
            campaign_id=result.campaign.campaign_id,
            nodes=len(result.campaign.nodes),
            feasible=result.campaign.feasible,
        )
        return JSONResponse({"status": "seeded", "campaign_id": result.campaign.campaign_id})

    changed = 0
    for campaign in campaigns:
        applicant = store.get_applicant(campaign.applicant_id) or stateless_masters_applicant()
        result = replan(
            store=store,
            pack=load_pack_by_id(campaign.pack_id),
            applicant=applicant,
            program=campaign.program,
            today=as_of,
            campaign_id=campaign.campaign_id,
            target_date=campaign.target_date,
        )
        if result.changed:
            changed += 1
            emit(
                "plan.changed",
                campaign_id=result.campaign.campaign_id,
                version=result.campaign.version,
                summary=result.diff.summary(),
                events=len(result.events),
            )
        else:
            emit("plan.unchanged", campaign_id=campaign.campaign_id)

    emit("tick.done", campaigns=len(campaigns), changed=changed)
    return JSONResponse({"status": "ok", "campaigns": len(campaigns), "changed": changed})
