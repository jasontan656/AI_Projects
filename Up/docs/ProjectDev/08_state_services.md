# 状态与服务层说明

## 1. Pinia Stores

### 1.1 pipelineDraft（src/stores/pipelineDraft.js）
- **状态**：`nodes`、`selectedNodeId`。
- **核心方法**：
  - `replaceNodes(nodes)`：覆盖节点集合，并在选中节点不存在时重置 selection。
  - `addNodeDraft(node)` / `removeNodeDraft(id)`：增删单个草稿。
  - `resetSelection()`：清空选中。
  - `cloneSelectedActions()`：深拷贝动作列表，供 UI 使用。
- **数据预处理**：
  - `prepareNodeDraft()` 调用 `normalizeActions()`，确保 `actions` 有序。
  - 若仅有 `systemPrompt`，转换为单个 `prompt_append`。

### 1.2 promptDraft（src/stores/promptDraft.js）
- **状态**：`prompts`、`selectedPromptId`。
- **方法**：`replacePrompts`、`removePromptDraft`、`setSelectedPrompt`、`resetSelection`。

## 2. 工具函数
- `src/utils/nodeActions.js`：
  - `sanitizeConfig()`：限制 `config` 字段。
  - `createPromptAppendAction()`：新建动作。
  - `normalizeActions()` / `serializeActionsForApi()` / `composeSystemPromptFromActions()`。

## 3. 服务层

### 3.1 pipelineService（src/services/pipelineService.js）
- **请求封装**：统一请求头、错误处理。
- **函数**：
  - `listPipelineNodes(params)`
  - `createPipelineNode(payload)`：自动生成 `systemPrompt`。
  - `updatePipelineNode(id, payload)`：支持部分字段更新。
  - `deletePipelineNode(id)`
- **辅助函数**：`buildSystemPrompt(actions,fallback)` 用于兼容旧数据。

### 3.2 promptService（src/services/promptService.js）
- 操作与 pipelineService 类似，提供 `list/create/update/delete`。
- `sanitize()` 确保字符串字段去除多余空格。

## 4. 契约文件
- `docs/contracts/pipeline-node-draft.json`：
  - `actions[].config` 包含 `templateId/legacyText/inputMapping/disabled`。
  - 示例展示由动作生成的 `systemPrompt`。
- `docs/contracts/prompt-draft.json`：
  - 字段 `id/name/markdown/createdAt`。

## 5. 环境变量
- API 基础地址从 `import.meta.env.VITE_API_BASE_URL` 读取，默认 `http://localhost:8000`。
- 可在 `.env.development` 中覆盖。

## 6. 后续优化
1. 引入统一的 API 错误格式，方便 UI 显示详细信息。
2. 将 `request` 方法抽象为独立模块，支持拦截器、重试。
3. 为 Pinia store 添加持久化或缓存策略（如 localStorage）。
4. 引入 TypeScript / Zod 校验，增强类型安全。
5. 补充单元测试（Vitest）验证序列化、转换逻辑。
