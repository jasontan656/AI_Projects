"""Tool registry producing LangChain StructuredTool wrappers."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field, ConfigDict
from hub.logger import info


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(..., description="Action name")
    params: Dict[str, Any] = Field(default_factory=dict)


class ToolRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        actions: List[str],
    ) -> None:
        self._registry[name] = {
            "handler": handler,
            "description": description,
            "actions": actions,
        }
        info("tool_registry.registered", tool=name, action_count=len(actions))

    def build_langchain_tools(
        self,
        context_provider: Callable[[], Dict[str, Any]],
    ) -> List[StructuredTool]:
        """
        Build LangChain tools from registered tool specs.
        
        Note: Empty lists/dicts are allowed for optional parameters:
        - actions: Some tools may not declare specific actions
        - params: Tool calls may have no parameters
        - context: Context provider may return None for anonymous users
        """
        tools: List[StructuredTool] = []
        for name, meta in self._registry.items():
            handler = meta["handler"]
            # actions can be empty list if tool doesn't declare specific actions
            actions = meta["actions"] if meta["actions"] is not None else []
            description = meta["description"]

            def tool_fn(action: str, params: Dict[str, Any] | None = None, *, _handler=handler) -> str:
                # context_provider may return None for anonymous users - treat as empty dict
                context = context_provider()
                if context is None:
                    context = {}
                
                # params is optional - None means no parameters provided
                if params is None:
                    params = {}
                
                result = _handler(
                    action=action,
                    params=params,
                    user_context=context,
                )
                return json.dumps(result, ensure_ascii=False)

            tool_description = (
                f"{description}\n\nSupported actions: {', '.join(actions)}"
                if actions
                else description
            )

            tools.append(
                StructuredTool.from_function(
                    tool_fn,
                    name=name,
                    description=tool_description,
                    args_schema=ToolArgs,
                )
            )
        return tools

    def list_tools(self) -> List[str]:
        return list(self._registry.keys())


__all__ = ["ToolRegistry"]


