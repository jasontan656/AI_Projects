"""文件: Kobe/WorkPlan/12.md
模块: kobe.adapters.core_strategy
同步策略: doc_is_source
目的: 统一所有渠道 Adapter 的 CoreEnvelope 构建策略；复用 13.md 中 canonical schema，避免漂移与重复维护。"""

"""导入 __future__.annotations：推迟类型注解解析，便于前向引用类型名。"""
from __future__ import annotations

"""导入 Path（路径）以表达文件/目录；从 typing 导入 Protocol/TyedDict/Mapping 表达依赖与结构。"""
from pathlib import Path
from typing import Protocol, TypedDict, Mapping, Any


"""依赖接口外形：
CoreSchemaValidator —— 校验/规范化 CoreEnvelope；Logger —— 记录 schema 警示。"""
class CoreSchemaValidator(Protocol):
    def validate(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def normalize(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...


class Logger(Protocol):
    def warn(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...


"""输出结构：CoreEnvelope（简化版，完整定义见 13.md schema）。"""
class CoreEnvelope(TypedDict, total=False):
    metadata: Mapping[str, Any]
    context_quotes: list[str]
    attachments: list[Mapping[str, Any]]
    ext_flags: Mapping[str, Any]
    telemetry: Mapping[str, Any]
    version: str


class SchemaValidationError(Exception):
    pass


"""函数：call_build_core_schema —— 构建统一 CoreEnvelope
MUST：
  - 使用 canonical schema（见 13.md / kobe/core/core_envelope.schema.json）校验并规范化。
  - 缺失 language → 默认 zh-CN。
  - 合并 telemetry.request_id（由中间件注入）。
失败：raise SchemaValidationError。"""
def call_build_core_schema(validator: CoreSchemaValidator, update: Mapping[str, Any], channel: str) -> CoreEnvelope:
    try:
        normalized = validator.normalize(update)  # call：统一字段形态/默认值
        checked = validator.validate(normalized)  # call：按 canonical schema 校验
    except Exception as e:  # error：SchemaValidationError
        raise SchemaValidationError(str(e))

    meta = dict(checked.get("metadata", {}))
    if not meta.get("language"):
        meta["language"] = "zh-CN"  # default：缺失语言 → zh-CN

    env: CoreEnvelope = CoreEnvelope(**checked)  # assign：回填规范化后的结构
    env["metadata"] = meta
    # 合并 telemetry.request_id（由外部中间件写入 update）
    telemetry = dict(env.get("telemetry", {}))
    if "request_id" not in telemetry and "request_id" in update:
        telemetry["request_id"] = update["request_id"]  # merge：链路追踪
    env["telemetry"] = telemetry
    env["version"] = env.get("version", "v1.0.0")
    return env


"""函数：behavior_core_envelope —— Adapter 统一行为（入站构建）
MUST：
  - Validate inbound payload against core_envelope.schema.json。
  - Normalize language；默认 zh-CN。
  - Merge telemetry.request_id。
SHOULD：
  - 提供 to_agent_request()/to_logging_dict() 帮助方法。"""
def behavior_core_envelope(validator: CoreSchemaValidator, update: Mapping[str, Any], channel: str) -> CoreEnvelope:
    return call_build_core_schema(validator, update, channel)


"""函数：call_emit_schema_alert —— 发送 schema 告警（辅助）
用于在发现渠道字段与 schema 不符时，输出结构化提示给 DevOps。"""
def call_emit_schema_alert(logger: Logger, channel: str, field: str) -> None:
    logger.warn(f"Schema mismatch on {channel}: {field}")  # log：面向运维的行动提示


"""示例（最小）：
Golden：telegram 入站 update 缺 language -> language=zh-CN；返回 version=v1.0.0。
Counter：unknown channel -> 上层拒绝（不在本函数范围）。"""
def _examples() -> None:
    return None


#@anchor:prompts_snapshot
PROMPT_CATALOG: dict = {
    "core_schema_violation": {
        "locale": "zh-CN",
        "audience": "dev",
        "text": "CoreEnvelope 校验失败: {error}",
    },
    "core_schema_alert": {
        "locale": "en-US",
        "audience": "ops",
        "text": "Schema mismatch on {channel}: {field}",
    },
}


PROMPT_VARS_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "error": {"type": "string"},
        "channel": {"type": "string"},
        "field": {"type": "string"},
    },
    "required": [],
}
