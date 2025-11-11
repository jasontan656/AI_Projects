# Rise 后端全量落地计划（实时数据 & 实际 API）

## 背景与目标
- 立即恢复“真实”后端能力：会话流必须返回真实 LLM 输出，Pipeline/Tool/Stage API 必须使用 MongoDB 及 Redis 持久化。
- `openai_agents/agent_contract` 与 `KnowledgeBase/*` 中的合同需被实时加载并驱动 orchestrator，不再允许占位返回。
- 重构目标改为“一步到位”：完成实现即可视作测试通过，无须灰度阶段或占位壳。

## 目标能力列表
1. **会话编排（Telegram/HTTP）**
   - 读取 stage manifest、runtime contract。
   - 触发 OpenAI Responses API，处理 delta/完结事件。
   - 维护 `cached_state.json`、Redis（短期上下文）与 Mongo（长期历史）。
2. **Tool/Stage/Workflow 配置**
   - ToolDefinition / StageDefinition / WorkflowDefinition CRUD。
   - 允许从 `openai_agents/agent_contract` 导入并写回新版结构。
3. **Pipeline 节点管理**
   - 管理节点及其动作清单、变量映射，使用 Mongo 真实集合。
   - 提供对前端 Up 的实时读写接口。
4. **监控与日志**
   - 记录每次 orchestrator 执行的 telemetry、错误栈。
   - 支持快速追踪 LLM 请求与响应。

## 实施步骤
1. **恢复数据模型**
   - 重建 `PipelineNode`, `ToolDefinition`, `StageDefinition`, `WorkflowDefinition` Pydantic v2 模型。
   - 建立 Mongo 集合 `pipeline_nodes`, `tools`, `stages`, `workflows`，配置索引。
2. **重写业务服务**
   - `PipelineNodeService`/`AsyncPipelineNodeService` 使用真实 repository 逻辑，校验名称冲突、返回最新版本。
   - 引入 `ToolService`, `StageService`, `WorkflowService`。
3. **实现 Workflow Orchestrator**
   - 解析 workflow definition → 阶段顺序 → 调用 OpenAI Responses。
   - 处理 Redis（会话 key: `chat:{chat_id}:summary`）读写、Mongo `chat_history` upsert。
   - 失败时回滚最新状态并记录 telemetry。
4. **接口层调整**
   - `/api/pipeline-nodes`, `/api/tools`, `/api/stages`, `/api/workflows`, `/api/workflows/apply`, `/api/workflows/simulate`.
   - Telegram webhook 路径进来后调用 orchestrator。
5. **知识库加载**
   - `KnowledgeSnapshotService` 补充加载 stage 所需 dictionary/service index，并在 orchestrator 中注入。
6. **实测**
   - 准备样例 manifest + knowledge YAML + Tool/Stage 数据 → 实际调用 Telegram/HTTP 触发多阶段流程 → 观察日志、数据库。

## 成功路径（Success Path & Core Workflow）
1. **配置导入**
   - 通过 `/api/workflows/import` 导入包含 stage manifest、tool/stage 定义的 ZIP；系统写入 Mongo 并返回版本 ID。
2. **会话执行**
   - Telegram update → inbound 净化 → orchestrator 读取 workflow → 依序执行阶段：
     - 访问 Redis 获取最近 20 条上下文。
     - 调用 OpenAI Responses（store=true，关闭占位）。
     - 校验输出符合 `stage_runtime_contract.md`。
     - 更新 cached_state/Redis/Mongo。
3. **结果返回**
   - orchestration 成功 → 生成最终 `assistantReply` → outbound 发送至 Telegram → API 返回 200。
4. **前端联动**
   - `/api/pipeline-nodes` 列表展示真实数据；操作新增/修改/删除实时落库。
   - `/api/workflows/apply` 触发一次 workflow-run，返回 stage telemetry、LLM usage。

## 失败模式与防御行为
- **OpenAI 响应结构不符合合同**：记录 `workflow.stage_validation_failed`，将错误消息写入 telemetry，同时保留 cached_state 未变；向客户端返回 500 并附详细错误路径。
- **知识库缺失或 YAML 解析失败**：在 orchestrator 启动前检测，若缺文件/字段则阻断执行并提示缺失路径。
- **Redis/Mongo 不可达**：立即抛出 `ServiceUnavailable`，阻止执行，提示检查依赖；不再 fallback 内存。
- **重复/循环阶段**：保存 workflow 时校验 DAG，无效则返回 422。
- **工具定义缺失**：执行阶段发现引用不存在工具 → 抛出 `StageToolNotFound`，telemetry 标记 `missing_tool_id`。
- **LLM 超时/配额**：捕获异常，记录 telemetry，并返回 503 允许客户端重试。

## 约束与验收（GIVEN / WHEN / THEN）
- **GIVEN** Mongo/Redis 配置正确 & 已导入 workflow，**WHEN** 调用 Telegram 或 `/api/workflows/apply`，**THEN** orchestrator 必须完成全部阶段并返回含 LLM 实际输出的响应。  
- **GIVEN** 工具/阶段定义缺失，**WHEN** 保存 workflow，**THEN** 返回 422 并列出缺少的工具/阶段 ID。  
- **GIVEN** LLM 产生不符合合同的 JSON，**WHEN** orchestrator 验证失败，**THEN** 立即终止流程，返回 500，telemetry 记录 `validation_error_path`。  
- **GIVEN** 用户删除 Pipeline 节点并为同名新建，**WHEN** 列表刷新，**THEN** Mongo 中只保留新记录且版本号重置为 1。  
- **GIVEN** Redis 宕机，**WHEN** 调用 orchestrator，**THEN** 返回 503 `REDIS_UNAVAILABLE`，不进入 LLM 调用。  
- **GIVEN** 通过 `/api/workflows/import` 导入 ZIP，**WHEN** 成功写入，**THEN** 接口返回新版本号并能通过 `/api/workflows/{id}` 查询详细结构。

## 行动项
- 恢复并重写 `business_service`、`business_logic`、`interface_entry` 相关模块，删除占位逻辑。
- 启动真实 Redis/Mongo/OpenAI 凭据，准备测试数据。
- 编写最小集成测试脚本，验证从导入 → 会话 → 数据落库全链路。
- 后续所有开发以“实时执行”为准，不再引入占位阶段。*** End Patch
