"""Persistence. Nothing above this package imports a cloud client directly."""

from __future__ import annotations

from taashira.config import Settings
from taashira.store.base import CampaignStore
from taashira.store.memory import InMemoryStore

__all__ = ["CampaignStore", "InMemoryStore", "build_store"]


def build_store(config: Settings) -> CampaignStore:
    """Firestore when configured and reachable, otherwise in-memory.

    The import is deferred so that a local run with `TAASHIRA_USE_FIRESTORE=0` does not
    need the cloud libraries installed at all.
    """
    if not (config.use_firestore and config.project_id):
        return InMemoryStore()

    from taashira.store.firestore import FirestoreStore

    return FirestoreStore(project=config.project_id)
