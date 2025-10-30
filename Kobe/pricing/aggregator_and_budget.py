"""文件: Kobe/WorkPlan/14.md
模块: kobe.pricing.aggregator_and_budget
同步策略: doc_is_source
目的: 定义费用聚合与 token 预算守卫的“可执行”文档；含行为契约、Prompts 与输出结构。"""

from __future__ import annotations

"""导入 Protocol/TyedDict/Mapping/Optional：定义依赖接口与返回结构。"""
from typing import Protocol, TypedDict, Mapping, Any, Optional


class PricingAggregator(Protocol):
    def calculate(self, inputs: Mapping[str, Any], config: Mapping[str, Any]) -> Mapping[str, Any]: ...


class BudgetPolicy(TypedDict, total=False):
    per_call_max_tokens: int
    per_flow_max_tokens: int
    summary_threshold_tokens: int


class PricingResult(TypedDict):
    currency: str
    total: float
    breakdown: Mapping[str, Any]


"""函数：call_calculate_total —— 费用聚合
MUST：
  - 校验表达式变量存在；应用分层/阶梯计价；按 locale/货币格式化。"""
def call_calculate_total(pricing_inputs: Mapping[str, Any], aggregator: Mapping[str, Any]) -> PricingResult:
    # 真实计算逻辑由外部注入；此处给出接口与返回结构
    base_fee = float(pricing_inputs.get("base_fee", 0))
    units = float(pricing_inputs.get("units", 0))
    unit_fee = float(aggregator.get("unit_fee", 0))
    total = base_fee + units * unit_fee
    return PricingResult(
        currency=str(pricing_inputs.get("currency", "CNY")),
        total=total,
        breakdown={"base_fee": base_fee, "units": units, "unit_fee": unit_fee},
    )


"""函数：call_check_budget —— token 预算守卫
MUST：
  - 强制 per_call/per_flow；超过 summary_threshold 触发“总结”。"""
def call_check_budget(stage: str, tokens_used: int, policy: BudgetPolicy) -> Mapping[str, Any]:
    exceeded = False
    threshold = policy.get("per_call_max_tokens", 0)
    if tokens_used > int(threshold):
        exceeded = True
    return {"stage": stage, "tokens": tokens_used, "threshold": int(threshold), "exceeded": exceeded}


"""函数：behavior_pricing_aggregator —— 费用聚合行为
Inputs：pricing_inputs, aggregator_config。
MUST：变量存在、阶梯策略、货币格式；错误 → refuse 并触发 pricing_error。"""
def behavior_pricing_aggregator(pricing_inputs: Mapping[str, Any], aggregator_config: Mapping[str, Any]) -> PricingResult:
    return call_calculate_total(pricing_inputs, aggregator_config)


"""函数：behavior_budget_guard —— token 预算守卫
MUST：
  - enforce per_call/per_flow；超过 summary_threshold → 触发 summarize。"""
def behavior_budget_guard(stage: str, tokens_used: int, policy: BudgetPolicy) -> Mapping[str, Any]:
    return call_check_budget(stage, tokens_used, policy)


def _examples() -> None:
    return None


#@anchor:prompts_snapshot
PROMPT_CATALOG: dict = {
    "pricing_summary": {
        "locale": "zh-CN",
        "audience": "llm",
        "text": "费用：基础 {base_fee}，用量 {units}，总计 {total}",
    },
    "budget_alert": {
        "locale": "en-US",
        "audience": "ops",
        "text": "Token budget exceeded at {stage}: tokens={tokens} > {threshold}",
    },
    "pricing_error": {
        "locale": "en-US",
        "audience": "ops",
        "text": "Pricing calc failed: {error}",
    },
}


PROMPT_VARS_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "base_fee": {"type": "number"},
        "units": {"type": "number"},
        "total": {"type": "number"},
        "stage": {"type": "string"},
        "tokens": {"type": "integer"},
        "threshold": {"type": "integer"},
        "error": {"type": "string"},
    },
    "required": [],
}
