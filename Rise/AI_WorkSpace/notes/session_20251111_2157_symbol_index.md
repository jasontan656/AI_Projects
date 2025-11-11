# Session Notes 2025-11-11 21:57 CST

## User Intent
- 扩展 `AI_WorkSpace/Index/index.py`，在同一目录运行离线扫描后输出多份 `.md`（函数/类/Schema/事件/API/配置/存储/测试）索引，帮助 AI 快速定位 Rise 与 Up 代码中的关键符号与依赖。

## Repo Context
  - 新增 Vue 组件 fallback（即便未显式 defineComponent 仍按文件名收录），Pinia Store/Service 输出也写入 schemas/functions 索引，满足多端并行研发的定位需求。
- `AI_WorkSpace/Index/index.py:1-900`：新增符号解析 + API/事件/配置/存储/测试聚合逻辑，输出 `functions/classes/schemas/api/events/config/storage/tests` 七份 Markdown 及原 `index.yaml`。
- `AI_WorkSpace/functions_index.md:1`：列出 Rise/Up 各层代表性函数。
- `AI_WorkSpace/classes_index.md:1`：列出 Rise/Up 各层类与 Vue 组件。
- `AI_WorkSpace/schemas_index.md:1`：列出 Pydantic/BaseModel、dataclass、Pinia store/Vue 组件 Schema。
- `AI_WorkSpace/api_index.md:1`：FastAPI + Up request 映射（method/path/handler/文件）。
- `AI_WorkSpace/events_index.md:1`：Channel 事件/队列/Topic 列表（来源文件与层级）。
- `AI_WorkSpace/config_index.md:1`：`.env` 变量与 `src/project_utility/config` 常量清单（仅展示键名）。
- `AI_WorkSpace/storage_index.md:1`：Mongo collection、Rabbit topic、Redis 持久化入口映射。
- `AI_WorkSpace/tests_index.md:1`：Rise/Up 测试文件清单及断言提示。
- `src/interface_entry/bootstrap/application_builder.py`：扫描结果显示 `configure_application()` 仍为 481 行，表明入口层存在“大函数”堆叠问题。

## Technology Stack
- Python 3.11 AST（`ast.parse`, `ast.walk`, `ast.get_docstring`, `ast.unparse`）解析 Rise 代码，正则 + 字符串解析提取 FastAPI 装饰、事件常量、Mongo collection。
- JS/TS/Vue 正则解析 `export function/const`, `defineStore`, `defineComponent`, `requestJson()`，覆盖 Up 服务/API 请求。
- PyYAML 输出 `index.yaml`; Markdown 通过标准字符串拼接生成。

## Search Results
- Context7 `/python/cpython`：AST API 用法（def/class解析、docstring获取）。
- Exa `python ast extractor list functions classes pydantic schemas`（turn0exa0）：佐证 BaseModel 抽取的必要性。
- Web：AST 官方文档 + StackOverflow AST 遍历技巧（`turn0search0/1/5/11`）确保装饰器/节点解析正确。

## Architecture Findings
1. `src/interface_entry/bootstrap/application_builder.py`（Interface Layer）仍聚合日志、节点注册、Healthz、Channel Binding刷新等流程，`configure_application()` 481 行 ⇒ 必须拆分到 `bootstrap/logging.py`, `bootstrap/runtime.py`, `bootstrap/channel.py`，入口仅 orchestrate。
2. `src/stores/workflowDraft.js`（Up Business Service Layer）仍把 schema + API + 校验混在 Store 内；需新增 `src/schemas/workflowDraft.js` 并移出字段定义，Store 仅引用 schema 与 `workflowService`。
3. `foundational_service/messaging/channel_binding_event_publisher.py` 与 `business_service/channel/events.py` 中大量事件/队列常量重复出现在 storage/events 索引，可视为“单文件既定义事件又封装发布逻辑”（Violation #1/#4）；建议将事件常量抽到 `business_asset` 或独立 schema 模块，Publisher/Consumer 仅引用常量。
4. `.env` 中含 RabbitMQ / Redis / OpenAI 等全部密钥，需建立“配置来源枚举 + Secrets 管控”，避免后续脚本误输出值（当前索引仅列键名，但 `.env` 仍是单点）。

## File References
- `AI_WorkSpace/Index/index.py:1`
- `AI_WorkSpace/functions_index.md:1`
- `AI_WorkSpace/classes_index.md:1`
- `AI_WorkSpace/schemas_index.md:1`
- `AI_WorkSpace/api_index.md:1`
- `AI_WorkSpace/events_index.md:1`
- `AI_WorkSpace/config_index.md:1`
- `AI_WorkSpace/storage_index.md:1`
- `AI_WorkSpace/tests_index.md:1`
- `src/interface_entry/bootstrap/application_builder.py`
- `src/stores/workflowDraft.js`
- `src/business_service/channel/events.py`

## Violations & Remediation
1. `src/interface_entry/bootstrap/application_builder.py`（Interface / Entry）— 单一文件混合大量引导逻辑（Violation #1）。
   - **Remediation**：拆分为 `bootstrap/logging.py`, `bootstrap/runtime.py`, `bootstrap/channel.py` 等模块；`configure_application` 仅 orchestrate。
2. `src/stores/workflowDraft.js`（Business Service Layer - Up）— Store 同时声明 schema、API、表单校验（Violation #1/#3）。
   - **Remediation**：新增 `src/schemas/workflowDraft.js`（描述字段/约束），Store 仅引用 schema 并调用 `workflowService`。
3. `src/business_service/channel/events.py` + `foundational_service/messaging/channel_binding_event_publisher.py` — 同文件既定义事件常量又处理队列/发布，实现/常量耦合（Violation #1/#4）。
   - **Remediation**：将事件/Topic 常量抽到 `business_asset/channel_events.py`（或 JSON schema），Publisher/Monitor 仅引用；同时在 storage/events 索引确认引用地点，防止重复定义。
