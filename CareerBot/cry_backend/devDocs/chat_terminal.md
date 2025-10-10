# Chat Terminal 功能说明（工作版）

> 版本：v0.1-draft｜文件：`cry_backend/devDocs/chat_terminal.md`｜状态：初始化占位，随对话迭代完善

## 1. 目标与范围
- **目标**：
  - 明确并固化接口契约：Envelope 结构、统一响应骨架、受限事件集（token|ui|artifact|final|error|metrics）。
  - 确保对话驱动的工具化调用：Chat Agent 仅以 `function_call_tool` 经 LangServe 访问工具，禁止旁路。
  - 统一 UI 渲染协定：工具以 `ui|artifact` 事件声明渲染，前端据此完成表单/媒体预览，无页面跳转。
  - 落实 Fail-Fast 与追踪：错误即时失败、结构化日志最小字段齐备（trace_id/request_id/route_path/tool/...）。
  - 通过合规清单验收：满足本文件“合规审查清单”全部条目。
- **范围**：后端 Hub 编排、LangChain Chat Agent、工具（LangChain Tool via LangServe）、统一 Envelope 协议、流式事件、前端渲染协定。

- **功能承载目录**：scripts/chat_terminal
- **非目标**：不设计外部旁路 API、不引入宪法外技术栈、不实现与规范无关的试验性特性。

## 2. 宪法对齐（强制约束）
- 运行时：Python 3.10、.venv 管理依赖。
- 框架：FastAPI（HTTP 层）、LangChain ≥ 0.3（智能体/工具）、LangServe（服务暴露）。
- 数据模型：Pydantic v3。
- 通道：WebSocket（唯一前端流式通道）。
- HTTP 出站：仅 `httpx`/`httpx-sse`。
- DB：MongoDB，经 `shared_utilities/mango_db/mongodb_connector.py` 的 `DatabaseOperations` 门面访问。
- 前端：Vue 3 + TypeScript + Vite（优先 `pnpm`）。
- 统一协议：Envelope 输入/输出与响应骨架；流式事件仅限 `token|ui|artifact|final|error|metrics`。

## 3. 交互总览
- 用户输入 → Hub 适配为 Envelope → Chat Agent 判定 → 按需 `function_call_tool`（封装 Envelope）→ 工具门面执行业务 → 结构化结果/流式事件返回 → Chat Agent 生成最终答复（结构化）。
- 禁止：绕开 Envelope 或工具门面的直连调用；禁止返回自由文本。

## 3.1 对齐后端编排（终端遵循）
- 终端消息封装：所有上行消息必须为 Envelope；若终端无法直接封装，则必须发送到 Hub 的 chat→envelope 适配入口，由 Hub 严格封装后再下游流转。
- 决策与调用：Hub 仅将 Envelope 交由 Chat Agent 判定；工具调用仅采用 `function_call_tool`，统一经 LangServe 暴露的 Tool 路由执行。
- 路由显式：`payload.route.path` 必填且为唯一路由依据，禁止隐式默认或自动补全。
- 只读/只写边界：下游处理器仅读 `user/meta`，仅写 `payload.data`；多余字段判 `INVALID_INPUT`。
- 错误与收束：错误映射到标准 `error_type` 并以 `error` 事件收束；成功以 `final` 收束。
- 禁止旁路：终端不得直接调用工具 HTTP/RPC；一切经 Hub→Chat Agent→Tool 规范链路。

## 4. Envelope 协议（唯一输入/输出）
```
Envelope {
  user: {
    user_id: string   // timestamp+uuidv4（去符号），只读
    ...               // 仅必要字段
  },
  payload: {
    route: { path: string[] },  // 唯一路由依据，非空数组
    data: { ... }               // 业务输入/状态，仅此可写
  },
  meta: {
    request_id: string,         // timestamp+uuidv4（去符号）
    ...                         // 只读辅助元信息
  }
}
```
- 处理器仅读 `user/meta`，仅写 `payload.data`；缺失/多余字段 → `INVALID_INPUT`。
- 响应骨架：
  - 成功：`{"success": true, "message"?: str, "data"?: {...}}`
  - 失败：`{"success": false, "error": str, "error_type": str, "details"?: {...}}`

