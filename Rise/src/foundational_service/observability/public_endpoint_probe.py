from __future__ import annotations

"""Webhook security observability helpers (secret uniqueness + TLS expiry)."""

import asyncio
import hashlib
import logging
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from redis.asyncio import Redis

from foundational_service.messaging.channel_binding_event_publisher import (
    ChannelBindingEventPublisher,
    WebhookCredentialRotatedEvent,
)
from project_utility.db.redis import get_async_redis
from project_utility.telemetry import emit as telemetry_emit

__all__ = [
    "CertificateStatus",
    "SecretStatus",
    "WebhookSecuritySnapshot",
    "PublicEndpointSecurityProbe",
]


SECRET_FINGERPRINT_HASH = "rise:webhook_security:fingerprints"
SECRET_INDEX_PREFIX = "rise:webhook_security:index:"


@dataclass(slots=True)
class CertificateStatus:
    status: str
    expires_at: Optional[datetime]
    days_remaining: Optional[int]
    issuer: Optional[str] = None
    subject: Optional[str] = None
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            "daysRemaining": self.days_remaining,
            "issuer": self.issuer,
            "subject": self.subject,
            "detail": self.detail,
        }


@dataclass(slots=True)
class SecretStatus:
    fingerprint: Optional[str]
    is_unique: bool
    conflicts: Sequence[str] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "isUnique": self.is_unique,
            "conflicts": list(self.conflicts),
        }


@dataclass(slots=True)
class WebhookSecuritySnapshot:
    workflow_id: str
    channel: str
    endpoint: str
    checked_at: datetime
    certificate: CertificateStatus
    secret: SecretStatus

    def to_dict(self) -> Dict[str, object]:
        return {
            "workflowId": self.workflow_id,
            "channel": self.channel,
            "endpoint": self.endpoint,
            "checkedAt": self.checked_at.isoformat(),
            "certificate": self.certificate.to_dict(),
            "secret": self.secret.to_dict(),
        }


class _SecretRegistry:
    """Track secret fingerprints in Redis with in-memory fallback."""

    def __init__(self, redis: Optional[Redis], logger: logging.Logger) -> None:
        self._redis = redis
        self._logger = logger
        self._local_fingerprints: Dict[str, str] = {}
        self._local_index: Dict[str, set[str]] = {}

    async def register(self, workflow_id: str, fingerprint: Optional[str]) -> Sequence[str]:
        if self._redis is None:
            return self._register_local(workflow_id, fingerprint)
        try:
            return await self._register_redis(workflow_id, fingerprint)
        except Exception as exc:  # pragma: no cover - fallback path
            self._logger.warning(
                "webhook_security.secret_registry.redis_failed",
                extra={"error": str(exc)},
            )
            return self._register_local(workflow_id, fingerprint)

    async def release(self, workflow_id: str) -> None:
        await self.register(workflow_id, None)

    async def _register_redis(self, workflow_id: str, fingerprint: Optional[str]) -> Sequence[str]:
        redis = self._redis
        if redis is None:
            return ()
        previous = await redis.hget(SECRET_FINGERPRINT_HASH, workflow_id)
        previous_fp = previous.decode("utf-8") if isinstance(previous, (bytes, bytearray)) else previous
        if previous_fp and previous_fp != fingerprint:
            await redis.srem(self._index_key(previous_fp), workflow_id)
            if await redis.scard(self._index_key(previous_fp)) == 0:
                await redis.delete(self._index_key(previous_fp))
        if not fingerprint:
            await redis.hdel(SECRET_FINGERPRINT_HASH, workflow_id)
            return ()
        await redis.hset(SECRET_FINGERPRINT_HASH, mapping={workflow_id: fingerprint})
        await redis.sadd(self._index_key(fingerprint), workflow_id)
        members = await redis.smembers(self._index_key(fingerprint))
        decoded = sorted(
            member.decode("utf-8") if isinstance(member, (bytes, bytearray)) else str(member)
            for member in members
        )
        return tuple(wf for wf in decoded if wf != workflow_id)

    def _register_local(self, workflow_id: str, fingerprint: Optional[str]) -> Sequence[str]:
        previous = self._local_fingerprints.get(workflow_id)
        if previous and previous != fingerprint:
            self._local_index.setdefault(previous, set()).discard(workflow_id)
            if not self._local_index[previous]:
                self._local_index.pop(previous, None)
        if not fingerprint:
            self._local_fingerprints.pop(workflow_id, None)
            return ()
        self._local_fingerprints[workflow_id] = fingerprint
        holder = self._local_index.setdefault(fingerprint, set())
        holder.add(workflow_id)
        conflicts = sorted(holder - {workflow_id})
        return tuple(conflicts)

    @staticmethod
    def _index_key(fingerprint: str) -> str:
        return f"{SECRET_INDEX_PREFIX}{fingerprint}"


