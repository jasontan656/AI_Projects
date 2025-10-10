from __future__ import annotations


class _Monitor:
    def event(self, name: str, **kwargs) -> None:
        # No-op placeholder for monitoring hooks
        return None


monitor = _Monitor()

__all__ = ["monitor"]

