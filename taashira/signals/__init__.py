"""External signals that change a plan.

Everything here reads data somebody publishes. Nothing here automates a system that was
not meant to be automated.
"""

from taashira.signals.wait_times import (
    LivePublishedSource,
    SnapshotSource,
    WaitTimeObservation,
    observe,
    observed_lead_days,
)

__all__ = [
    "LivePublishedSource",
    "SnapshotSource",
    "WaitTimeObservation",
    "observe",
    "observed_lead_days",
]
