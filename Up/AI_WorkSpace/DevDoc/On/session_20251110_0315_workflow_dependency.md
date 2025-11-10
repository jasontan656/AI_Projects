# Workflow 依赖守卫方案（session_20251110_0315）

## 背景
- 当前 Workspace 允许用户在 Nodes、Prompts 均为空时直接进入 Workflow Builder 并保存空 workflow，导致后端存在无节点的编排记录。
- 业务定义要求：Workflow 必须串联至少一个已发布节点；节点本身又依赖既有 Prompt/变量。昨夜排查确认问题集中于 `src/views/WorkflowBuilder.vue` 与 `src/components/WorkflowEditor.vue` 未做前置守卫。

## 目标
1. Workflow 在 `pipelineStore.nodeCount === 0` 或 `promptStore.promptCount === 0` 时必须阻断创建流程，并引导用户回到 Nodes/Prompts。
2. 保存/发布流程要验证 `nodeSequence` 与 `promptBindings` 引用的实体真实存在，防止孤儿引用落库。
3. 后端 `/api/workflows` 在接收到空序列时直接拒绝，杜绝漏网请求。

## 现状与问题定位
| 层级 | 文件 | 问题 |
| --- | --- | --- |
| UI 入口 | `src/views/WorkflowBuilder.vue:5-84` | 永远渲染 `<WorkflowEditor>`，未检测资产库存。 |
| 表单 | `src/components/WorkflowEditor.vue:32-120` | `canSave` 仅校验名称/dirty，未验证 `nodeSequence`；节点被删后依旧可以保存。 |
| Store | `src/stores/workflowDraft.js:60-115` | `saveCurrentWorkflow` 不检查 payload，任何空数组均可直达后端。 |
| API | `src/services/workflowService.js:3-80` | `sanitizeWorkflowPayload` 默认返回空序列，后端未对空值报错。 |

## 设计方案
### 入口守卫（WorkflowBuilder）
- 引入 `const hasNodes = computed(() => pipelineStore.nodeCount > 0); const hasPrompts = computed(() => promptStore.promptCount > 0);`。
- 在 `<WorkflowEditor>` 外层加上：
  ```vue
  <div v-if="!hasNodes || !hasPrompts" class="workflow-builder__guard">
    <el-empty description="Workflow 需要至少 1 个节点和 1 个提示词">
      <el-button @click="goToNodes">前往 Nodes</el-button>
      <el-button @click="goToPrompts" text>前往 Prompts</el-button>
    </el-empty>
  </div>
  <WorkflowEditor v-else ... />
  ```
- `goToNodes`/`goToPrompts` 调用父级 `PipelineWorkspace` 的导航（通过 emit 或在 store 中设置 `activeNav`），确保用户能快速回填资产。

### 表单校验（WorkflowEditor）
- 扩展 `canSave = computed(() => form.name.trim() && form.nodeSequence.length > 0 && validateBindings())`。
- 实现 `validateBindings()`：
  ```js
  const nodeIds = new Set(props.nodes.map((n) => n.id));
  const promptIds = new Set(props.prompts.map((p) => p.id));
  const missingNodes = form.nodeSequence.filter((id) => !nodeIds.has(id));
  const missingPrompts = Object.entries(nodePromptMap)
    .filter(([nodeId, promptId]) => promptId && !promptIds.has(promptId));
  ```
  - 若 `missingNodes.length > 0`，弹出 `ElMessage.error("以下节点已不存在: ...")` 并返回 false。
  - 若 `missingPrompts.length > 0`，清理对应绑定并提示。
- 在 `handleSave` 内调用 `if (!validateBindings()) return;`，确保任何脏数据都被阻断。

### Store / API 兜底
- `src/stores/workflowDraft.js`：在构造 `payload` 之后加入：
  ```js
  if (!payload.nodeSequence?.length) {
    this.setError("Workflow 需要至少一个节点");
    throw new Error("WORKFLOW_NODE_REQUIRED");
  }
  ```
- `src/services/workflowService.js`：
  - `sanitizeWorkflowPayload` 结束前断言 `normalized.nodeSequence.length > 0`，否则抛错。
  - `promptBindings` 过滤掉无效条目（缺 nodeId / promptId）。
- 视情况在后端 `/api/workflows` 增加校验（不在本 repo，但需要同步需求）。

## Success Path & Core Workflow
1. 用户在 Nodes 菜单创建至少 1 个节点（节点内部已绑定 Prompt/变量）。
2. 用户在 Prompts 菜单创建至少 1 个提示词模板。
3. 回到 Workflow：守卫检测到 `hasNodes && hasPrompts` 为 true，允许打开编辑器。
4. 在 WorkflowEditor 中选择节点顺序，绑定提示词，设置策略，点击“保存草稿”。
5. `validateBindings()` 通过 → `saveCurrentWorkflow` 提交 → 后端成功落库。
6. Workflow 列表更新状态，后续可发布/绑定渠道。

## Failure Modes / Defensive Behaviors
- **缺少节点**：`hasNodes === false` → 显示空态卡片，禁用保存钮。
- **缺少提示词**：同上，提示“请先创建 Prompt”。
- **节点被删除**：`validateBindings()` 检测到缺失 → 自动移除该节点并提示，保存失败。
- **提示词被删除**：同理，清空该节点的 prompt 绑定并警告。
- **并发冲突**：若 `saveCurrentWorkflow` 在提交前检测到 `payload.nodeSequence.length === 0`，直接抛出错误，不调用 API。
- **后端兜底**：`normalizePayload` 发现空序列→ throw，防止前端遗漏校验。

## 约束与验收（GIVEN / WHEN / THEN）
1. **GIVEN** 节点或提示词数量为 0，**WHEN** 用户打开 Workflow 标签，**THEN** UI 只显示引导卡片且“保存草稿”按钮不可用。
2. **GIVEN** 用户删除了 Workflow 正在引用的节点，**WHEN** 再次进入 WorkflowEditor，**THEN** 该节点会被自动从 `nodeSequence` 移除并提示“节点不存在”。
3. **GIVEN** Workflow 包含至少一个节点且提示词绑定有效，**WHEN** 点击“保存草稿”，**THEN** 请求体必须包含非空 `nodeSequence`，后端成功返回 2xx。
4. **GIVEN** 有人尝试调用 `/api/workflows` 创建空序列，**WHEN** payload 中 `nodeSequence` 长度为 0，**THEN** API 返回 4xx，并记录错误码 `WORKFLOW_NODE_REQUIRED`。

## 后续跟进
- 若需支持“节点 = Workflow”单层模型，需另开设计讨论（当前不在 scope）。
- 调整完前端后，需要在文档 / Onboarding 中明确“先建 Nodes/Prompts → 再建 Workflow”流程。
