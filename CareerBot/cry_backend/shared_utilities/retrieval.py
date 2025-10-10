from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


class LocalRetriever:
    """
    Minimal local retriever to satisfy RAG-first contract without external deps.

    Loads a small corpus from repository docs and does naive keyword scoring.
    """

    def __init__(self) -> None:
        self.corpus: List[Tuple[str, str]] = []  # (source, paragraph)
        self._load_corpus()

    def _load_corpus(self) -> None:
        candidates = [
            Path("project_overview.md"),
            Path("spec-kit-main/memory/constitution.md"),
            Path("specs/001-arguments/contracts/envelope.md"),
        ]
        loaded: List[Tuple[str, str]] = []
        for p in candidates:
            try:
                if p.exists():
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    for para in text.split("\n\n"):
                        chunk = para.strip()
                        if len(chunk) >= 40:
                            loaded.append((str(p), chunk))
            except (OSError, UnicodeError):
                # Fail-safe: ignore unreadable files; retriever can still operate
                continue
        self.corpus = loaded

    def retrieve(self, query: str, *, k: int = 3) -> List[Tuple[str, str]]:
        """Return top-k paragraphs with simple token overlap scoring."""
        q_tokens = {t.lower() for t in query.split() if t and t.isascii()}
        if not q_tokens:
            return []
        scored: List[Tuple[int, Tuple[str, str]]] = []
        for item in self.corpus:
            _, para = item
            p_tokens = {t.lower() for t in para.split() if t and t.isascii()}
            score = len(q_tokens & p_tokens)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:k]]

__all__ = ["LocalRetriever"]
