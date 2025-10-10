"""Shared validation helpers aligned with the Career Bot constitution."""

from __future__ import annotations

import re
from typing import Optional

__all__ = [
    "ensure_timestamp_uuidv4",
    "normalize_auth_username",
    "is_valid_email",
    "ensure_email",
    "ensure_password_strength",
]

_CANONICAL_TIMESTAMP_UUIDV4_PATTERN = re.compile(
    r"^[0-9]{8}T[0-9]{6}[0-9]{4}[0-9a-f]{32}$",
    re.IGNORECASE,
)

_LEGACY_TIMESTAMP_UUIDV4_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{4}_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._@+-]{3,128}$")
_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _canonicalize_timestamp_uuidv4(raw: str) -> Optional[str]:
    candidate = raw.strip()
    if not candidate:
        return None
    if _CANONICAL_TIMESTAMP_UUIDV4_PATTERN.fullmatch(candidate):
        return candidate

    relaxed = candidate.replace("+", "")
    if _CANONICAL_TIMESTAMP_UUIDV4_PATTERN.fullmatch(relaxed):
        return relaxed

    if _LEGACY_TIMESTAMP_UUIDV4_PATTERN.fullmatch(candidate):
        ts_part, uuid_part = candidate.split("_", 1)
        sanitized_ts = (
            ts_part
            .replace("-", "")
            .replace(":", "")
            .replace("+", "")
        )
        sanitized_uuid = uuid_part.replace("-", "")
        canonical = f"{sanitized_ts}{sanitized_uuid}"
        if _CANONICAL_TIMESTAMP_UUIDV4_PATTERN.fullmatch(canonical):
            return canonical
    return None


def ensure_timestamp_uuidv4(value: Optional[str], *, field_name: str = "value") -> str:
    """Validate and normalize timestamp+uuid identifiers.

    Returns the canonical format (YYYYMMDDTHHMMSSZZZZ + uuid4 hex without separators).
    Legacy formats with dashes/underscores are accepted and normalized.
    """
    if value is None or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string in timestamp_uuidv4 format")

    canonical = _canonicalize_timestamp_uuidv4(value)
    if canonical is None:
        raise ValueError(f"{field_name} must match timestamp_uuidv4 format")
    return canonical


def normalize_auth_username(value: Optional[str]) -> str:
    """Normalize auth usernames with constitution-compliant rules."""
    if value is None:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    normalized = normalized.lower()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "auth_username must be 3-128 characters of letters, numbers, '.', '_', '@', '+', or '-'"
        )
    return normalized


def is_valid_email(value: Optional[str]) -> bool:
    """Return True when the provided value is a syntactically valid email address."""
    if value is None:
        return False
    return bool(_EMAIL_PATTERN.fullmatch(value.strip()))


def ensure_email(value: Optional[str], *, field_name: str = "email") -> str:
    """Validate and normalize email addresses."""
    if value is None or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    candidate = value.strip().lower()
    if not candidate:
        raise ValueError(f"{field_name} must not be empty")
    if not is_valid_email(candidate):
        raise ValueError(f"{field_name} must be a valid email address")
    return candidate


def ensure_password_strength(value: Optional[str], *, field_name: str = "password", min_length: int = 8) -> str:
    """Validate password strength requirements."""
    if value is None or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    candidate = value.strip()
    if len(candidate) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters long")
    return candidate



