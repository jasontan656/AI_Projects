from __future__ import annotations

import re


_SLUG_RE = re.compile(r"^[a-z0-9_.:]{1,64}$")


def is_valid_task_slug(value: str) -> bool:
    """Return True if value is a valid task slug (Constitution-compliant)."""
    return bool(_SLUG_RE.match(value))

