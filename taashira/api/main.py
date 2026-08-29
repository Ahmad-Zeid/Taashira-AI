"""FastAPI application: the operator's view of a running campaign.

Read-only over the store. No model is called anywhere in this service — every number
on screen comes from the deterministic planner, and the API's service account has no
Vertex AI access to call one with.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from taashira import __version__
from taashira.config import settings
from taashira.domain.temporal import Interval
from taashira.fixtures import (
    MASTERS_PROGRAM,
    REFERENCE_TODAY,
    stateless_masters_applicant,
    well_documented_applicant,
)
from taashira.packs import available_packs, load_pack_by_id
from taashira.planner import plan_campaign
from taashira.store import build_store

app = FastAPI(
    title="Taashira",
    version=__version__,
    description=(
        "Plans a student-visa campaign as a dependency graph of documents with "
        "validity windows, scheduled backwards from an immovable date."
    ),
)

STATIC = Path(__file__).parent / "static"
_FIXTURES = {"stateless": stateless_masters_applicant, "control": well_documented_applicant}


def _store():
    return build_store(settings())


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"))


@app.get("/api/health")
def health() -> dict:
    """Liveness, plus enough detail to show which project and model are wired up.

    Deliberately not at `/healthz`: Google's frontend intercepts that path before it
    reaches the container, so the route 404s in Cloud Run while passing local tests.
    """
    config = settings()
    return {
        "status": "ok",
        "role": "api",
        "version": __version__,
        "project": config.project_id or "(unset)",
        "region": config.region,
        "model": config.model,
        "model_location": config.model_location,
        "packs": available_packs(),
    }


@app.get("/api/packs")
def list_packs() -> dict:
    packs = []
    for pack_id in available_packs():
        pack = load_pack_by_id(pack_id)
        packs.append(
            {
                "pack_id": pack.pack_id,
                "version": pack.version,
                "corridor": str(pack.corridor),
                "requirements": len(pack.requirements),
                "base_graph": sum(1 for r in pack.requirements if not r.remediation_only),
                "remediation_only": sum(1 for r in pack.requirements if r.remediation_only),
                "sources": pack.sources,
            }
        )
    return {"packs": packs}


def _decorate(campaign) -> dict:
    """Attach requirement labels so the UI shows prose, not identifiers."""
    pack = load_pack_by_id(campaign.pack_id)
    payload = campaign.model_dump(mode="json")
    for node in payload["nodes"]:
        requirement = pack.by_id(node["requirement_id"])
        node["label"] = requirement.label
        node["actor"] = requirement.actor
        node["authority"] = requirement.authority
        node["guidance"] = requirement.guidance
    payload["corridor"] = str(pack.corridor)
    return payload


@app.get("/api/campaigns")
def list_campaigns() -> dict:
    campaigns = _store().list_campaigns()
    return {
        "campaigns": [
            {
                "campaign_id": c.campaign_id,
                "corridor_id": c.corridor_id,
                "version": c.version,
                "feasible": c.feasible,
                "nodes": len(c.nodes),
                "target_date": str(c.target_date),
            }
            for c in campaigns
        ]
    }


@app.get("/api/campaign/{campaign_id}")
def get_campaign(campaign_id: str) -> JSONResponse:
    campaign = _store().get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(404, f"no campaign '{campaign_id}'")
    return JSONResponse(_decorate(campaign))


@app.get("/api/campaign/{campaign_id}/versions")
def list_versions(campaign_id: str) -> dict:
    """Version history — the evidence that the plan repaired itself."""
    versions = _store().list_versions(campaign_id)
    return {
        "versions": [
            {
                "version": v.version,
                "computed_at": v.computed_at.isoformat(),
                "feasible": v.feasible,
                "nodes": len(v.nodes),
                "node_ids": v.node_ids,
                "critical_path": v.critical_path,
            }
            for v in versions
        ]
    }


@app.get("/api/campaign/{campaign_id}/events")
def list_events(campaign_id: str) -> dict:
    events = _store().list_events(campaign_id, limit=200)
    return {"events": [e.model_dump(mode="json") for e in events]}


@app.get("/api/campaign/{campaign_id}/stream")
async def stream_events(campaign_id: str) -> StreamingResponse:
    """Server-sent events: new activity as the background worker produces it."""

    async def generate():
        seen: set[str] = set()
        store = _store()
        for _ in range(600):  # ~20 minutes, then the client reconnects
            try:
                campaign = store.get_campaign(campaign_id)
                for event in store.list_events(campaign_id, limit=200):
                    if event.event_id in seen:
                        continue
                    seen.add(event.event_id)
                    yield f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
                if campaign is not None:
                    beat = {"kind": "heartbeat", "version": campaign.version}
                    yield f"data: {json.dumps(beat)}\n\n"
            except Exception as exc:  # noqa: BLE001 - a stream must not die on one bad read
                yield f"data: {json.dumps({'kind': 'error', 'detail': str(exc)})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/preview")
def preview(
    pack_id: str = "lb-prtd__us-f1",
    applicant: str = "stateless",
    program_start: date | None = None,
    program_end: date | None = None,
    today: date | None = None,
) -> JSONResponse:
    """Plan a campaign for a synthetic applicant without persisting anything.

    `applicant=stateless` holds a one-year travel document and triggers the cascade;
    `applicant=control` holds a ten-year passport and does not. Same pack either way,
    which is what shows the cascade is driven by constraints rather than hardcoded.
    """
    if applicant not in _FIXTURES:
        raise HTTPException(404, f"unknown applicant '{applicant}'; try {list(_FIXTURES)}")
    try:
        pack = load_pack_by_id(pack_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

    program = MASTERS_PROGRAM
    if program_start and program_end:
        try:
            program = Interval(start=program_start, end=program_end)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    result = plan_campaign(
        pack=pack,
        applicant=_FIXTURES[applicant](),
        program=program,
        today=today or REFERENCE_TODAY,
    )
    return JSONResponse(_decorate(result))
