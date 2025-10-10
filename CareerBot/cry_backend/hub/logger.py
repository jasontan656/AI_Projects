from __future__ import annotations

from typing import Any, Dict

import structlog


_REQUIRED_FIELDS: tuple[str, ...] = ("trace_id", "request_id", "route_path", "user_id", "session_id")


_logger = structlog.get_logger("hub")



def _bind_request(level: str, **kwargs: Any):
    def _is_meaningful(v: Any) -> bool:
        if v is None:
            return False
        if isinstance(v, str) and v == "":
            return False
        return True

    filtered: Dict[str, Any] = {key: value for key, value in kwargs.items() if _is_meaningful(value)}

    # Treat non-request context as a legitimate case: if no required fields are
    # provided at all (e.g., during startup), do not emit missing field warnings.
    if not any(field in filtered for field in _REQUIRED_FIELDS):
        return _logger.bind(**filtered)
    missing = [field for field in _REQUIRED_FIELDS if field not in filtered]

    if missing:
        meta_log: Dict[str, Any] = {
            "level": level,
            "missing_fields": tuple(missing),
            "provided_fields": tuple(sorted(filtered.keys())),
        }
        for required in _REQUIRED_FIELDS:
            meta_log.setdefault(required, filtered.get(required, "missing"))
        _logger.bind().warning("logger.missing_required_fields", **meta_log)
        for field in missing:
            filtered[field] = "missing"

    return _logger.bind(**filtered)


def debug(msg: str, **kwargs: Any) -> None:
    _bind_request("debug", **kwargs).debug(msg)


def info(msg: str, **kwargs: Any) -> None:
    _bind_request("info", **kwargs).info(msg)


def warning(msg: str, **kwargs: Any) -> None:
    _bind_request("warning", **kwargs).warning(msg)


def error(msg: str, **kwargs: Any) -> None:
    _bind_request("error", **kwargs).error(msg)


def exception(msg: str, **kwargs: Any) -> None:
    _bind_request("exception", **kwargs).exception(msg)


__all__ = ["debug", "info", "warning", "error", "exception"]