## 5. 流式事件与前端渲染协定
- 事件类型：`token|ui|artifact|final|error|metrics`（仅限）。
- `ui` 渲染声明（示例）：
  - `type: form|video|image|preview|markdown|list|modal`
  - `schema: [{ name,label,type,required,options?,placeholder?,default? }]`
  - `actions: [{ label, route.path, method, validate }]`
  - `data: 任意初始数据`
  - `meta: 呈现细节（布局/占位/优先级）`
- `artifact`：资源引用（URL/上传 token）。
- 约束：`ui/artifact` 必经统一流式通道；表单提交必须回到 Envelope；所有 `route.path` 显式（如 `auth/login/step/verify`）。

## 6. Chat Agent 与工具调用
- Chat Agent：基于 LangChain，按语义判定是否调用工具（`function_call_tool`）。
- 工具：以 LangChain Tool 注册，经 LangServe 挂载（统一前缀，如 `/api/tools`，kebab-case 命名）。
- 请求体：仅接收 Envelope；`payload.route.path` 精确映射处理器；禁止弱化/自动补全。
- 返回体：统一响应骨架；流式严格遵守 SSE 协议（若使用）。
- 错误映射：`INVALID_INPUT|UNAUTHORIZED|FORBIDDEN|NOT_FOUND|STEP_NOT_FOUND|CONFLICT|RATE_LIMITED|DEPENDENCY_ERROR|INTERNAL_ERROR`。

## 7. 典型流程（抽象）
```
User → Hub(chat→envelope) → Chat Agent
  ↳ 判定：需要工具？
    ├─ 否：生成结构化答复 → emit token→final
    └─ 是：call tool (Envelope)
         → 工具门面：校验→路由→业务→DAO
         → emit ui|artifact（可多次）
         → emit token（可选）
         → final|error 收束
```

## 8. 目录结构与门面职责
- 目录：
  - `tool_modules/` 业务域门面+路由
  - `hub/` 编排/注册/聊天（Agent、流式、路由）
  - `shared_utilities/` 跨域门面/适配器（validator/time/http/db/logging）
- 门面不变式：Envelope 强校验 → 显式路由 → 纯业务逻辑 → 数据访问 → 统一响应构造。
- 渐进式整改：触达重复实现时迁移至单点模块并移除旧实现。

## 9. 单点能力与调用规范
- Validators：`shared_utilities/validator.py`（如 `ensure_timestamp_uuidv4()`、`is_valid_email()`、`normalize_auth_username()`）。禁止内联复制。
- Time：`shared_utilities/time.py` 的 `Time.timestamp()` 生成 timestamp-uuidv4。
- HTTP：仅 `httpx`/`httpx-sse`；禁止手写流式解析。
- DB：`shared_utilities/mango_db/mongodb_connector.py` 的 `DatabaseOperations`（优先异步）。
- Logging：`hub/logger.py`，字段至少包含 `trace_id|request_id|route_path|tool|error_type?|user_id?|session_id?`。

## 10. Fail-Fast 策略
- 禁止 catch-all 与吞错；错误立即失败（fast-fail），日志结构化记录。
- 禁止静默默认/自动补全；非法/缺失字段 → `INVALID_INPUT`。
- 禁止无条件自动重试（需显式策略时再开）。
- 流式错误必须 `error` 事件结束并关闭连接。

## 11. 核心标识与命名
- 字段：snake_case 小写；历史异常命名入库时规范化。
- `user_id`/`request_id`：timestamp+uuidv4 串接，移除分隔符，仅字母数字。
- `auth_username`：仅作“用户名”处理（可含 `@`/`.`），使用 `normalize_auth_username()` 归一；不得作为邮件地址。
- `email_add`：字符串数组，每项经 `is_valid_email()` 校验；仅通信/画像用途。
- 代码风格：Python PEP8/四空格/类型注解；TS 采用 ESLint+Prettier，函数命名 camelCase；导入禁止二次重命名。

