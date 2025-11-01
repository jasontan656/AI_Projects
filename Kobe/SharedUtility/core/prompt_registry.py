"""
Prompt registry loader driven by 02.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


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
        for path in base_dir.glob("prompts.*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            for prompt_id, payload in data.items():
                if prompt_id == "metadata":
                    continue
                entry = PromptEntry(
                    prompt_id=prompt_id,
                    locale=payload["locale"],
                    audience=payload["audience"],
                    text=payload["text"],
                    variables=payload.get("variables", {}) or {},
                )
                self._entries[prompt_id] = entry

    def render(self, prompt_id: str, **variables: Any) -> str:
        if prompt_id not in self._entries:
            raise KeyError(f"prompt {prompt_id} not registered")
        return self._entries[prompt_id].render(**variables)

    def has_prompt(self, prompt_id: str) -> bool:
        return prompt_id in self._entries


PROMPT_REGISTRY = PromptRegistry(Path(__file__).resolve().parents[1] / "Config")

