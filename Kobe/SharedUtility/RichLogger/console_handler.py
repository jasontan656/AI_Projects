from __future__ import annotations
import json
import logging
from typing import Any, Iterable, Mapping, Optional, Dict, Sequence
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


class PrettyEventFilter(logging.Filter):
    """将结构化 JSON 事件在终端美化为可读的一行/少量多行。

    仅作用于控制台 handler；文件 handler 仍记录原始 JSON。
    """

    def __init__(self, max_show_files: int = 3, max_preview: int = 120):
        super().__init__()
        self.max_show_files = max_show_files
        self.max_preview = max_preview

    def _short(self, s: Optional[str], n: int = 8) -> str:
        return (s or "-")[:n]

    def _join(self, items: Iterable[Optional[str]]) -> str:
        normalized = [item or "-" for item in items]
        if not normalized:
            return "-"
        head = normalized[: self.max_show_files]
        more = len(normalized) - len(head)
        name = "; ".join(x.split("/")[-1] for x in head)
        return f"{name}{f' +{more}' if more>0 else ''}"

    def _tokens(self, meta: Dict[str, Any]) -> str:
        tu = (meta or {}).get("token_usage") or {}
        pt, ct, tt = tu.get("prompt_tokens"), tu.get("completion_tokens"), tu.get("total_tokens")
        if pt is None and ct is None and tt is None:
            return ""
        if tt is None:
            tt = (pt or 0) + (ct or 0)
        return f"tokens: {pt or 0}/{ct or 0}={tt}"

    def _model(self, meta: Dict[str, Any]) -> str:
        name = (meta or {}).get("model_name")
        return f"model={name}" if name else ""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if not msg or msg[0] not in "{[":
            return True
        try:
            payload = json.loads(msg)
        except Exception:
            return True
        if not isinstance(payload, dict) or "event" not in payload:
            return True

        ev = payload.get("event")
        trace = payload.get("trace_id") or payload.get("trace")
        meta = payload.get("meta") or {}
        line: Optional[str] = None

        if ev == "router.llm":
            line = f"[ROUTE/LLM] trace={self._short(trace)} {self._model(meta)} {self._tokens(meta)}"
        elif ev == "router.result":
            line = (
                f"[ROUTE] {payload.get('route')} conf={payload.get('confidence', 0):.2f} "
                f"reason={payload.get('reason','-')} trace={self._short(trace)}"
            )
        elif ev == "kb.select_files.llm":
            raw = payload.get("raw") or []
            picks = [it.get("path") for it in raw if isinstance(it, dict)]
            line = (
                f"[KB/SELECT] picks={len(picks)} {self._model(meta)} {self._tokens(meta)} "
                f"trace={self._short(trace)}\n  top: {self._join(picks)}"
            )
        elif ev == "kb.snippets":
            files = payload.get("files") or []
            ctx = payload.get("context_len")
            cites = payload.get("cites") or []
            cite_titles = [c.get("title") for c in cites if isinstance(c, dict)]
            line = (
                f"[KB/SNIPPETS] files={len(files)} context={ctx}B trace={self._short(trace)}\n"
                f"  files: {self._join(files)}\n  cites: {self._join([t or '-' for t in cite_titles])}"
            )
        elif ev == "kb.answer.llm":
            ans_len = payload.get("answer_len")
            prev = payload.get("prompt_preview") or ""
            if len(prev) > self.max_preview:
                prev = prev[: self.max_preview] + "…"
            line = (
                f"[LLM/ANSWER] {self._model(meta)} {self._tokens(meta)} answer_len={ans_len} "
                f"trace={self._short(trace)}\n  prompt_preview: {prev}"
            )
        elif ev in ("request.start", "request.end"):
            method = payload.get("method")
            path = payload.get("path")
            extra = f" status={payload.get('status')}" if ev == "request.end" else ""
            line = f"[HTTP] {ev.split('.')[1]} {method} {path}{extra} trace={self._short(trace)}"

        if line:
            record.msg = Text.from_markup(line)
        return True

def build_console_handler(
    *,  # 使用 * 限定后续参数必须用关键字传递；提高可读性【语法（Syntax）】
    level: int = logging.INFO,  # 声明关键字参数 level 默认 INFO；控制控制台最小等级【配置（Config）】
    console_kwargs: Mapping[str, Any] | None = None,  # 声明可选 console_kwargs；允许调用者透传 Console 的样式配置【扩展（Extension）】
    rich_tracebacks: bool = True,  # 声明 rich_tracebacks 默认 True；输出堆栈时带富文本【体验（Experience）】
    keywords: Sequence[str] | None = None,  # 声明 keywords 关键术语元组；支持高亮重要词汇【体验（Experience）】
) -> logging.Handler:  # 指明函数返回标准库 logging.Handler；保持与 logging 生态一致【类型（Type Hint）】
    handler = RichHandler(
        console=Console(**(console_kwargs or {})),  # 调用 Console 并解包自定义参数；默认创建标准终端对象【依赖库（Library）】
        rich_tracebacks=rich_tracebacks,  # 传入 rich_tracebacks 控制堆栈呈现；保留彩色上下文【配置（Config）】
        keywords=list(keywords) if keywords else None,  # 传入 keywords 用于高亮关键字；提升可读性【体验（Experience）】
    )
    handler.setLevel(level)  # 在 handler 上调用 setLevel 应用最低等级；与全局策略保持一致【配置（Config）】
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(PrettyEventFilter())
    return handler  # 返回配置好的处理器实例；供 RichLoggerManager 统一挂载【返回（Return）】
