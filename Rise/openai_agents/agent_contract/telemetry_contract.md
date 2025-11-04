# UnifiedCS Telemetry Contract (Dev Phase Draft)

> 状态：开发阶段草案 – 若字段缺失或类型不匹配，视为阻断性缺陷。  
> 目标：为推理链路提供逐节点的可视化、性能诊断与成本追踪能力。  

## 1. 术语

| 名称 | 说明 |
| --- | --- |
| `stage` | Orchestrator 中的单个执行节点（如 `judgement_v1`） |
| `iteration` | 同一会话内的第 N 次调度（每次用户输入或内部重放算一次） |
| `bridge` | `UnifiedCS` Offline Orchestrator + 行为桥接层 |
| `event` | Telemetry Bus 产出的结构化记录 |

## 2. 事件类型

| 事件 | 触发时机 | 重点字段 |
| --- | --- | --- |
| `StageStart` | stage 调用前 | prompt、state 快照、用户输入 |
| `StageEnd` | stage 成功/失败返回 | 模型输出、validator 结果、token / cost / latency |
| `GuardEvent` | guard 计数或锁定变化 | `violations`、`locked_until`、触发原因 |
| `CacheEvent` | state 或 summary 读写 | `cache_op`（load/save/reset）、`next_step`、diff |
| `BridgeSummary` | 每轮 orchestrator 完成 | 合计 token、耗时、最终 reply、模式（template/guard_lock 等） |

未来可以扩展 `ErrorEvent`、`ToolEvent` 等，需追加在本文档。

## 3. 通用字段

所有事件必须包含以下字段：

```json
{
  "timestamp": "ISO-8601 UTC",
  "event_type": "StageStart",
  "request_id": "str",
  "convo_id": "str",
  "session_id": "str",
  "iteration": 0,
  "stage_id": "str|null",
  "metadata": {
    "channel": "telegram",
    "source": "UnifiedCS"
  }
}
```

`stage_id` 对于非 stage 事件可为空；`iteration` 用于排序还原流水线。

## 4. StageStart 字段

```json
{
  "user_input": {
    "raw": "原始 message",
    "normalized": "规范化文本"
  },
  "prompt": {
    "system": "...",
    "header": "...",
    "body_preview": "前 400 字符",
    "token_estimate": 820
  },
  "state_snapshot": {
    "next_step": "judgement_v1",
    "guard": {"violations": 3, "locked_until": null},
    "latest_response_id": "resp_..."
  }
}
```

## 5. StageEnd 字段

```json
{
  "result": {
    "output_excerpt": "{...}",
    "schema_valid": true,
    "annotations": ["non_inquiry_smalltalk"]
  },
  "performance": {
    "latency_ms_total": 842,
    "latency_ms_provider": 790,
    "token_in": 1024,
    "token_out": 168,
    "cache_hit": false
  },
  "cost": {
    "model": "gpt-4o-mini",
    "pricing_usd": 0.00231
  },
  "state_diff": {
    "next_step": {"old": "judgement_v1", "new": "session_end"},
    "guard.violations": {"old": 3, "new": 4}
  }
}
```

`schema_valid` = false 时必须在 `annotations` 写明原因。

## 6. GuardEvent 字段

```json
{
  "guard": {
    "violations": 4,
    "locked_until": null,
    "action": "register_non_inquiry",
    "message": "No inquiry intent detected..."
  }
}
```

## 7. CacheEvent 字段

```json
{
  "cache": {
    "op": "reset|load|save",
    "path": "openai_agents/agent_contract/runtime_state/chat_.../cached_state.json",
    "summary": {
      "next_step": "judgement_v1",
      "latest_response_id": null
    }
  }
}
```

## 8. BridgeSummary 字段

```json
{
  "summary": {
    "mode": "template|guard_lock",
    "chunks": ["最终回复..."],
    "tokens_total": 1420,
    "token_in": 1200,
    "token_out": 220,
    "pricing_usd": 0.00385,
    "latency_ms_total": 1640
  }
}
```

## 9. 输出渠道

1. **Rich Console**：Tree + Table 结构，默认展开 Stage 层，为测试人员即时观察。  
2. **JSONL 文件**：落地至 `var/logs/unifiedcs.telemetry.jsonl`，按事件逐行追加。  
3. **Logger**：`root.debug.log` 保留结构化 JSON，供其他系统订阅。

## 10. 安全与脱敏

- 开发阶段允许输出完整 prompt / 用户输入；生产需通过配置关闭或截断。  
- 当 `annotations` 包含敏感标签（如 `pii_detected`），Rich Console 需醒目标记。  
- JSONL 文件建议加入每日轮转脚本，防止磁盘膨胀。

---

如需扩展，请在提交前更新本合同并通知下游调用方。
