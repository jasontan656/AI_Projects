## Why
- Telegram 会话流此前依赖多阶段 Prompt 编排与 AgentsBridge，但 pipeline 代码已被删除且 `AgentsBridge.dispatch` 只抛 `NotImplementedError`，导致业务逻辑绕一圈仍无法产出回复。
- Prompt Registry 配置已被判定为过时设计；即便补齐 YAML，也违背现在“直接调用 LLM” 的业务方向。
- 需要重建一个最小骨架：收到消息后直接构造请求给 Responses API（或未来自定义模型），并将返回结果封装给接口层；所有旧的 triage/summary/compose prompt 逻辑必须移除。

## What Changes
- 精简 `business_service.conversation`：删除 prompt renderer / triage 逻辑，调整模型结构，仅保留必要的请求上下文与响应数据。
- 在 `foundational_service.integrations.openai_bridge` 中实现一个真正可调用的 Responses API 适配器（使用 `AsyncOpenAI`），返回精简结构供业务服务使用。
- 更新 `business_logic.conversation.TelegramConversationFlow` 以匹配新结果结构，同时更新 OpenSpec specs 反映直接 LLM 方案。
- 移除 prompt registry 中相关条目与配置文件，确保不再加载旧的 YAML。

## Impact
- Telegram webhook 将变为单阶段调用，消除 prompt 缺失与旧 pipeline 的隐藏耦合。
- 业务逻辑和业务服务层职责重新一致：服务层直接调用 LLM，逻辑层仅作薄包装。
- 后续若要重新接入复杂流程，可在新的骨架上逐步扩展，而不会再受旧设计牵制。
