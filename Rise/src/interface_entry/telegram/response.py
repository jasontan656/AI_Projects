"""
Telegram outbound adapter helpers.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def core_to_telegram_response(
    outbound_contract: Dict[str, Any],
    *,
    text: str,
) -> Dict[str, Any]:
    """
    Transform the outbound adapter contract into arguments suitable for aiogram/Telegram API.
    """
    response: Dict[str, Any] = {
        "chat_id": outbound_contract.get("chat_id"),
        "text": text,
        "parse_mode": outbound_contract.get("parse_mode", "MarkdownV2"),
        "disable_web_page_preview": outbound_contract.get("disable_web_page_preview", True),
    }
    if outbound_contract.get("reply_to_message_id") is not None:
        response["reply_to_message_id"] = outbound_contract["reply_to_message_id"]
    return response


__all__ = ["core_to_telegram_response"]

