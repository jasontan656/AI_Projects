"""
Hub-level router that routes all requests to the orchestrator.
Simplified architecture: all requests go through chat agent with function calling.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Optional

from .models.orchestrator import Orchestrator


class HubRouter:
    """Routes all requests to orchestrator for chat agent processing."""

    def __init__(
        self,
        *,
        orchestrator: Optional[Orchestrator] = None,
        memory_service=None,
        audit_service=None,
        form_service=None,
        llm=None,
    ) -> None:
        if orchestrator is None:
            orchestrator = Orchestrator(
                memory_service=memory_service,
                audit_service=audit_service,
                form_service=form_service,
                llm=llm,
            )
        self.orchestrator = orchestrator

    async def route(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to orchestrator for processing."""
        return await self.orchestrator.run(envelope)

    def stream(self, envelope: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        return self.orchestrator.stream(envelope)


__all__ = ["HubRouter"]
