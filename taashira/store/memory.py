"""In-memory store.

Used by the tests and by any local run with `TAASHIRA_USE_FIRESTORE=0`, so the whole
system can be exercised end to end with no cloud credentials at all.
"""

from __future__ import annotations

from taashira.domain.campaign import Action, Campaign, Event
from taashira.domain.documents import Applicant


class InMemoryStore:
    def __init__(self) -> None:
        self._applicants: dict[str, Applicant] = {}
        self._campaigns: dict[str, Campaign] = {}
        self._versions: dict[str, dict[int, Campaign]] = {}
        self._events: list[Event] = []
        self._actions: list[Action] = []
        self._seen_keys: set[str] = set()

    def save_applicant(self, applicant: Applicant) -> None:
        self._applicants[applicant.applicant_id] = applicant.model_copy(deep=True)

    def get_applicant(self, applicant_id: str) -> Applicant | None:
        found = self._applicants.get(applicant_id)
        return found.model_copy(deep=True) if found else None

    def save_campaign(self, campaign: Campaign) -> None:
        snapshot = campaign.model_copy(deep=True)
        self._campaigns[campaign.campaign_id] = snapshot
        self._versions.setdefault(campaign.campaign_id, {})[campaign.version] = snapshot

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        found = self._campaigns.get(campaign_id)
        return found.model_copy(deep=True) if found else None

    def list_campaigns(self) -> list[Campaign]:
        return [c.model_copy(deep=True) for c in self._campaigns.values()]

    def get_version(self, campaign_id: str, version: int) -> Campaign | None:
        found = self._versions.get(campaign_id, {}).get(version)
        return found.model_copy(deep=True) if found else None

    def list_versions(self, campaign_id: str) -> list[Campaign]:
        versions = self._versions.get(campaign_id, {})
        return [versions[v].model_copy(deep=True) for v in sorted(versions)]

    def append_event(self, event: Event) -> bool:
        if event.idempotency_key in self._seen_keys:
            return False
        self._seen_keys.add(event.idempotency_key)
        self._events.append(event.model_copy(deep=True))
        return True

    def list_events(self, campaign_id: str, limit: int = 100) -> list[Event]:
        matching = [e for e in self._events if e.campaign_id == campaign_id]
        return [e.model_copy(deep=True) for e in matching[-limit:]]

    def record_action(self, action: Action) -> bool:
        if action.idempotency_key in self._seen_keys:
            return False
        self._seen_keys.add(action.idempotency_key)
        self._actions.append(action.model_copy(deep=True))
        return True

    def list_actions(self, campaign_id: str, limit: int = 100) -> list[Action]:
        matching = [a for a in self._actions if a.campaign_id == campaign_id]
        return [a.model_copy(deep=True) for a in matching[-limit:]]
