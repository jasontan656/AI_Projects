import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from foundational_service.messaging.channel_binding_event_publisher import WebhookCredentialRotatedEvent
from foundational_service.observability.public_endpoint_probe import (
    CertificateStatus,
    PublicEndpointSecurityProbe,
)


class _FakePublisher:
    def __init__(self) -> None:
        self.events: list[WebhookCredentialRotatedEvent] = []

    async def publish_webhook_credentials(self, event: WebhookCredentialRotatedEvent):
        self.events.append(event)
        # mimic PublishResult
        class _Result:
            status = "sent"

            warnings: tuple[str, ...] = ()

        return _Result()


def _certificate_fetcher_factory(days: int) -> CertificateStatus:
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    return CertificateStatus(
        status="available",
        expires_at=expires_at,
        days_remaining=days,
        issuer="CN=test",
        subject="CN=test",
    )


@pytest.mark.asyncio
async def test_secret_uniqueness_in_memory():
    probe = PublicEndpointSecurityProbe(
        redis=None,
        certificate_fetcher=lambda url: _certificate_fetcher_factory(30),
    )
    snapshot_first = await probe.inspect(
        workflow_id="wf-1",
        channel="telegram",
        endpoint="https://example.com",
        secret="secret-value",
    )
    assert snapshot_first.secret.is_unique
    assert snapshot_first.secret.conflicts == ()

    snapshot_second = await probe.inspect(
        workflow_id="wf-2",
        channel="telegram",
        endpoint="https://example.com",
        secret="secret-value",
    )
    assert not snapshot_second.secret.is_unique
    assert snapshot_second.secret.conflicts == ("wf-1",)


@pytest.mark.asyncio
async def test_rotation_event_emitted_on_secret_change():
    publisher = _FakePublisher()
    probe = PublicEndpointSecurityProbe(
        redis=None,
        certificate_fetcher=lambda url: _certificate_fetcher_factory(45),
        publisher=publisher,
    )
    await probe.inspect(
        workflow_id="wf-1",
        channel="telegram",
        endpoint="https://example.com",
        secret="alpha",
    )
    assert publisher.events == []

    await probe.inspect(
        workflow_id="wf-1",
        channel="telegram",
        endpoint="https://example.com",
        secret="beta",
    )
    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.workflow_id == "wf-1"
    assert event.rotation_type == "secret"
    assert event.secret_fingerprint is not None
