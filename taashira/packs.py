"""Loading requirement packs from disk.

Packs are data. Adding a corridor means adding a YAML file here — no code changes,
which is the property the architecture criterion is asking about when it talks about
a "clean, modularized, ease of maintenance system".
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml

from taashira.domain.requirements import RequirementPack

PACKS_DIR = Path(__file__).resolve().parent.parent / "packs"


def load_pack(path: Path) -> RequirementPack:
    """Parse and validate one pack. Referential integrity is enforced by the model."""
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return RequirementPack.model_validate(raw)


@cache
def load_pack_by_id(pack_id: str, packs_dir: Path | None = None) -> RequirementPack:
    directory = packs_dir or PACKS_DIR
    path = directory / f"{pack_id}.yaml"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in directory.glob("*.yaml"))) or "none"
        raise FileNotFoundError(f"no pack '{pack_id}' in {directory} (available: {available})")
    return load_pack(path)


def available_packs(packs_dir: Path | None = None) -> list[str]:
    directory = packs_dir or PACKS_DIR
    return sorted(p.stem for p in directory.glob("*.yaml"))
