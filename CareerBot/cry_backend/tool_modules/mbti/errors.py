from __future__ import annotations

"""Custom exception hierarchy for MBTI module."""


class MBTIError(Exception):
    """Base class for MBTI domain errors."""


class MBTIConfigurationError(MBTIError):
    """Raised when MBTI static assets or configuration are invalid."""


class MBTIStepStateError(MBTIError):
    """Raised when step progression is inconsistent (e.g., batch mismatch)."""


class MBTIDatabaseError(MBTIError):
    """Raised when database operations fail for MBTI workflows."""


__all__ = [
    "MBTIError",
    "MBTIConfigurationError",
    "MBTIStepStateError",
    "MBTIDatabaseError",
]
