"""Consular appointment wait times.

The US State Department publishes average interview wait times per post as public data,
updated monthly in 15- or 30-day increments. Reading that published figure is categorically
different from automating a booking system: we never touch the appointment portal, never
hold a slot, and never submit anything. We read a number the government publishes and let
it change the plan.

Two sources, in order of preference:

  1. `LivePublishedSource` — fetches the published page.
  2. `SnapshotSource` — a committed reading with the date it was taken.

If the live fetch fails or the page layout changes, the system falls back to the snapshot
**and says which one it used**. It never invents a number, because a fabricated wait time
would silently move every downstream date in a months-long plan.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

PUBLISHED_URL = (
    "https://travel.state.gov/content/travel/en/us-visas/"
    "visa-information-resources/global-visa-wait-times.html"
)

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "wait_times_snapshot.json"


@dataclass(frozen=True)
class WaitTimeObservation:
    """One reading of the published wait time for a post."""

    post: str
    visa_class: str
    days: int
    observed_on: date
    source: str
    note: str | None = None

    def key(self) -> str:
        return f"{self.post}|{self.visa_class}|{self.observed_on.isoformat()}"

    def to_dict(self) -> dict:
        return {
            "post": self.post,
            "visa_class": self.visa_class,
            "days": self.days,
            "observed_on": self.observed_on.isoformat(),
            "source": self.source,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> WaitTimeObservation:
        return cls(
            post=raw["post"],
            visa_class=raw["visa_class"],
            days=int(raw["days"]),
            observed_on=date.fromisoformat(raw["observed_on"]),
            source=raw.get("source", "unknown"),
            note=raw.get("note"),
        )


class SnapshotSource:
    """A committed reading, with the date it was taken recorded alongside it."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or SNAPSHOT_PATH

    def fetch(self, post: str, visa_class: str = "student") -> WaitTimeObservation | None:
        if not self._path.exists():
            return None
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for entry in raw.get("observations", []):
            if entry["post"].lower() == post.lower() and entry["visa_class"] == visa_class:
                return WaitTimeObservation.from_dict(entry)
        return None


class LivePublishedSource:
    """Reads the figure off the published State Department page.

    Deliberately conservative: on any parsing ambiguity it returns None and lets the caller
    fall back, rather than guessing at a number that would move real deadlines.
    """

    def __init__(self, url: str = PUBLISHED_URL, timeout: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout

    def fetch(self, post: str, visa_class: str = "student") -> WaitTimeObservation | None:
        try:
            request = Request(self._url, headers={"User-Agent": "Taashira/0.1 (hackathon project)"})
            with urlopen(request, timeout=self._timeout) as response:  # noqa: S310 - fixed https URL
                html = response.read().decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError):
            return None

        # Find the row for this post and take the first day-count near it.
        index = html.lower().find(post.lower())
        if index == -1:
            return None
        window = re.sub(r"<[^>]+>", " ", html[index : index + 600])
        match = re.search(r"(\d{1,3})\s*(?:calendar\s*)?days?", window, re.IGNORECASE)
        if not match:
            return None

        return WaitTimeObservation(
            post=post,
            visa_class=visa_class,
            days=int(match.group(1)),
            observed_on=datetime.now().date(),
            source="travel.state.gov (live)",
        )


def observe(
    post: str, visa_class: str = "student", *, allow_live: bool = True
) -> WaitTimeObservation | None:
    """Best available reading, preferring live and falling back to the snapshot."""
    if allow_live and (live := LivePublishedSource().fetch(post, visa_class)):
        return live
    return SnapshotSource().fetch(post, visa_class)


def observed_lead_days(pack, *, allow_live: bool = True) -> dict[str, int]:
    """Lead-time overrides for every requirement in the pack that declares a signal.

    Returns only what was actually observed. A requirement whose signal cannot be read keeps
    its pack estimate rather than being silently zeroed.
    """
    overrides: dict[str, int] = {}
    for requirement in pack.requirements:
        signal = requirement.wait_time_signal
        if signal is None:
            continue
        reading = observe(signal.post, signal.visa_class, allow_live=allow_live)
        if reading is not None:
            overrides[requirement.id] = reading.days
    return overrides
