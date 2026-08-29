"""Container entrypoint.

Both Cloud Run services run the same image and are selected by `TAASHIRA_ROLE`. One
image means one build and one thing to keep current; the separation that matters is
enforced by IAM, not by shipping two artefacts — `taashira-api` has no Vertex AI
access whichever module it loads.
"""

from __future__ import annotations

import os

ROLE = os.getenv("TAASHIRA_ROLE", "api")

if ROLE == "worker":
    from taashira.worker.main import app as app
else:
    from taashira.api.main import app as app