## 12. 聊天终端功能要点
- 会话接入：WebSocket 建链，首帧校验 Envelope 完整性与 `route.path`。
- 对话驱动 UI：工具返回 `ui`/`artifact` 渲染声明，前端据此无页面跳转完成交互。
- 表单回传：前端表单提交装配为 Envelope（原 `route.path` 或显式新路径）回流工具。
- 流式体验：token 增量输出，`final` 收束；异常以 `error` 收束并含 `error_type`。
- 可观测性：全链路打点与结构化日志（含 `user_id`/`request_id`/`route_path`/`tool`）。

## 12.1 终端（Rich）渲染与交互
- 核心目标（终端内稳定对话体验）：
  - 接受用户输入（单行/多行），以 Envelope 发送。
  - 渲染模型增量输出（`token` 事件）与结构化 `ui|artifact` 事件。
  - 保持布局稳定、无闪烁、可回溯（历史消息可折叠/展开）。
- 事件到渲染的映射：
  - `token`：Rich `Live` 区域增量写入；支持 Markdown（`Console.print(Markdown)`），在 `final` 收束前仅追加不回退。
  - `ui`：按 `type` 渲染：
    - `form` → 使用 `Table` 展示字段（name/label/type/required/default），逐项交互式输入并校验；`actions` 显示为可选指令（编号选择）。
    - `markdown` → 直接 Markdown 渲染于独立 Panel。
    - `list|modal|preview` → `Panel`/`Table` 组合展示摘要，必要时提供“展开”命令。
  - `artifact`：展示可访问 URL/令牌；若为图像/视频，仅展示元信息与可打开的本地命令提示（不在终端内自绘）。
  - `final|error|metrics`：
    - `final` → 关闭 `Live` 并固化输出；
    - `error` → 高亮错误区块（含 `error_type` 与 `details`），记录日志；
    - `metrics` → 以轻量 `Table` 显示（tokens/s、latency、tool_calls）。
- 输入与并发模型：
  - 异步三任务建议：`receiver_task`（事件消费）/`renderer_task`（富渲染）/`input_task`（用户输入）。
  - 使用无界或限界队列（建议限界）传递事件，避免渲染阻塞接收；对 `token` 事件做批量合并（时间窗 16–33ms）。
  - 输入模式：
    - 单行：直接 `>` 提示符；
    - 多行：输入 `>>>` 进入多行模式，以 `...` 前缀；`/end` 结束；
    - 通用命令：`/actions` 查看当前可用动作、`/history` 查看历史、`/clear` 清屏。
- 布局建议：
  - 左列消息历史（可滚动），右列上下两区：上区 `Live`（增量 token），下区输入提示/动作栏。
  - `Panel` 标题包含 `route.path` 关键信息，便于调试与审计。
- 协议与约束：
  - 仅通过 WebSocket 统一通道接收事件；禁止自定义协议解析；
  - 提交表单/动作必须回到 Envelope（显式 `route.path`）。
- 日志与审计：
  - 记录用户输入与关键事件摘要（脱敏），对齐 `hub/logger.py` 字段规范。
  - 错误与超时（如 30s 无事件）高亮提示并落盘。

## 13. 示例路由（占位）
- 认证登录：`["auth","login","step","verify"]`
- MBTI 测评：`["mbti","questionnaire","v1","step","q01"]`
- 资源预览：`["media","preview","v1"]`
- 说明：以上为抽象示例，最终以工具门面提交的路由规范为准（待补）。

## 14. 合规审查清单（必须通过）
- Envelope 完整性与显式路由。
- 统一响应骨架与错误码映射（含流式事件约束）。
- Validators/Time/HTTP/DB/Logging 单点调用，无重复实现。
- LangServe 挂载与工具注册一致（不存在旁路）。
- 异步/幂等/审计轨迹（含 `STEP_ALREADY_COMPLETE`）。
- 目录与门面职责符合不变式。

## 15. 架构现状与落地方案（基于代码库扫描）

