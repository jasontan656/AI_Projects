"""文件: Kobe/WorkPlan/13.md
模块: kobe.core.core_envelope_spec
同步策略: doc_is_source
目的: 给出 CoreEnvelope 字段的“可执行”结构定义（TypedDict）与校验要点；其它文档引用此规范。"""

from __future__ import annotations

"""导入 TypedDict/Required/NotRequired 用于精确定义字段必选性；re/typing 用于附加约束说明。"""
from typing import TypedDict, Required, Literal, NotRequired


"""CoreEnvelope 元数据（metadata）字段：
chat_id/convo_id/channel/language 均为字符串；language 需匹配 ^[a-z]{2}(-[A-Z]{2})?$。"""
class Metadata(TypedDict):
    chat_id: str
    convo_id: str
    channel: str
    language: str


class Attachment(TypedDict, total=False):
    kind: Literal["image", "file", "voice", "audio", "video", "link", "unknown"]
    url: NotRequired[str]
    checksum_sha256: NotRequired[str]


class Telemetry(TypedDict, total=False):
    request_id: NotRequired[str]
    trace_id: NotRequired[str]
    latency_ms: NotRequired[int]
    validation_ms: NotRequired[int]
    status_code: NotRequired[int]
    error_hint: NotRequired[str]


class CoreEnvelope(TypedDict, total=False):
    metadata: Required[Metadata]
    context_quotes: NotRequired[list[str]]
    attachments: NotRequired[list[Attachment]]
    ext_flags: NotRequired[dict]
    telemetry: NotRequired[Telemetry]
    version: Required[str]


"""函数：validate_core_envelope —— 结构校验（骨架）
MUST：
  - metadata.chat_id/convo_id/channel/language 必填；language 符合正则。
  - attachments.kind 在白名单内，否则拒绝并触发 core_envelope_attachment。
  - version 严格 SemVer（示例 v1.0.0）。"""
def validate_core_envelope(env: CoreEnvelope) -> None:
    # 这里只给出形状与关键规则；具体正则/枚举校验由 JSON Schema 执行
    required_meta = ["chat_id", "convo_id", "channel", "language"]
    meta = env.get("metadata", {})
    for k in required_meta:
        if k not in meta:
            raise ValueError(f"missing metadata.{k}")
    if "version" not in env:
        raise ValueError("missing version")


"""示例（最小）：
Golden：完整 metadata + version=v1.0.0 -> 通过。
Counter：attachments.kind=\"video\" 且不在白名单 -> 拒绝。"""
def _examples() -> None:
    return None


#@anchor:prompts_snapshot
PROMPT_CATALOG: dict = {
    "core_envelope_gap": {
        "locale": "zh-CN",
        "audience": "dev",
        "text": "CoreEnvelope 缺少字段 {field}",
    },
    "core_envelope_attachment": {
        "locale": "en-US",
        "audience": "ops",
        "text": "Attachment validation failed for {kind}",
    },
}


PROMPT_VARS_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "field": {"type": "string"},
        "kind": {"type": "string"},
    },
    "required": [],
}
