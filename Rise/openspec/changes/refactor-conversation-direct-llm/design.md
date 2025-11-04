## Target Architecture
1. **Conversation Facade**
   - `TelegramConversationService.process_update` 直接读取用户输入和上下文，构造 `LLMRequest`（含 user_text、history、policy seed 等元信息）。
   - 调用 `AgentDelegator.dispatch`，该方法通过新的 `behavior_agents_bridge` 与 Responses API 通信，返回 `LLMResult`。
   - 服务层负责组装 Telegram outbound contract（保持 adapter 构造逻辑），但不再渲染任何 Prompt。

2. **OpenAI Bridge**
   - 采用 `from openai import AsyncOpenAI`。
   - 使用 `responses.create`，将用户消息映射为单轮对话输入；允许 future 传递 system prompt / additional context。
   - 返回结构仅包含 `text`、`usage`（tokens）和 `response_id`。

3. **Business Logic**
   - `TelegramConversationFlow` 仍输出 `ConversationResult`，但字段来自新的 `LLMResult`（无 triage / telemetry chunk）。
   - 分类、triage、summary 等字段置空或默认值，确保接口层兼容。

4. **Specs 调整**
   - 新增 capability 说明“直接 LLM 骨架”，废弃对 prompt registry 的依赖条目。
   - 文档化返回结构和错误处理（如调用失败时抛 500 / 返回占位文本）。

## Outstanding Questions
- 安全拒绝逻辑暂时由上游模型决定，是否需要保留保底拒绝模板？暂按用户要求移除，必要时再引入。
- Token 预算由运行策略提供，目前直接转交给 Responses API；后续可扩展为 dynamic 参数。
