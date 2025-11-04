"""Prompt registry loader for foundational services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from foundational_service.policy.paths import get_shared_config_root

__all__ = ["PromptEntry", "PromptRegistry", "PROMPT_REGISTRY"]


@dataclass(slots=True)
class PromptEntry:
    prompt_id: str
    locale: str
    audience: str
    text: str
    variables: Dict[str, Dict[str, Any]]

    def render(self, **values: Any) -> str:
        merged: Dict[str, Any] = {}
        for name, meta in self.variables.items():
            default = meta.get("default")
            if name in values:
                merged[name] = values[name]
            elif default is not None:
                merged[name] = default
            elif not meta.get("required", False):
                merged[name] = ""
            else:
                raise KeyError(f"missing required variable {name} for {self.prompt_id}")
        for key, value in values.items():
            if key not in merged:
                merged[key] = value
        return self.text.format(**merged)


class PromptRegistry:
    def __init__(self, base_dir: Path) -> None:
        self._entries: Dict[str, PromptEntry] = {}
        if not base_dir.exists():
            return
        for path in sorted(base_dir.glob("prompts.*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for prompt_id, payload in data.items():
                if prompt_id == "metadata":
                    continue
                entry = PromptEntry(
                    prompt_id=prompt_id,
                    locale=payload.get("locale", "en-US"),
                    audience=payload.get("audience", "general"),
                    text=payload.get("text", ""),
                    variables=payload.get("variables", {}) or {},
                )
                self._entries[prompt_id] = entry

    def render(self, prompt_id: str, **variables: Any) -> str:
        if prompt_id not in self._entries:
            raise KeyError(f"prompt {prompt_id} not registered")
        return self._entries[prompt_id].render(**variables)

    def has_prompt(self, prompt_id: str) -> bool:
        return prompt_id in self._entries


def _default_prompts_dir() -> Path:
    return get_shared_config_root() / "prompts"


PROMPT_REGISTRY = PromptRegistry(_default_prompts_dir())

