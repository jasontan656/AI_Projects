from __future__ import annotations

"""Dispatcher-backed channel binding providers for aiogram runtime."""

from typing import Any, Mapping, Optional, Sequence

from business_service.channel.models import ChannelBindingRuntime, WorkflowChannelPolicy
from business_service.conversation.service import ChannelBindingProvider


class DispatcherChannelBindingProvider(ChannelBindingProvider):
    """Read channel binding snapshots directly from aiogram dispatcher workflow_data."""

    def __init__(self, dispatcher: Any) -> None:
        self._dispatcher = dispatcher

    async def get_active_binding(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        snapshot = self._get_channel_snapshot(channel)
        if not snapshot:
            return None
        workflow_id = snapshot.get("active")
        if not workflow_id:
            return None
        option = self._resolve_option(snapshot, workflow_id)
        if option is None:
            return None
        policy_doc = option.get("policy")
        if not policy_doc:
            return None
        policy = WorkflowChannelPolicy.from_document(policy_doc)
        return ChannelBindingRuntime(
            workflow_id=policy.workflow_id,
            channel=channel,
            policy=policy,
            version=int(snapshot.get("version") or 0),
        )

    async def refresh(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        # Dispatcher data is already refreshed by registry events; just return the current snapshot.
        return await self.get_active_binding(channel)

    def _get_channel_snapshot(self, channel: str) -> Optional[dict[str, Any]]:
        workflow_data = getattr(self._dispatcher, "workflow_data", None) or {}
        bindings = workflow_data.get("channel_bindings") or {}
        snapshot = bindings.get(channel)
        if isinstance(snapshot, dict):
            return snapshot
        return None

    @staticmethod
    def _resolve_option(snapshot: Mapping[str, Any], workflow_id: str) -> Optional[Mapping[str, Any]]:
        options = snapshot.get("options")
        if isinstance(options, dict):
            option = options.get(workflow_id)
            if isinstance(option, dict):
                return option
        return None


class CompositeChannelBindingProvider(ChannelBindingProvider):
    """Try multiple providers in order, returning the first successful binding."""

    def __init__(self, *providers: ChannelBindingProvider) -> None:
        self._providers: Sequence[ChannelBindingProvider] = tuple(
            provider for provider in providers if provider is not None
        )

    async def get_active_binding(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        for provider in self._providers:
            result = await provider.get_active_binding(channel)
            if result is not None:
                return result
        return None

    async def refresh(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        refreshed: Optional[ChannelBindingRuntime] = None
        for provider in self._providers:
            refresh = getattr(provider, "refresh", None)
            if refresh is None:
                continue
            try:
                candidate = await refresh(channel)
            except TypeError:
                candidate = await refresh()
            if candidate is not None:
                refreshed = candidate
        return refreshed