### 15.1 已落地架构要素
- **已注册工具清单**（`hub/hub.py`）：
  - `auth`：认证模块，支持 8 个动作（login/register/oauth_google/oauth_facebook/reset/logout）
  - `mbti`：MBTI 测评模块，支持 5 个步骤（step1-step5）
- **路由命名模式**（已落实）：
  - 入口路由：`["chat", "v1", "message"]`（LangServeChatAdapter.ROUTE_PATH）
  - 工具内路由：`["auth"|"mbti", action]`，如 `["auth", "auth_login"]`、`["mbti", "mbti_step1"]`
  - 规范：无版本号嵌套（工具级隐式 v1），kebab-case 动作名（实际采用 snake_case）
- **流式事件类型**（`chat_agent.py` 实现）：
  - `token`：LLM 增量输出（`on_llm_new_token`）
  - `ui`：工具返回 form_data 或 ui 声明（`_tool_output_events` 解析）
  - `artifact`：工具返回 artifacts 列表
  - `final`：收束事件，含完整消息与 retrieval 上下文
  - `error`：异常收束，含 error_type（INVALID_INPUT/DEPENDENCY_ERROR 等）
  - `metrics`：当前仅在流开始时发送 `{"type": "metrics", "retrieval_count": N}`
- **UI 渲染协定**（已实现字段）：
  - `ui.type = "form"`：从 `form_data.form_schema` 构造
  - `ui.schema`：字段定义数组
  - `ui.data`：初始数据（来自 `form_data.initial_data`）
  - `ui.meta`：批次信息（`form_data.batch_info`）
  - 验证：form_schema 由工具模块定义（如 `mbti/step1.py`），Hub 不做结构校验，直接透传
- **单点能力落实**（宪法对齐）：
  - Validators：`shared_utilities/validator.py`（ensure_timestamp_uuidv4/normalize_auth_username/is_valid_email）
  - Time：`shared_utilities/time.py` 的 `Time.timestamp()` 与 `Time.now()`
  - HTTP：httpx（代码库中使用，SSE 通过 LangServe 原生支持）
  - DB：`shared_utilities/mango_db/mongodb_connector.py` 的 `DatabaseOperations`
  - Logging：`hub/logger.py`（结构化日志，含 trace_id/request_id/route_path）

### 15.2 待补齐能力与风险
- **未注册工具模块**（目录存在但未挂载）：
  - `company_identity`、`final_analysis_output`、`jobpost`、`matching`、`ninetest`、`resume`、`taggings`
  - 处理策略：终端首发不支持，Chat Agent 遇到相关意图时回复"功能开发中"；待工具模块提交 TOOL_SPEC 后注册
- **metrics 事件扩展**：
  - 当前：仅 `retrieval_count`（流开始时一次性发送）
  - 建议补齐：`tokens_count`（累计 token 数）、`tool_calls`（工具调用次数与耗时）、`latency_ms`（端到端延迟）
  - 实施：在 `chat_agent.py` 的 `stream_chat` 中收集统计，于 `final` 前或同时发送完整 metrics
- **终端渲染策略**：
  - token 批处理：建议 16-33ms 时间窗合并，避免过度刷新（Rich `Live` 区域帧率限制）
  - artifact 降级：终端仅展示 URL/元信息/MIME type，不尝试内嵌渲染（图像/视频）
  - 多行输入：建议 `>>>` 进入多行模式，`/end` 结束；单行直接 `>` 提示符
- **会话管理**：
  - 当前实现：session_id 在 ChatRequest 中可选，Chat Agent 未实现持久化会话历史（chat_history 硬编码空列表）
  - 终端策略：单会话模式，本地生成 session_id 并复用，不实现多会话并发（简化 MVP）

### 15.3 风险与缓解
- **旁路调用巡检**：扫描确认工具模块（auth/mbti）均通过 `router.route(envelope)` 调用内核，无旁路直连（合规）
- **SSE 与 WebSocket**：
  - 当前：LangServe 暴露 `/chat/stream` 为 SSE 端点，前端可采用 WebSocket 或 SSE
  - 终端采用：HTTP POST + SSE（httpx-sse），不引入 WebSocket 复杂度
  - 前端 Web 采用：建议 WebSocket（需单独实现 WebSocket 适配器）
