from __future__ import annotations

"""Async Telegram Bot API client with domain-specific error mapping."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional

import httpx

__all__ = ["TelegramClient", "TelegramClientError"]

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = 5.0


@dataclass(slots=True)
class TelegramClientError(RuntimeError):
    code: str
    message: str
    trace_id: str
    status_code: Optional[int] = None


class TelegramClient:
    def __init__(self, *, base_url: str = TELEGRAM_API_BASE, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_bot_info(self, token: str, *, trace_id: str) -> Mapping[str, Any]:
        return await self._request(token, "getMe", trace_id=trace_id)

    async def get_webhook_info(self, token: str, *, trace_id: str) -> Mapping[str, Any]:
        return await self._request(token, "getWebhookInfo", trace_id=trace_id)

    async def send_message(
        self,
        token: str,
        *,
        chat_id: str,
        text: str,
        parse_mode: Optional[str],
        trace_id: str,
    ) -> Mapping[str, Any]:
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return await self._request(token, "sendMessage", payload=payload, trace_id=trace_id)

    async def _request(
        self,
        token: str,
        method: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        trace_id: str,
    ) -> Mapping[str, Any]:
        url = f"{self._base_url}/bot{token}/{method}"
        try:
            response = await self._client.post(url, json=payload or {})
        except httpx.RequestError as exc:
            raise TelegramClientError(
                code="NETWORK_FAILURE",
                message=str(exc),
                trace_id=trace_id,
            ) from exc
        if response.status_code >= 400:
            raise self._map_http_error(response, trace_id)
        data = response.json()
        if not data.get("ok"):
            raise TelegramClientError(
                code="TELEGRAM_ERROR",
                message=str(data.get("description") or "telegram api error"),
                trace_id=trace_id,
                status_code=response.status_code,
            )
        return data.get("result") or {}

    @staticmethod
    def _map_http_error(response: httpx.Response, trace_id: str) -> TelegramClientError:
        description = ""
        try:
            payload = response.json()
            description = payload.get("description") or ""
        except Exception:
            description = response.text
        code = "TELEGRAM_ERROR"
        if response.status_code == 401 or "unauthorized" in description.lower():
            code = "BOT_FORBIDDEN"
        elif response.status_code == 403:
            code = "BOT_FORBIDDEN"
        elif response.status_code == 429:
            code = "RATE_LIMIT"
        elif response.status_code == 400 and "chat not found" in description.lower():
            code = "CHAT_NOT_FOUND"
        return TelegramClientError(
            code=code,
            message=description or f"telegram error {response.status_code}",
            trace_id=trace_id,
            status_code=response.status_code,
        )
