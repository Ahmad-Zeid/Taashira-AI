"""Storage protocol.

Two implementations satisfy this: an in-memory one for tests and local runs with no
credentials, and a Firestore one for deployment. Everything above the store is written
against the protocol, so the planner and agents never import a cloud client.

Campaigns are versioned append-only. Each re-plan writes a new immutable snapshot
rather than mutating the last one, which is what makes "the agent re-planned itself"
provable from stored history instead of asserted in a voiceover.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from taashira.domain.campaign import Action, Campaign, Event
from taashira.domain.documents import Applicant


@runtime_checkable
class CampaignStore(Protocol):
    # -- applicants -------------------------------------------------------
    def save_applicant(self, applicant: Applicant) -> None: ...
    def get_applicant(self, applicant_id: str) -> Applicant | None: ...

    # -- campaigns --------------------------------------------------------
    def save_campaign(self, campaign: Campaign) -> None:
        """Persist as current *and* append an immutable version snapshot."""
        ...

    def get_campaign(self, campaign_id: str) -> Campaign | None: ...
    def list_campaigns(self) -> list[Campaign]: ...
    def get_version(self, campaign_id: str, version: int) -> Campaign | None: ...
    def list_versions(self, campaign_id: str) -> list[Campaign]: ...

    # -- audit trail ------------------------------------------------------
    def append_event(self, event: Event) -> bool:
        """Record an event. Returns False when the idempotency key was already seen."""
        ...

    def list_events(self, campaign_id: str, limit: int = 100) -> list[Event]: ...

    def record_action(self, action: Action) -> bool:
        """Record an action. Returns False when the idempotency key was already seen.

        This is the guard against a redelivered Pub/Sub message acting twice — the
        "resumable agent orders two laptops" failure from Google's own ADK workshop.
        """
        ...

    def list_actions(self, campaign_id: str, limit: int = 100) -> list[Action]: ...

    # -- agent output -----------------------------------------------------
    def save_review(self, campaign_id: str, review: dict) -> None:
        """Store the latest grounded critic + coach output for a campaign."""
        ...

    def get_review(self, campaign_id: str) -> dict | None: ...
