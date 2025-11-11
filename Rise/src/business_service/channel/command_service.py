from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from business_service.channel.events import ChannelBindingEvent
from business_service.channel.models import ChannelBindingOption
from business_service.channel.registry import ChannelBindingRegistry
from business_service.channel.service import WorkflowChannelService
from foundational_service.messaging.channel_binding_event_publisher import (
    ChannelBindingEventPublisher,
    PublishResult,
)


@dataclass(slots=True)
class BindingCommandOutcome:
    option: ChannelBindingOption
    warnings: Sequence[str]


class ChannelBindingCommandService:
    """Application-layer command helper for channel binding mutations."""

    def __init__(
        self,
        *,
        service: WorkflowChannelService,
        registry: ChannelBindingRegistry,
        publisher: Optional[ChannelBindingEventPublisher],
    ) -> None:
        self._service = service
        self._registry = registry
        self._publisher = publisher

    async def list_options(self, channel: str = "telegram") -> Sequence[ChannelBindingOption]:
        try:
            return await self._registry.get_options(channel)
        except Exception:
            return await self._service.list_binding_options(channel)

    async def get_binding(self, workflow_id: str, channel: str = "telegram") -> ChannelBindingOption:
        return await self._service.get_binding_view(workflow_id, channel)

    async def upsert_binding(
        self,
        workflow_id: str,
        *,
        channel: str = "telegram",
        enabled: bool,
        config: Optional[Mapping[str, object]],
        actor: str,
    ) -> BindingCommandOutcome:
        operation = "delete"
        policy = None
        if enabled:
            if config is None:
                raise ValueError("config is required when enabling channel binding")
            operation = "upsert"
            policy = await self._service.save_policy(
                workflow_id,
                config,
                actor=actor,
                channel=channel,
            )
            await self._service.set_channel_enabled(workflow_id, channel, enabled=True, actor=actor)
        else:
            try:
                await self._service.delete_policy(workflow_id, channel)
            except KeyError:
                pass
            await self._service.set_channel_enabled(workflow_id, channel, enabled=False, actor=actor)
            await self._service.set_kill_switch_state(workflow_id, channel, active=True, actor=actor)

        state = await self._registry.refresh(channel, workflow_id=workflow_id)
        option = state.options.get(workflow_id) if state else None
        if option is None:
            option = await self._service.get_binding_view(workflow_id, channel)
        publish_result = await self._publish_event(
            ChannelBindingEvent(
                channel=channel,
                workflow_id=workflow_id,
                operation=operation,
                binding_version=state.version if state else 0,
                published_version=option.published_version if option else 0,
                enabled=enabled,
                secret_version=policy.secret_version if policy else None,
                actor=actor,
            )
        )
        return BindingCommandOutcome(option=option, warnings=self._warnings(publish_result))

    async def set_kill_switch_state(
        self,
        workflow_id: str,
        *,
        channel: str = "telegram",
        active: bool,
        actor: str,
        reason: Optional[str] = None,
    ) -> BindingCommandOutcome:
        await self._service.set_kill_switch_state(
            workflow_id,
            channel,
            active=active,
            actor=actor,
        )
        state = await self._registry.refresh(channel, workflow_id=workflow_id)
        option = state.options.get(workflow_id) if state else None
        if option is None:
            option = await self._service.get_binding_view(workflow_id, channel)
        payload: Mapping[str, object] = {"reason": reason} if reason else {}
        publish_result = await self._publish_event(
            ChannelBindingEvent(
                channel=channel,
                workflow_id=workflow_id,
                operation="kill_switch_on" if active else "kill_switch_off",
                binding_version=state.version if state else 0,
                published_version=option.published_version if option else 0,
                enabled=option.is_enabled if option else False,
                secret_version=option.policy.secret_version if option and option.policy else None,
                actor=actor,
                payload=payload,
            )
        )
        return BindingCommandOutcome(option=option, warnings=self._warnings(publish_result))

    async def refresh_binding(
        self,
        workflow_id: str,
        *,
        channel: str = "telegram",
        actor: str,
    ) -> BindingCommandOutcome:
        state = await self._registry.refresh(channel, workflow_id=workflow_id)
        option = state.options.get(workflow_id) if state else None
        if option is None:
            option = await self._service.get_binding_view(workflow_id, channel)
        publish_result = await self._publish_event(
            ChannelBindingEvent(
                channel=channel,
                workflow_id=workflow_id,
                operation="refresh",
                binding_version=state.version if state else 0,
                published_version=option.published_version if option else 0,
                enabled=option.is_enabled if option else False,
                secret_version=option.policy.secret_version if option and option.policy else None,
                actor=actor,
            )
        )
        return BindingCommandOutcome(option=option, warnings=self._warnings(publish_result))

    async def _publish_event(self, event: ChannelBindingEvent) -> Optional[PublishResult]:
        if self._publisher is None:
            return None
        return await self._publisher.publish(event)

    @staticmethod
    def _warnings(result: Optional[PublishResult]) -> Sequence[str]:
        if result is None:
            return ()
        return tuple(result.warnings)


__all__ = ["ChannelBindingCommandService", "BindingCommandOutcome"]