- **输入法与历史**：Rich 原生支持 `Prompt.ask()`，多行模式需自定义循环采集，历史管理不依赖 readline（Windows 兼容性）

## 16. 终端实现决策（基于当前架构）

### 16.1 终端首发工具支持
- **优先级 P0**（必须支持）：
  - 基础对话（无工具调用，纯 LLM 回复）
  - `auth` 工具：登录/注册流（演示 UI 表单渲染与多轮交互）
- **优先级 P1**（建议支持）：
  - `mbti` 工具：展示多步骤流程与问卷渲染
- **P2 及以后**：其他工具模块（待注册后支持）

### 16.2 路由与版本策略
- **确认**：当前无需 `/api/tools/<tool-name>/vX` 前缀
- **实际路由**：
  - 入口：`POST /chat/invoke`（一次性）、`POST /chat/stream`（SSE）
  - Envelope 内路由：`payload.route.path = ["chat", "v1", "message"]`
  - 工具由 Chat Agent 通过 LangChain function calling 自动选择，终端用户无需手动指定工具路由
- **终端行为**：用户输入自然语言 → Hub 判定 → 自动调用工具或直接回复

### 16.3 UI 表单校验策略
- **确认**：全部服务端兜底（工具模块内强校验，返回 INVALID_INPUT 错误）
- **终端轻校验**：可选，仅做基础格式提示（如必填项、邮箱格式），不替代服务端校验
- **实施**：终端展示 form_schema 时，标注 `required` 字段；提交前检查非空，格式校验由后端返回错误后重新提示

### 16.4 会话恢复策略
- **确认**：首发**不支持**多会话并发与跨进程恢复
- **实施**：
  - 单会话：终端启动时生成 session_id（timestamp+uuid），进程内复用
  - 历史：仅内存保留当前会话消息（用于终端滚动查看），不持久化
  - 恢复：退出即清空；如需恢复，待 MemoryService 实现持久化后对接

### 16.5 Metrics 事件字段集
- **最小字段集**（终端必须展示）：
  - `retrieval_count`：检索文档数（已实现）
  - `tokens_count`：生成 token 总数（待补齐）
  - `latency_ms`：端到端延迟（待补齐）
- **扩展字段**：
  - `tool_calls`：工具调用次数与名称列表
  - `tool_latency_ms`：工具调用总耗时
- **展示策略**：终端以轻量 `Table` 或状态栏形式显示，不干扰主内容区

## 17. 实施路径与验收标准

### 17.1 文档路径统一
- **确认**：仓库实际路径为 `cry_backend/devDocs`（驼峰式）
- **行动**：保持一致，文档与代码引用统一使用 `devDocs`

### 17.2 通道策略明确
- **统一通道（前端）**：Web 前端采用 **WebSocket**（唯一流式通道）。
- **终端通道**：终端也采用 **WebSocket** 为默认通道；SSE 仅作为调试回退（不推荐在生产环境使用）。
- **兼容性**：保留 LangServe `/chat/stream`（SSE）以便自动化/回放；新增 `/ws/chat`（WebSocket）供前端与终端统一使用。
- **协议一致**：上行一律发送 Envelope；下行严格为受限事件集 `token|ui|artifact|final|error|metrics` 的 JSON 帧。

### 17.3 WebSocket 设计与实现
- **端点**：`GET /ws/chat`
- **握手与首帧**：建立连接后，客户端发送首帧 Envelope（含 `user.id`、`meta.request_id`、`payload.route.path=["chat","v1","message"]`、`payload.data.message`）。
- **上行消息（客户端→服务端）**：
  - 每条用户输入均作为完整 Envelope JSON 帧发送；禁止发送自由文本。
  - `authorization` 放置于 Envelope `user.authorization` 字段（或在首次帧中携带并在后续沿用）。
- **下行事件（服务端→客户端）**：
  - 逐帧发送 JSON：`{"type": "token|ui|artifact|final|error|metrics", ...}`。
  - `final` 或 `error` 必须收束一次往返；随后连接保持可复用以承载下一条 Envelope。