class PublicEndpointSecurityProbe:
    """Evaluate webhook TLS expiry and secret uniqueness."""

    def __init__(
        self,
        *,
        redis: Optional[Redis] = None,
        logger: Optional[logging.Logger] = None,
        publisher: Optional[ChannelBindingEventPublisher] = None,
        certificate_fetcher: Optional[Callable[[str], CertificateStatus]] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("observability.webhook_security")
        self._redis = redis
        self._registry = _SecretRegistry(redis, self._logger)
        self._publisher = publisher
        self._certificate_fetcher = certificate_fetcher or (
            lambda url: PublicEndpointSecurityProbe._fetch_certificate_status(url)
        )
        self._snapshots: Dict[Tuple[str, str], WebhookSecuritySnapshot] = {}
        self._lock = asyncio.Lock()

    async def inspect(
        self,
        *,
        workflow_id: str,
        channel: str,
        endpoint: str,
        secret: Optional[str],
    ) -> WebhookSecuritySnapshot:
        fingerprint = self._fingerprint(secret) if secret else None
        conflicts = await self._registry.register(workflow_id, fingerprint)
        secret_status = SecretStatus(
            fingerprint=fingerprint,
            is_unique=not conflicts,
            conflicts=conflicts,
        )
        certificate_status = await asyncio.to_thread(self._certificate_fetcher, endpoint)
        snapshot = WebhookSecuritySnapshot(
            workflow_id=workflow_id,
            channel=channel,
            endpoint=endpoint,
            checked_at=datetime.now(timezone.utc),
            certificate=certificate_status,
            secret=secret_status,
        )
        await self._handle_snapshot(snapshot)
        return snapshot

    async def _handle_snapshot(self, snapshot: WebhookSecuritySnapshot) -> None:
        key = (snapshot.workflow_id, snapshot.channel)
        previous = self._snapshots.get(key)
        self._snapshots[key] = snapshot
        if previous is None:
            return
        rotation = self._rotation_type(previous, snapshot)
        if rotation is None:
            return
        if self._publisher is None:
            return
        event = WebhookCredentialRotatedEvent(
            workflow_id=snapshot.workflow_id,
            channel=snapshot.channel,
            rotation_type=rotation,
            secret_fingerprint=snapshot.secret.fingerprint,
            certificate_expires_at=(
                snapshot.certificate.expires_at.isoformat()
                if snapshot.certificate.expires_at
                else None
            ),
        )
        try:
            await self._publisher.publish_webhook_credentials(event)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning(
                "webhook_security.publish_rotation_failed",
                extra={"error": str(exc)},
            )

    @staticmethod
    def _rotation_type(
        previous: WebhookSecuritySnapshot,
        current: WebhookSecuritySnapshot,
    ) -> Optional[str]:
        secret_changed = previous.secret.fingerprint != current.secret.fingerprint
        cert_changed = (previous.certificate.expires_at != current.certificate.expires_at) or (
            previous.certificate.status != current.certificate.status
        )
        if secret_changed and cert_changed:
            return "both"
        if secret_changed:
            return "secret"
        if cert_changed:
            return "certificate"
        return None

    @staticmethod
    def _fingerprint(secret: str) -> str:
        digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        return digest

    @staticmethod
    def _fetch_certificate_status(endpoint: str) -> CertificateStatus:
        parsed = urlparse(endpoint)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return CertificateStatus(status="unavailable", expires_at=None, days_remaining=None, detail="invalid_url")
        if parsed.scheme != "https":
            return CertificateStatus(status="unavailable", expires_at=None, days_remaining=None, detail="not_https")
        context = ssl.create_default_context()
        try:
            with socket.create_connection((host, port), timeout=3.0) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
        except Exception as exc:
            return CertificateStatus(
                status="unavailable",
                expires_at=None,
                days_remaining=None,
                detail=str(exc),
            )
        not_after = cert.get("notAfter")
        expires_at = (
            datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            if not_after
            else None
        )
        days_remaining: Optional[int] = None
        if expires_at:
            delta = expires_at - datetime.now(timezone.utc)
            days_remaining = max(0, int(delta.total_seconds() // 86400))
        issuer = _flatten_subject(cert.get("issuer"))
        subject = _flatten_subject(cert.get("subject"))
        status = "available"
        detail = None
        if days_remaining is not None and days_remaining < 14:
            status = "degraded"
            detail = "certificate_expiring_soon"
        return CertificateStatus(
            status=status,
            expires_at=expires_at,
            days_remaining=days_remaining,
            issuer=issuer,
            subject=subject,
            detail=detail,
        )


def _flatten_subject(value: Optional[Iterable[Iterable[Tuple[str, str]]]]) -> Optional[str]:
    if not value:
        return None
    parts: List[str] = []
    for rdn in value:
        if not isinstance(rdn, Iterable):
            continue
        for key, val in rdn:
            parts.append(f"{key}={val}")
    return ", ".join(parts) if parts else None


async def build_security_probe(
    *,
    logger: Optional[logging.Logger] = None,
    publisher: Optional[ChannelBindingEventPublisher] = None,
) -> PublicEndpointSecurityProbe:
    redis = get_async_redis()
    return PublicEndpointSecurityProbe(redis=redis, logger=logger, publisher=publisher)
