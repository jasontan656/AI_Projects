# Up 工作流 GUI 概览

该文档聚焦产品目标与整体信息架构，为后续细化文档（布局、Nodes、Prompts 等）提供统一视角。

## 产品定位
- **类型**：内部工作流运维 GUI。
- **核心目标**：
  1. 用可视化方式编排节点脚本（支持 LLM、工具、输出动作等）。
  2. 集中管理提示词模板，确保与节点引用一致。
  3. 快速检索运行时上下文变量，辅助排查。
  4. 追踪实时日志，帮助 Ops/研发定位异常。
- **契约策略**：前端作为“事实来源”，通过 `docs/contracts/*.json` 输出草稿结构，FastAPI 后端遵循该格式实现接口。

## 技术栈快照
- **前端框架**：Vue 3 (Composition API) + Vite。
- **状态管理**：Pinia。
- **UI 组件**：Element Plus。
- **画布**：@vue-flow/core。
- **编辑器**：Codemirror 6。
- **辅助库**：@vueuse/core、uuid。

## 核心模块一览
| 模块 | 说明 | 关键组件 |
| ---- | ---- | ---- |
| Nodes | 节点脚本化与契约输出 | `NodeList`、`NodeDraftForm`、`NodeActionList` |
| Prompts | 提示词模板集中管理 | `PromptList`、`PromptEditor`、`PromptCodeEditor` |
| Workflow | 工作流画布（占位） | `WorkflowCanvas` |
| Variables | 变量面板 | `VariablesPanel` |
| Logs | 实时日志查看 | `LogsPanel` |
| Settings | 系统设置占位 | `el-empty` |

后续章节按功能拆分，说明界面结构、状态流转、待办提升点等。
