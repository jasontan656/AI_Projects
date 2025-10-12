from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Any

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

try:
    import orjson  # type: ignore
except Exception:  # pragma: no cover
    orjson = None  # type: ignore

from .models import ChatMessage, KnowledgeSlice, Thread

logger = logging.getLogger(__name__)


async def parse_telegram_export(
    path: str,
    chat_id: str,
    since: str | None = None,
    until: str | None = None,
) -> list[ChatMessage]:
    """Parse Telegram export (HTML/JSON) and return ChatMessage list.

    Parameters:
        path: Path to an exported HTML or JSON file.
        chat_id: Channel or group identifier used for normalization.
        since: Optional ISO date (YYYY-MM-DD) lower bound.
        until: Optional ISO date (YYYY-MM-DD) upper bound.

    Returns:
        A list of ChatMessage objects in ascending chronological order.

    Raises:
        FileNotFoundError: When the file does not exist.
        ValueError: When format is not supported or malformed.
    """
    logger.info("parse_telegram_export: start", extra={"path": path, "chat_id": chat_id})

    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(path)

    # 允许传入“导出目录”：自动定位典型 JSON 文件（result.json / messages*.json）
    if file.is_dir():
        # 优先使用聚合文件，其次直接扫描 messages*.json
        agg = None
        for name in ("result.json", "ExportedData.json"):
            p = file / name
            if p.exists():
                agg = p
                break
        if agg is not None:
            logger.info("parse_telegram_export: found aggregator", extra={"file": str(agg)})
            try:
                raw_any: Any = json.loads(agg.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(raw_any, dict) and isinstance(raw_any.get("chats"), dict) and isinstance(raw_any["chats"].get("list"), list):
                    # 聚合格式：递归扫描目录下的 messages*.json 并合并
                    for jf in sorted(file.rglob("*messages*.json")):
                        try:
                            sub_raw = json.loads(jf.read_text(encoding="utf-8", errors="ignore"))
                        except Exception:
                            continue
                        items: list[Any] | None = None
                        if isinstance(sub_raw, dict) and "messages" in sub_raw:
                            items = sub_raw.get("messages") or []
                        elif isinstance(sub_raw, list):
                            items = sub_raw
                        else:
                            continue
                        for item in items:
                            try:
                                created: datetime | None = None
                                if isinstance(item, dict):
                                    if item.get("created_at"):
                                        created = datetime.fromisoformat(str(item["created_at"]))
                                    elif item.get("date"):
                                        created = datetime.fromisoformat(str(item["date"]).replace("Z", "+00:00"))
                                    elif item.get("date_unixtime"):
                                        created = datetime.utcfromtimestamp(int(item["date_unixtime"]))
                                if created is None:
                                    continue
                                if since_dt and created < since_dt:
                                    continue
                                if until_dt and created > until_dt:
                                    continue
                                msg_id = (item.get("id") if isinstance(item, dict) else None) or len(messages) + 1  # type: ignore[attr-defined]
                                sender = str((item.get("sender") if isinstance(item, dict) else None) or (item.get("from") if isinstance(item, dict) else None) or (item.get("author") if isinstance(item, dict) else None) or "unknown")
                                # 复用下方 _normalize_text，临时内联以避免循环依赖
                                val = (item.get("text") if isinstance(item, dict) else None)
                                if isinstance(val, str):
                                    text_val = val
                                elif isinstance(val, list):
                                    parts: list[str] = []
                                    for x in val:
                                        if isinstance(x, str):
                                            parts.append(x)
                                        elif isinstance(x, dict):
                                            t = x.get("text")
                                            parts.append(t if isinstance(t, str) else str(t))
                                        else:
                                            parts.append(str(x))
                                    text_val = " ".join(parts).strip()
                                else:
                                    text_val = str(val) if val is not None else ""
                                messages.append(
                                    ChatMessage(
                                        message_id=str(msg_id),
                                        chat_id=chat_id,
                                        sender=sender,
                                        text=text_val,
                                        created_at=created,
                                        reply_to=(item.get("reply_to_message_id") if isinstance(item, dict) else None),
                                        media=None,
                                    )
                                )
                            except Exception:
                                continue
                    messages.sort(key=lambda m: m.created_at)
                    logger.info("parse_telegram_export: aggregated", extra={"count": len(messages)})
                    return messages
            except Exception:  # 如果解析聚合失败，继续走普通路径
                pass

        # 未发现聚合或解析失败：选择一个最可能的 JSON 文件
        candidates: list[Path] = []
        candidates += sorted(file.glob("*messages*.json"))
        for name in ("result.json", "ExportedData.json"):
            p = file / name
            if p.exists():
                candidates.append(p)
        candidates += sorted(file.glob("*.json"))
        if not candidates:
            raise ValueError(f"No JSON files found under directory: {file}")
        file = candidates[0]
        logger.info("parse_telegram_export: resolved directory to file", extra={"file": str(file)})

    # Parse time boundaries
    def _parse_date(d: str | None) -> datetime | None:
        if not d:
            return None
        return datetime.fromisoformat(d)

    since_dt = _parse_date(since)
    until_dt = _parse_date(until)

    messages: list[ChatMessage] = []

    if file.suffix.lower() == ".json":
        text = file.read_text(encoding="utf-8", errors="ignore")
        raw: Any = json.loads(text)

        # 如果是聚合 result.json（含 chats.list），优先直接解析内嵌的 messages 列表；
        # 如缺失内嵌 messages 再回退到扫描子目录 messages*.json / messages*.html。
        if isinstance(raw, dict) and isinstance(raw.get("chats"), dict) and isinstance(raw["chats"].get("list"), list):
            def _parse_chat_messages(chat_obj: Any) -> int:
                count_before = len(messages)
                msgs = chat_obj.get("messages") if isinstance(chat_obj, dict) else None
                if isinstance(msgs, list):
                    for item in msgs:
                        try:
                            created: datetime | None = None
                            if isinstance(item, dict):
                                if item.get("created_at"):
                                    created = datetime.fromisoformat(str(item["created_at"]))
                                elif item.get("date"):
                                    created = datetime.fromisoformat(str(item["date"]).replace("Z", "+00:00"))
                                elif item.get("date_unixtime"):
                                    created = datetime.utcfromtimestamp(int(item["date_unixtime"]))
                            if created is None:
                                continue
                            if since_dt and created < since_dt:
                                continue
                            if until_dt and created > until_dt:
                                continue
                            msg_id = (item.get("id") if isinstance(item, dict) else None) or len(messages) + 1  # type: ignore[attr-defined]
                            sender = str((item.get("sender") if isinstance(item, dict) else None) or (item.get("from") if isinstance(item, dict) else None) or (item.get("author") if isinstance(item, dict) else None) or "unknown")
                            val = (item.get("text") if isinstance(item, dict) else None)
                            if isinstance(val, str):
                                text_val = val
                            elif isinstance(val, list):
                                parts: list[str] = []
                                for x in val:
                                    if isinstance(x, str):
                                        parts.append(x)
                                    elif isinstance(x, dict):
                                        t = x.get("text")
                                        parts.append(t if isinstance(t, str) else str(t))
                                    else:
                                        parts.append(str(x))
                                text_val = " ".join(parts).strip()
                            else:
                                text_val = str(val) if val is not None else ""
                            messages.append(
                                ChatMessage(
                                    message_id=str(msg_id),
                                    chat_id=chat_id,
                                    sender=sender,
                                    text=text_val,
                                    created_at=created,
                                    reply_to=(item.get("reply_to_message_id") if isinstance(item, dict) else None),
                                    media=None,
                                )
                            )
                        except Exception:
                            continue
                return len(messages) - count_before

            chats_list = raw["chats"]["list"]
            total_added = 0
            for chat in chats_list:
                total_added += _parse_chat_messages(chat)
            # 同时兼容 left_chats（已退出的聊天）
            left = raw.get("left_chats")
            if isinstance(left, dict) and isinstance(left.get("list"), list):
                for chat in left["list"]:
                    total_added += _parse_chat_messages(chat)
            if total_added > 0:
                messages.sort(key=lambda m: m.created_at)
                return messages
            base_dir = file.parent
            # 先扫描 JSON
            for jf in sorted(base_dir.rglob("*messages*.json")):
                try:
                    sub_raw = json.loads(jf.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    continue
                items: list[Any] | None = None
                if isinstance(sub_raw, dict) and "messages" in sub_raw:
                    items = sub_raw.get("messages") or []
                elif isinstance(sub_raw, list):
                    items = sub_raw
                else:
                    continue
                for item in items:
                    try:
                        created: datetime | None = None
                        if isinstance(item, dict):
                            if item.get("created_at"):
                                created = datetime.fromisoformat(str(item["created_at"]))
                            elif item.get("date"):
                                created = datetime.fromisoformat(str(item["date"]).replace("Z", "+00:00"))
                            elif item.get("date_unixtime"):
                                created = datetime.utcfromtimestamp(int(item["date_unixtime"]))
                        if created is None:
                            continue
                        if since_dt and created < since_dt:
                            continue
                        if until_dt and created > until_dt:
                            continue
                        msg_id = (item.get("id") if isinstance(item, dict) else None) or len(messages) + 1  # type: ignore[attr-defined]
                        sender = str((item.get("sender") if isinstance(item, dict) else None) or (item.get("from") if isinstance(item, dict) else None) or (item.get("author") if isinstance(item, dict) else None) or "unknown")
                        val = (item.get("text") if isinstance(item, dict) else None)
                        if isinstance(val, str):
                            text_val = val
                        elif isinstance(val, list):
                            parts: list[str] = []
                            for x in val:
                                if isinstance(x, str):
                                    parts.append(x)
                                elif isinstance(x, dict):
                                    t = x.get("text")
                                    parts.append(t if isinstance(t, str) else str(t))
                                else:
                                    parts.append(str(x))
                            text_val = " ".join(parts).strip()
                        else:
                            text_val = str(val) if val is not None else ""
                        messages.append(
                            ChatMessage(
                                message_id=str(msg_id),
                                chat_id=chat_id,
                                sender=sender,
                                text=text_val,
                                created_at=created,
                                reply_to=(item.get("reply_to_message_id") if isinstance(item, dict) else None),
                                media=None,
                            )
                        )
                    except Exception:
                        continue
            # 若内嵌 messages 缺失：再扫描 HTML（如果 bs4 可用）
            if BeautifulSoup is not None:
                for hf in sorted(base_dir.rglob("*messages*.html")):
                    try:
                        html = hf.read_text(encoding="utf-8", errors="ignore")
                        soup = BeautifulSoup(html, "lxml")
                    except Exception:
                        continue
                    for elem in soup.select(".message"):
                        try:
                            mid = elem.get("id") or elem.select_one(".body") and elem.select_one(".body").get("id")
                            sender = (elem.select_one(".from_name") or {}).get_text(" ").strip()  # type: ignore[union-attr]
                            text = (elem.select_one(".text") or {}).get_text(" ").strip()  # type: ignore[union-attr]
                            date_elem = elem.select_one(".date") or elem.select_one(".date.details")
                            date_attr = date_elem.get("title") if date_elem else None
                            created = datetime.fromisoformat(date_attr.replace(" ", "T")) if date_attr else datetime.utcnow()
                        except Exception:
                            continue
                        if since_dt and created < since_dt:
                            continue
                        if until_dt and created > until_dt:
                            continue
                        messages.append(
                            ChatMessage(
                                message_id=str(mid or len(messages) + 1),
                                chat_id=chat_id,
                                sender=sender or "unknown",
                                text=text or "",
                                created_at=created,
                            )
                        )
            messages.sort(key=lambda m: m.created_at)
            return messages

        # Telegram Desktop 单文件：顶层为 dict(messages) 或 list
        if isinstance(raw, dict) and "messages" in raw:
            items = raw.get("messages") or []
        elif isinstance(raw, list):
            items = raw
        else:
            raise ValueError("Unsupported JSON; expected a list or an object with 'messages'.")

        def _normalize_text(val: Any) -> str:
            if isinstance(val, str):
                return val
            if isinstance(val, list):
                parts: list[str] = []
                for x in val:
                    if isinstance(x, str):
                        parts.append(x)
                    elif isinstance(x, dict):
                        t = x.get("text")
                        if isinstance(t, str):
                            parts.append(t)
                        else:
                            parts.append(str(t))
                    else:
                        parts.append(str(x))
                return " ".join(parts).strip()
            return str(val) if val is not None else ""

        for item in items:
            try:
                created: datetime | None = None
                if isinstance(item, dict):
                    if item.get("created_at"):
                        created = datetime.fromisoformat(str(item["created_at"]))
                    elif item.get("date"):
                        # 兼容带时区的 ISO 格式
                        created = datetime.fromisoformat(str(item["date"]).replace("Z", "+00:00"))
                    elif item.get("date_unixtime"):
                        created = datetime.utcfromtimestamp(int(item["date_unixtime"]))
                if created is None:
                    # 无法解析时间则跳过（保持稳健）
                    continue
            except Exception:  # pragma: no cover - robustness
                continue

            if since_dt and created < since_dt:
                continue
            if until_dt and created > until_dt:
                continue

            msg_id = None
            sender = "unknown"
            text_val: str | None = None
            reply_to = None
            if isinstance(item, dict):
                msg_id = item.get("id") or item.get("message_id")
                sender = str(item.get("sender") or item.get("from") or item.get("author") or "unknown")
                text_val = _normalize_text(item.get("text"))
                reply_to = item.get("reply_to_message_id")

            messages.append(
                ChatMessage(
                    message_id=str(msg_id or len(messages) + 1),
                    chat_id=chat_id,
                    sender=sender,
                    text=text_val,
                    created_at=created,
                    reply_to=reply_to,
                    media=None,
                )
            )
    elif file.suffix.lower() in {".html", ".htm"}:
        if BeautifulSoup is None:
            raise ValueError("bs4 is required to parse HTML exports")
        html = file.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "lxml")
        for elem in soup.select(".message"):  # telegram export default class
            try:
                mid = elem.get("id") or elem.select_one(".body") and elem.select_one(".body").get("id")
                sender = (elem.select_one(".from_name") or {}).get_text(" ").strip()  # type: ignore[union-attr]
                text = (elem.select_one(".text") or {}).get_text(" ").strip()  # type: ignore[union-attr]
                date_elem = elem.select_one(".date") or elem.select_one(".date.details")
                date_attr = date_elem.get("title") if date_elem else None
                created = datetime.fromisoformat(date_attr.replace(" ", "T")) if date_attr else datetime.utcnow()
            except Exception:  # pragma: no cover
                continue
            if since_dt and created < since_dt:
                continue
            if until_dt and created > until_dt:
                continue
            messages.append(
                ChatMessage(
                    message_id=str(mid or len(messages) + 1),
                    chat_id=chat_id,
                    sender=sender or "unknown",
                    text=text or "",
                    created_at=created,
                )
            )
    else:
        raise ValueError(f"Unsupported file type: {file.suffix}")

    messages.sort(key=lambda m: m.created_at)
    logger.info("parse_telegram_export: done", extra={"count": len(messages)})
    return messages


async def build_knowledge_slices(threads: list[Thread]) -> list[KnowledgeSlice]:
    """Build knowledge slices from conversation threads using LLM prompts.

    Implementation detail: prompt templates are defined in prompts/*.md as per
    Tech_Decisions.md §2.2; this function focuses on orchestration and JSON
    parsing, not on embedding the prompt content.
    """
    logger.info("build_knowledge_slices: start", extra={"threads": len(threads)})
    # Minimal placeholder implementation; real implementation would call LLM and
    # honor batching/ratelimiting from Tech_Decisions.md §2.
    slices: list[KnowledgeSlice] = []
    now = datetime.utcnow()
    for i, th in enumerate(threads, start=1):
        sid = f"S{i:06d}"
        slices.append(
            KnowledgeSlice(
                slice_id=sid,
                title=(th.topic or "Untitled Topic")[:80],
                summary="Auto-generated placeholder summary.",
                tags=[],
                sources=th.message_ids[:10],
                created_at=now,
            )
        )
    logger.info("build_knowledge_slices: done", extra={"slices": len(slices)})
    return slices
