"""LangChain helper utilities."""

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI


def create_chat_model(**kwargs: Any) -> ChatOpenAI:
    """Factory for ChatOpenAI using OPENAI_* environment variables."""
    return ChatOpenAI(**kwargs)


__all__ = ["create_chat_model"]


