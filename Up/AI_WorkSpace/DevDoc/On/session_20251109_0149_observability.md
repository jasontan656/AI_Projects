# Workflow 可观测性与可视化扩展（session_20251109_0149）

## 背景与范围
- **目标**：落实报告 M3，提供运行中 workflow 的日志、状态可视化、变量/工具面板，支撑调试与运维。
- **范围**：
  - 新增实时日志视图：订阅 Rise SSE/WebSocket（如 `/api/workflows/{id}/logs/stream`），显示任务轨迹、节点执行耗时、错误。
  - 画布/可视化：在 Workflow Builder 中增加“画布”Tab，使用 Vue Flow 或自建 DAG 渲染节点顺序（可初期用静态连接）。
  - Variables/Tools 面板：让用户浏览可用变量、工具（来自 `src/components/VariablesPanel.vue`、`NodeActionList.vue`），并与 workflow 绑定。
  - 日志检索与下载：支持按时间段过滤、导出 JSON/文本；与 Telegram 测试结合，快速定位问题。

## 模块划分
| 组件/文件 | 作用 |
| --- | --- |
| `src/services/logService.js` | SSE/WebSocket 客户端，提供 `subscribeLogs(workflowId)`、`fetchHistory(params)`。 |
| `src/components/WorkflowLogStream.vue` | 实时日志列表，支持过滤条件、暂停/恢复。 |
| `src/components/WorkflowCanvas.vue` (扩展) | 在 workflow 详情中展示 DAG，仅读或简单编辑。 |
| `src/components/VariableCatalog.vue` | 变量/上下文列表，可点击复制；数据来源于 `/api/workflows/{id}/variables`. |
| `src/components/ToolCatalog.vue` | 展示可用工具（未来 NodeActionList 需要），用于帮助 Ops。 |

## 交互流程
1. **日志 Tab**  
   - 用户切换到“日志”→ `logService.subscribeLogs(workflowId)` 建立 SSE/WebSocket，流式展示事件（timestamp、node、status、payload）。  
   - 可设置过滤条件（节点/等级），或暂停流（并保留缓冲）。  
   - 提供“导出最近 X 条”按钮，调用 `fetchHistory` 下载 JSON。
2. **画布 Tab**  
   - 基于 `workflowStore` 的 nodeSequence 渲染 DAG；节点卡片展示提示词引用、策略摘要。  
   - 支持鼠标悬浮查看详情，后续可扩展编辑能力（非必需）。  
3. **变量/工具 Tab**  
   - 显示 workflow 可用的变量、上下文、工具；使用 `ElTable` 或列表分组。  
   - 允许复制变量 key，帮助编写节点/提示词。  
4. **日志与 Telegram 调试联动**  
   - 在 Channel Test Panel 或 Telegram 测试后，日志视图自动滚动到最新事件，并显示对应 correlationId。

## Success Path & Core Workflow
1. **订阅成功**：进入日志 Tab → SSE 连接建立 → UI 展示“已连接”绿标；收到事件后立即渲染，并保留最近 N 条。
2. **过滤/暂停**：用户设置过滤器 → 新消息按条件显示；点击“暂停”则停止滚动但继续缓冲，点击“恢复”再统一渲染。
3. **导出**：点击“导出最近 200 条”→ 调用 `fetchHistory({ limit: 200 })` → 触发浏览器下载。
4. **画布渲染**：workflow 更新后触发画布刷新；节点卡片展示最新提示词/策略，连线箭头表示执行顺序。
5. **变量/工具加载**：进入 Tab 时调用 `/variables`、`/tools`，成功后按组展示，并提供搜索。

## Failure Modes & Defensive Behaviors
- **SSE/WebSocket 断线**：显示黄色提示“日志连接中断，重试中”，并进行指数退避重连；若用户主动断开则保持离线状态。
- **日志洪流**：为防 UI 卡顿，限制浏览器内存（例如最多保留 1000 条），超限后裁剪并提示。
- **画布渲染失败**：若数据不完整（缺节点/提示词），展示空态并提示到 Workflow Builder 修复，而不是报错。
- **变量/工具接口异常**：提示“无法加载变量目录”，提供刷新按钮；不要阻塞其他 Tab。
- **导出失败**：如果 `fetchHistory` 返回错误，弹窗显示错误码并建议稍后重试。

## Constraints & Acceptance（GIVEN / WHEN / THEN）
- GIVEN SSE/WebSocket 成功建立，WHEN 后端推送 workflow 事件，THEN UI 必须在 1 秒内渲染最新一条并更新时间戳。
- GIVEN 用户开启过滤器（按节点/级别），WHEN 新事件不满足条件，THEN 不显示在列表，但仍计入导出数据。
- GIVEN 日志连接断开 3 次仍失败，WHEN 状态栏刷新，THEN 要显示“持续失败，点击手动重连”按钮。
- GIVEN workflow 结构发生变更，WHEN 用户切换到画布 Tab，THEN 渲染顺序应即时更新（无旧数据闪烁）。
- GIVEN 用户点击“导出最近 200 条”，WHEN 请求成功，THEN 浏览器触发文件下载，文件名包含 workflowId+时间戳。
