from __future__ import annotations

"""In-memory registry for channel binding runtime snapshots."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence
import weakref

from business_service.channel.events import ChannelBindingEvent
from business_service.channel.models import ChannelBindingOption, ChannelBindingRuntime
from business_service.channel.service import WorkflowChannelService

__all__ = ["ChannelBindingRegistry"]


@dataclass(slots=True)
class _ChannelBindingState:
    options: Dict[str, ChannelBindingOption] = field(default_factory=dict)
    active: Optional[ChannelBindingRuntime] = None
    refreshed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 0


class ChannelBindingRegistry:
    """Cache channel binding information for both HTTP and runtime callers."""

    def __init__(
        self,
        service: WorkflowChannelService,
        *,
        default_channels: Optional[Sequence[str]] = None,
    ) -> None:
        self._service = service
        self._lock = asyncio.Lock()
        self._cache: Dict[str, _ChannelBindingState] = {}
        self._version = 0
        self._defaults = tuple(default_channels or ("telegram",))
        self._dispatchers: "weakref.WeakSet[object]" = weakref.WeakSet()
        self._kill_switch: Dict[str, Dict[str, bool]] = {}

    async def refresh(
        self,
        channel: Optional[str] = None,
        *,
        workflow_id: Optional[str] = None,
        binding_version: Optional[int] = None,
    ) -> _ChannelBindingState:
        if workflow_id and not channel:
            raise ValueError("workflow_id refresh requires channel")
        channels: Iterable[str]
        if channel:
            channels = (channel,)
        else:
            existing = tuple(self._cache.keys())
            channels = existing or self._defaults
        async with self._lock:
            if workflow_id and channel:
                state = await self._refresh_single(channel, workflow_id, binding_version)
                if state is not None:
                    return state
            state: Optional[_ChannelBindingState] = None
            for name in channels:
                state = await self._refresh_channel(name, binding_version)
                if channel and name == channel:
                    break
            return state or self._cache.get(channel or self._defaults[0], _ChannelBindingState())

    async def handle_event(self, event: ChannelBindingEvent) -> None:
        await self.refresh(
            event.channel,
            workflow_id=event.workflow_id,
            binding_version=event.binding_version,
        )

    async def get_active_binding(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        await self._ensure_channel(channel)
        state = self._cache.get(channel)
        return state.active if state else None

    async def get_options(self, channel: str = "telegram") -> Sequence[ChannelBindingOption]:
        await self._ensure_channel(channel)
        state = self._cache.get(channel)
        if state is None:
            return []
        return list(state.options.values())

    def get_state(self, channel: str) -> Optional[_ChannelBindingState]:
        return self._cache.get(channel)

    async def _ensure_channel(self, channel: str) -> None:
        if channel not in self._cache:
            await self.refresh(channel)

    def attach_dispatcher(self, dispatcher: object) -> None:
        self._dispatchers.add(dispatcher)
        self._sync_dispatchers_all()

    def snapshot(self) -> Mapping[str, Mapping[str, object]]:
        """Return a lightweight snapshot for diagnostics."""

        return {
            channel: {
                "activeWorkflowId": state.active.workflow_id if state.active else None,
                "version": state.version,
                "refreshedAt": state.refreshed_at.isoformat(),
                "optionCount": len(state.options),
            }
            for channel, state in self._cache.items()
        }

    def _sync_dispatchers(self, channel: str) -> None:
        state = self._cache.get(channel)
        if state is None:
            return
        payload = {
            "layer": "Interface",
            "version": state.version,
            "active": state.active.workflow_id if state.active else None,
            "options": {
                workflow_id: {
                    "status": option.status,
                    "health": option.health,
                    "killSwitch": option.kill_switch,
                    "policy": option.policy.to_document() if option.policy else None,
                }
                for workflow_id, option in state.options.items()
            },
            "last_refresh": state.refreshed_at.isoformat(),
        }
        for dispatcher in list(self._dispatchers):
            workflow_data = getattr(dispatcher, "workflow_data", None)
            if workflow_data is not None:
                bindings = workflow_data.setdefault("channel_bindings", {})
                bindings[channel] = payload

    def _sync_dispatchers_all(self) -> None:
        for channel in self._cache.keys():
            self._sync_dispatchers(channel)

    @staticmethod
    def _select_active_option(options: Sequence[ChannelBindingOption]) -> Optional[ChannelBindingOption]:
        candidates = [
            option
            for option in options
            if option.policy is not None
            and option.is_enabled
            and not option.kill_switch
            and option.status in {"bound", "degraded"}
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda option: option.updated_at or datetime(1970, 1, 1, tzinfo=timezone.utc),
        )

    async def _refresh_channel(
        self,
        channel: str,
        binding_version: Optional[int],
    ) -> _ChannelBindingState:
        options = await self._service.list_binding_options(channel)
        option_map = {item.workflow_id: item for item in options}
        version = binding_version or self._version + 1
        active_runtime = self._build_active_runtime(channel, options, version)
        state = _ChannelBindingState(
            options=option_map,
            active=active_runtime,
            refreshed_at=datetime.now(timezone.utc),
            version=version,
        )
        self._cache[channel] = state
        self._kill_switch[channel] = {opt.workflow_id: opt.kill_switch for opt in options}
        self._version = max(self._version, version)
        self._sync_dispatchers(channel)
        return state

    async def _refresh_single(
        self,
        channel: str,
        workflow_id: str,
        binding_version: Optional[int],
    ) -> Optional[_ChannelBindingState]:
        state = self._cache.get(channel)
        if state is None:
            return await self._refresh_channel(channel, binding_version)
        try:
            option = await self._service.get_binding_view(workflow_id, channel)
        except KeyError:
            state.options.pop(workflow_id, None)
            if channel in self._kill_switch:
                self._kill_switch[channel].pop(workflow_id, None)
        else:
            state.options[workflow_id] = option
            bucket = self._kill_switch.setdefault(channel, {})
            bucket[workflow_id] = option.kill_switch
        version = binding_version or state.version + 1
        state.version = version
        state.refreshed_at = datetime.now(timezone.utc)
        state.active = self._build_active_runtime(channel, tuple(state.options.values()), version)
        self._cache[channel] = state
        self._version = max(self._version, version)
        self._sync_dispatchers(channel)
        return state

    def _build_active_runtime(
        self,
        channel: str,
        options: Sequence[ChannelBindingOption],
        version: int,
    ) -> Optional[ChannelBindingRuntime]:
        active_option = self._select_active_option(options)
        if active_option and active_option.policy:
            return ChannelBindingRuntime(
                workflow_id=active_option.workflow_id,
                channel=channel,
                policy=active_option.policy,
                version=version,
            )
        return None
