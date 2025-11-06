# Nodes 模块详解

## 1. 目标
- 通过节点草稿定义工作流脚本动作。
- 输出契约供后端实现。
- 兼容旧 `systemPrompt` 数据。

## 2. 组件结构
| 组件 | 作用 | 路径 |
| ---- | ---- | ---- |
| NodeSubMenu | Nodes 子菜单入口 | src/components/NodeSubMenu.vue |
| NodeList | 节点列表展示、删除、选中 | src/components/NodeList.vue |
| NodeDraftForm | 节点表单主体 | src/components/NodeDraftForm.vue |
| NodeActionList | 节点动作编辑器 | src/components/NodeActionList.vue |
| nodeActions 工具 | 动作创建/序列化工具 | src/utils/nodeActions.js |

### 2.1 NodeList
- 仅在 manage 视图渲染，接收 Pinia `pipelineDraft.nodes`。
- 卡片内容：名称、更新时间、LLM 状态。
- 操作：刷新（触发父组件 `refreshNodes`）、删除（冒泡到 `PipelineWorkspace` 调用 API）。
- 样式：宽度 320px，支持滚动，保持与右侧表单等高。

### 2.2 NodeDraftForm
- 字段：
  - `name`：必填。
  - `allowLLM`：布尔开关，控制动作可用性。
  - `actions`：`NodeActionList` 双向绑定。
- `layout` 属性：`split`（manage 模式双列布局）/`full`（create 模式居中宽屏）。
- `handleSubmit`：
  1. 校验名称非空；
  2. 校验 `allowLLM=false` 时无 `prompt_append`；
  3. 组装 payload，调用 `createPipelineNode` 或 `updatePipelineNode`；
  4. 刷新列表并根据返回 ID 选中对应节点；
  5. 触发 `saved` 事件，为父组件切换视图提供钩子。
- `handleOpenActionSettings`：右键“查看设置”时弹出 Element Plus `ElMessageBox`，展示 JSON 配置。
- `watch(form.allowLLM)`：切换时同步更新动作的 `disabled` 属性。

### 2.3 NodeActionList
- `modelValue` 为动作数组。
- 提供按钮与右键菜单：
  - 添加提示词动作。
  - 上移/下移。
  - 删除。
  - 复制（使用 uuid 生成新 id）。
  - 右键菜单项：查看设置（触发外部弹窗）、删除、复制。
- `commit()`：保证顺序重新编号，并根据 `allowLlm` 标记 `disabled`。
- 模板预览：从 `promptTemplates` 中获取 Markdown，转换为 HTML（做基础转义）。

### 2.4 工具函数（nodeActions.js）
- `ACTION_TYPES`：`prompt_append`、`tool_invoke`、`emit_output`。
- `sanitizeConfig`：限制 `config` 字段，仅保留 `templateId`、`legacyText`、`inputMapping`、`disabled`。
- `normalizeActions`：将旧数据或 `systemPrompt` 转为动作数组。
- `serializeActionsForApi`：提交给后端时统一结构。
- `composeSystemPromptFromActions`：用于兼容旧字段。

### 2.5 视图切换流程
1. 点击左侧 `Nodes`：在导航右方弹出 `NodeSubMenu` 悬浮卡片，主体区域保持当前视图。
2. 子菜单选择：
   - **新建节点** → 切换到 `nodesViewMode=create`，表单全屏展示；
   - **查看已创建节点** → 切换到 `nodesViewMode=manage`，显示 NodeList + NodeDraftForm 双列。
3. 表单保存成功后自动调用父组件 `startManageNodes()`，刷新列表并停留在 manage 视图，可通过“返回节点菜单”按钮再次唤起子菜单。

## 3. Pinia 数据流
```
pipelineDraft.nodes ← listPipelineNodes()
  │
  ├─ NodeSubMenu → 决定呈现的视图模式
  ├─ NodeList（manage 模式）：显示/删除
  └─ NodeDraftForm（create/manage）：编辑，提交后触发 replaceNodes() 并发出 saved 事件
```

## 4. API 交互
- `listPipelineNodes(params)`：GET `/api/pipeline-nodes`，支持分页与状态过滤。
- `createPipelineNode(payload)`：POST，自动写入 `systemPrompt`。
- `updatePipelineNode(id, payload)`：PUT，可部分更新。
- `deletePipelineNode(id)`：DELETE。

## 5. 契约同步
- 保存/更新完成后需更新 `docs/contracts/pipeline-node-draft.json`。
- 文件描述字段：`id/name/allowLLM/actions/systemPrompt/createdAt` 等。
- 示例包含两个 `prompt_append` 动作。

## 6. 待办与优化方向
1. 实现 `tool_invoke`、`emit_output` 配置 UI。
2. 动作预览提供 Markdown 渲染 + 原文切换。
3. 表单支持草稿自动保存、版本回滚。
4. 列表支持过滤/排序、批量操作。
5. 将动作设置弹窗与右键菜单深度集成，使其可直接编辑。
