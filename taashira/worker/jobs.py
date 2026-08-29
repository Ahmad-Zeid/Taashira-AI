"""Job handlers.

Everything that touches a model lives here, because the worker holds the only service
account with `aiplatform.user`. Results are written to Firestore and announced as events,
so the browser learns about them the same way it learns about anything else the agent did
while nobody was watching.
"""

from __future__ import annotations

import uuid
from datetime import date

from taashira.agents.coach import build_coach, build_coach_prompt, ground_actions
from taashira.agents.critic import build_consular_critic, build_review_prompt, ground_findings
from taashira.agents.run import run_structured
from taashira.agents.schemas import CoachPlan, RefusalFindings
from taashira.config import Settings
from taashira.domain.campaign import Event, EventKind
from taashira.jobs import Job, JobKind
from taashira.packs import load_pack_by_id
from taashira.service import ingest_document, replan
from taashira.signals import observed_lead_days
from taashira.store.base import CampaignStore


async def handle(job: Job, *, store: CampaignStore, config: Settings, log) -> dict:
    match job.kind:
        case JobKind.EXTRACT_DOCUMENT:
            return await _extract(job, store=store, config=config, log=log)
        case JobKind.REVIEW_CAMPAIGN:
            return await _review(job, store=store, config=config, log=log)
    return {"status": "ignored", "kind": job.kind}


async def _extract(job: Job, *, store: CampaignStore, config: Settings, log) -> dict:
    """Read an uploaded document, fold it into the dossier, re-plan."""
    from google.cloud import storage

    blob_name = job.payload.get("blob")
    if not blob_name:
        return {"status": "dropped", "reason": "no blob"}

    client = storage.Client(project=config.project_id)
    blob = client.bucket(config.uploads_bucket).blob(blob_name)
    if not blob.exists():
        return {"status": "dropped", "reason": "blob missing"}

    data = blob.download_as_bytes()
    mime = blob.content_type or "image/png"

    extracted, result = await ingest_document(
        store=store,
        campaign_id=job.campaign_id,
        data=data,
        mime_type=mime,
        config=config,
        hint=job.payload.get("hint"),
        today=date.fromisoformat(job.payload["today"]) if job.payload.get("today") else None,
    )
    log(
        "document.extracted",
        campaign_id=job.campaign_id,
        kind=str(extracted.kind),
        expires_on=str(extracted.expires_on),
        confidence=extracted.confidence,
        replanned=bool(result and result.changed),
    )

    store.append_event(
        Event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            campaign_id=job.campaign_id,
            kind=EventKind.DOCUMENT_INGESTED,
            idempotency_key=f"doc-{blob_name}",
            payload={
                "kind": str(extracted.kind),
                "issued_on": str(extracted.issued_on),
                "expires_on": str(extracted.expires_on),
                "confidence": extracted.confidence,
                "summary": f"{extracted.kind} read, expires {extracted.expires_on}",
            },
        )
    )
    return {"status": "ok", "kind": str(extracted.kind)}


async def _review(job: Job, *, store: CampaignStore, config: Settings, log) -> dict:
    """Run the adversarial critic, then the coach, and store both grounded."""
    campaign = store.get_campaign(job.campaign_id)
    applicant = store.get_applicant(campaign.applicant_id) if campaign else None
    if campaign is None or applicant is None:
        return {"status": "dropped", "reason": "campaign or applicant missing"}

    pack = load_pack_by_id(campaign.pack_id)

    raw_findings = await run_structured(
        build_consular_critic(config),
        build_review_prompt(applicant, campaign, pack),
        RefusalFindings,
        config=config,
    )
    findings = ground_findings(raw_findings, pack)
    log(
        "critic.done",
        campaign_id=campaign.campaign_id,
        verdict=str(findings.verdict),
        kept=len(findings.findings),
        dropped=len(findings.dropped),
        grounding_rate=round(findings.grounding_rate, 3),
    )

    summary = f"verdict={findings.verdict}. " + " ".join(
        f"[{f.requirement_id}] {f.ground}" for f in findings.findings
    )
    raw_plan = await run_structured(
        build_coach(config),
        build_coach_prompt(campaign, pack, summary),
        CoachPlan,
        config=config,
    )
    advice = ground_actions(raw_plan, pack)
    log(
        "coach.done",
        campaign_id=campaign.campaign_id,
        actions=len(advice.actions),
        dropped=len(advice.dropped),
        grounding_rate=round(advice.grounding_rate, 3),
    )

    store.save_review(
        campaign.campaign_id,
        {
            "version": campaign.version,
            "verdict": str(findings.verdict),
            "summary": findings.summary,
            "findings": [f.model_dump(mode="json") for f in findings.findings],
            "dropped_findings": [f.model_dump(mode="json") for f in findings.dropped],
            "grounding_rate": findings.grounding_rate,
            "headline": advice.headline,
            "actions": [a.model_dump(mode="json") for a in advice.actions],
            "dropped_actions": [a.model_dump(mode="json") for a in advice.dropped],
        },
    )

    store.append_event(
        Event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            campaign_id=campaign.campaign_id,
            kind=EventKind.ACTION_REQUIRED,
            idempotency_key=f"review-{campaign.campaign_id}-v{campaign.version}",
            payload={
                "summary": f"review complete: {findings.verdict}, {len(advice.actions)} actions",
                "verdict": str(findings.verdict),
            },
        )
    )
    return {"status": "ok", "verdict": str(findings.verdict), "actions": len(advice.actions)}


def refresh_and_replan(store: CampaignStore, campaign, *, today: date, log) -> object:
    """Re-plan one campaign against the freshest published wait times."""
    pack = load_pack_by_id(campaign.pack_id)
    applicant = store.get_applicant(campaign.applicant_id)
    if applicant is None:
        return None
    return replan(
        store=store,
        pack=pack,
        applicant=applicant,
        program=campaign.program,
        today=today,
        campaign_id=campaign.campaign_id,
        target_date=campaign.target_date,
        observed_lead_days=observed_lead_days(pack),
    )