- **生命周期与并发**：
  - 单连接支持多轮对话；每次收到 Envelope 即启动一次流式处理，将事件按顺序写回。
  - 使用限界队列（建议 1024）做事件背压；超过上限触发 `error` 并主动关闭（`1009`）。
- **心跳与保活**：
  - 服务端每 25s 发送 `{"type":"metrics","heartbeat":true}`；客户端需在 10s 内回 `{"type":"metrics","heartbeat_ack":true}` 或发送下一条业务帧，否则关闭（`1001`）。
- **错误与关闭码**：
  - `INVALID_INPUT` → 1008（Policy Violation）；`UNAUTHORIZED` → 1008；`RATE_LIMITED` → 1013；依赖错误 → 1011；正常收束 → 1000。
  - 关闭前务必先下发 `{"type":"error", "error_type": ...}` 事件。
- **安全与日志**：
  - 首帧与每次 Envelope 验证 `user.id`/`meta.request_id`（`ensure_timestamp_uuidv4`）。
  - 结构化日志：`trace_id/request_id/route_path/tool/user_id/session_id` 最小字段齐备。
- **实现草案**：
  - 后端：新增 `hub/websocket.py` 暴露 `ws_chat_endpoint(websocket: WebSocket)`；复用 `HubRouter.stream(envelope)` 产出事件，逐帧 `await websocket.send_json(event)`。
  - 前端：`const ws = new WebSocket("wss://host/ws/chat")`；`ws.onmessage = (e) => render(JSON.parse(e.data))`；发送时封装 Envelope。
  - 终端：引入 `websockets` 库或 `anyio` WebSocket 客户端；三协程模型：`receiver`（读帧）/`renderer`（批量渲染 token）/`input`（采集并发送 Envelope）。

### 17.4 终端交付清单（DoD）
- [ ] 实现 `cry_backend/scripts/chat_terminal.py`（单文件或模块化）
- [ ] 支持命令行参数：`--host`、`--port`、`--ws/--no-ws`（默认 WebSocket）
- [ ] 实现交互命令：`/quit`、`/clear`、`/ws on|off`、`/info`（显示 user_id/session_id）
- [ ] 渲染：token 增量输出（Live，批处理 16–33ms）、ui 表单（Table）、artifact 元信息、metrics 面板
- [ ] Envelope 构造：自动生成 user_id/request_id（timestamp+uuid）、session_id 复用、route.path 固定为 `["chat","v1","message"]`
- [ ] 错误处理：网络失败/超时/非 2xx 或 WS 断连均有明确提示并可重连
- [ ] 依赖更新：新增 `websockets>=10.4`；（可选）保留 `httpx-sse` 作为回退
- [ ] 文档对齐：更新 `scripts/chat_terminal/README.md` 或新增说明，命令可直接运行
- [ ] 验收用例：基础对话、auth 登录流、mbti 测评流（至少 step1）

### 17.5 非目标（明确排除）
- 不以 SSE 作为主通道（仅调试回退）
- 不实现多会话管理与持久化（单会话）
- 不实现工具的手动路由选择（依赖 Chat Agent 自动判定）
- 不修改后端业务逻辑（仅终端侧实现）

## 18. 变更记录
- v0.1-draft：初始化文档骨架，补齐宪法约束、协议与缺口清单。
- v0.2-final：基于代码库扫描（hub/orchestrator/chat_agent/tool_modules），明确架构现状、工具清单（auth/mbti）、路由模式（["chat","v1","message"] + ["tool","action"]）、流式事件实现（token/ui/artifact/final/error/metrics）、终端实现决策（SSE 通道/单会话/P0 工具支持/DoD 清单），移除待澄清章节，文档进入可执行状态。
 - v0.3-ws：新增 WebSocket 设计与实现方案：统一前端与终端默认通道为 WebSocket；定义 `/ws/chat` 端点、握手/心跳/背压/关闭码与事件帧格式；更新 DoD 与非目标。
