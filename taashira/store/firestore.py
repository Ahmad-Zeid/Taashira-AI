"""Firestore-backed store.

Layout:

    applicants/{applicant_id}
    campaigns/{campaign_id}                    current plan
    campaigns/{campaign_id}/versions/{version} immutable snapshots
    events/{idempotency_key}                   append-only, key doubles as the dedupe
    actions/{idempotency_key}                  append-only, key doubles as the dedupe

Using the idempotency key as the document id is what makes deduplication atomic: a
create with `document_id` already present raises, and there is no read-then-write race
for a redelivered message to slip through.
"""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcloud_exc
from google.cloud import firestore

from taashira.domain.campaign import Action, Campaign, Event
from taashira.domain.documents import Applicant


class FirestoreStore:
    def __init__(self, project: str, client: firestore.Client | None = None) -> None:
        self._db = client or firestore.Client(project=project)

    # -- applicants -------------------------------------------------------

    def save_applicant(self, applicant: Applicant) -> None:
        self._db.collection("applicants").document(applicant.applicant_id).set(
            applicant.model_dump(mode="json")
        )

    def get_applicant(self, applicant_id: str) -> Applicant | None:
        snap = self._db.collection("applicants").document(applicant_id).get()
        return Applicant.model_validate(snap.to_dict()) if snap.exists else None

    # -- campaigns --------------------------------------------------------

    def save_campaign(self, campaign: Campaign) -> None:
        """Write the current plan and append its immutable version snapshot.

        Batched so a reader can never observe a current plan whose version snapshot
        is missing.
        """
        payload: dict[str, Any] = campaign.model_dump(mode="json")
        doc = self._db.collection("campaigns").document(campaign.campaign_id)

        batch = self._db.batch()
        batch.set(doc, payload)
        batch.set(doc.collection("versions").document(str(campaign.version)), payload)
        batch.commit()

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        snap = self._db.collection("campaigns").document(campaign_id).get()
        return Campaign.model_validate(snap.to_dict()) if snap.exists else None

    def list_campaigns(self) -> list[Campaign]:
        return [
            Campaign.model_validate(s.to_dict()) for s in self._db.collection("campaigns").stream()
        ]

    def get_version(self, campaign_id: str, version: int) -> Campaign | None:
        snap = (
            self._db.collection("campaigns")
            .document(campaign_id)
            .collection("versions")
            .document(str(version))
            .get()
        )
        return Campaign.model_validate(snap.to_dict()) if snap.exists else None

    def list_versions(self, campaign_id: str) -> list[Campaign]:
        snaps = (
            self._db.collection("campaigns").document(campaign_id).collection("versions").stream()
        )
        campaigns = [Campaign.model_validate(s.to_dict()) for s in snaps]
        return sorted(campaigns, key=lambda c: c.version)

    # -- audit trail ------------------------------------------------------

    def _create_once(self, collection: str, key: str, payload: dict) -> bool:
        """Create a document, returning False if that key already exists."""
        try:
            self._db.collection(collection).document(key).create(payload)
            return True
        except gcloud_exc.AlreadyExists:
            return False

    def append_event(self, event: Event) -> bool:
        return self._create_once("events", event.idempotency_key, event.model_dump(mode="json"))

    def list_events(self, campaign_id: str, limit: int = 100) -> list[Event]:
        snaps = (
            self._db.collection("events")
            .where(filter=firestore.FieldFilter("campaign_id", "==", campaign_id))
            .limit(limit)
            .stream()
        )
        events = [Event.model_validate(s.to_dict()) for s in snaps]
        return sorted(events, key=lambda e: e.occurred_at)

    def record_action(self, action: Action) -> bool:
        return self._create_once("actions", action.idempotency_key, action.model_dump(mode="json"))

    def list_actions(self, campaign_id: str, limit: int = 100) -> list[Action]:
        snaps = (
            self._db.collection("actions")
            .where(filter=firestore.FieldFilter("campaign_id", "==", campaign_id))
            .limit(limit)
            .stream()
        )
        actions = [Action.model_validate(s.to_dict()) for s in snaps]
        return sorted(actions, key=lambda a: a.created_at)
