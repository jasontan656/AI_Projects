from __future__ import annotations

from datetime import datetime

from Kobe.TelegramCuration.models import ChatMessage, KnowledgeSlice


def test_chat_message_model_minimal():
    msg = ChatMessage(
        message_id="m1",
        chat_id="@c",
        sender="user",
        created_at=datetime.utcnow(),
    )
    assert msg.message_id == "m1"


def test_knowledge_slice_defaults():
    ks = KnowledgeSlice(slice_id="S1", title="t", summary="s", sources=["m1"])
    assert ks.version == 1
    assert ks.lifecycle in {"draft", "published", "deprecated"}

