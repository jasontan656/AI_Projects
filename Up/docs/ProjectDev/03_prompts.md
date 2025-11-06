# Prompts 模块详解

## 1. 目标
- 集中管理 Markdown 模板，为节点动作提供引用。
- 输出契约 `prompt-draft.json`，保证后端持久化一致。

## 2. 组件结构
| 组件 | 作用 | 路径 |
| ---- | ---- | ---- |
| PromptList | 模板列表、删除、选中 | src/components/PromptList.vue |
| PromptEditor | 模板编辑表单 | src/components/PromptEditor.vue |
| PromptCodeEditor | Codemirror 封装 | src/components/PromptCodeEditor.vue |

### 2.1 PromptList
- 数据源：Pinia `promptDraft.prompts`。
- 卡片信息：名称、更新时间。
- 操作：刷新（触发 `PipelineWorkspace.refreshPrompts`）、删除。

### 2.2 PromptEditor
- 表单字段：
  - `name`：可选，默认“未命名提示词”。
  - `markdown`：必填。
  - `editorLanguage`：`markdown` / `yaml` / `json`，用于切换 Codemirror 语言包。
- 操作按钮：保存（create/update）、新建（重置状态）。
- 成功保存后调用 `promptDraftStore.replacePrompts` 刷新列表。
- 使用 `toastMessage` + Element Plus 状态提示保存结果。

### 2.3 PromptCodeEditor 封装
- 基于 Codemirror 6：含行号、历史、占位符、语法高亮。
- 通过 Compartment 实现动态语言、只读、placeholder 切换。
- `updateListener` 负责向父组件回写 `modelValue`。

## 3. 数据流
```
promptDraft.prompts ← listPromptDrafts()
  │
  ├─ PromptList：选中/删除
  └─ PromptEditor：创建/更新，保存后刷新列表
```

## 4. API
- `listPromptDrafts(params)`：GET `/api/prompts`。
- `createPromptDraft(payload)`：POST，校验 Markdown 非空。
- `updatePromptDraft(id,payload)`：PUT。
- `deletePromptDraft(id)`：DELETE。

## 5. 契约文件
- `docs/contracts/prompt-draft.json`：字段 `id/name/markdown/createdAt`。
- 示例展示 Markdown 内容和 ISO 时间戳。

## 6. 待办与优化
1. 提供模板搜索、分组、标签管理。
2. 支持版本控制（diff、回滚）。
3. 与 NodeActionList 联动提示引用情况。
4. 引入 Markdown 预览（同屏/分屏）。
5. 增加变量占位符校验与模板语法指南。
