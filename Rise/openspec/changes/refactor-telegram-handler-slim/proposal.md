## Why
- `TelegramConversationService` 现已直接调用 LLM 并恒返回 `mode="direct"`，但接口层 `handle_message` 仍保留占位符、流式分片、代理桥遥测等旧逻辑，造成复杂度和日志噪音。
- `ConversationServiceResult` 数据模型仍保留 triage / agent_bridge 等历史字段，默认值永远为空，容易误导后续调用者。
- Prompt registry 和 BehaviorContract 仍在启动时注入 `app.state`，尽管 registry 已经为空集合；该设计容易让人误以为 Prompt 仍可用。
- OpenAI bridge 兼容参数 `repo_root` 已无用途，`behavior_agents_bridge` 使用请求字典中过多无意义字段，接口应收敛到最小集合。

## What Changes
- 精简 `interface_entry.telegram.handlers.handle_message`，移除 streaming / prompt / refusal 分支与占位符逻辑，统一走单次发送路径，并调整日志字段。
- 收敛 `ConversationServiceResult` 为现用字段，更新业务层、逻辑层及日志处的访问。
- 移除 `BehaviorContract` 中对 Prompt registry 的注入，删除相关空配置引用。
- 调整 `behavior_agents_bridge` 签名为最小必要参数，显式构建 Responses API 请求，并更新调用方。

## Impact
- Telegram handler 更易读、维护，并减少无效日志字段；
- 数据模型与日志聚焦在“原始输入 + LLM 输出”，避免后续开发者误用失效字段；
- 清理 Prompt registry 遗留，启动流程更符合当前架构；
- OpenAI bridge 接口更明确，为未来扩展 (如多模型、retry) 打好基础。
