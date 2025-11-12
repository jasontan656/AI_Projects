# 技术策划（Tech Doc）· Session 00001 · compliance-audit

生成时间：2025-11-12（依据 01/03 文档与当前代码树；只给出文件级动作与接口边界，不含实现代码）

## 1. Background & Scope
- 目标：将 01（审计）与 03（回归护栏）落到可执行的“文件级”技术策划，服务于“行为不变”的重构。
- 范围：
  - Rise：移除上行依赖（BS→BL、F→BL/BS、BS→IE）、瘦身超大编排文件、保持 one_off 隔离。
  - Up：拆分过载组件、建立组件边界与命名/落位规则。
- 排除：业务新功能、端到端渠道联调、Secrets/Env 改动。

## 2. Tech Stack Overview（与本轮相关）
- 后端：Python 3.11 + FastAPI；依赖图/复杂度工具：ripgrep、import-linter、radon（只用于门禁，不进生产路径）。
- 前端：Vue 3 + Vite + Pinia；依赖环路检测：madge（只用于门禁）。
- 参考：
  - FastAPI 架构实践与示例模板（Context7：/fastapi-practices/fastapi_best_architecture；/jiayuxu0/fastapi-template）。
  - Pytest 组织与夹具最佳实践（Context7：/pytest-dev/pytest）。
  - Characterization Testing（Exa：Michael Feathers；DaedTech）。
  - 工具：madge（Exa，前端循环依赖）；import-linter（Exa，Python 导入约束）；radon（Exa，圈复杂度门禁）。

## 3. Module/File Change Matrix（文件级动作，不改行为）

### 3.1 Rise · 上行依赖与瘦身
- 场景：BS→BL 反向依赖（P0）
  - 现状：`src/business_service/conversation/service.py:16` 导入 `business_logic.workflow`。
  - 动作：
    1) 在 `src/business_service/conversation/` 下新增：
       - `channel_health.py`（频道健康与上报接口适配）
       - `runtime_dispatch.py`（RuntimeGateway/队列投递与重试编排）
       - `contracts_adapter.py`（入/出站契约中立化）
    2) `service.py` 保留为“编排壳”，只持有对上述子模块的组合；移除对 BL 的直接 import。
    3) 若需 BL 的数据结构/结果，改为通过上层注入或 DTO（见 4.1）。

- 场景：F→BL/BS 反向依赖（P0）
  - 现状：`src/foundational_service/persist/worker.py` 同时导入 `business_logic.workflow` 与 `business_service.workflow`；`integrations/memory_loader.py` 导入 `business_service.knowledge.*`；`messaging/channel_binding_event_publisher.py` 引用 `business_service.channel.events`。
  - 动作：
    1) 在 `src/foundational_service/contracts/` 下新增抽象边界：
       - `workflow_exec.py`：声明 `WorkflowExecutor`（Protocol/ABC），屏蔽 BL 类型；
       - `knowledge_io.py`：声明知识读写 DTO（不引用 BS）。
    2) `persist/worker.py` 改为依赖 `contracts.workflow_exec`；具体实现由上层在组合根注入。
    3) `integrations/memory_loader.py` 改为依赖 `contracts.knowledge_io` 的中立 DTO；具体实现由上层提供。
    4) `messaging/channel_binding_event_publisher.py` 改为使用 `contracts` 中的中立事件枚举/数据结构。

- 场景：BS→IE 依赖（P0）
  - 现状：`src/business_service/conversation/primitives.py` 导入 `interface_entry.telegram.adapters`。
  - 动作：
    1) 在 `src/business_service/conversation/` 新增 `adapters_core.py`（中立 DTO/转换门面）；
    2) `primitives.py` 仅面向中立 DTO；接口适配由入口层在“组合根”完成，向下传递中立结构。

### 3.2 Up · 组件拆分与落位
- 场景：过载组件（P1）
  - 现状：`PromptEditor.vue`/`NodeDraftForm.vue`/`WorkflowChannelForm.vue` 体量与职责过大。
  - 动作：
    - PromptEditor：
      - `src/components/prompt-editor/PromptMetaForm.vue`
      - `src/components/prompt-editor/PromptContentEditor.vue`
      - `src/components/prompt-editor/PromptPreviewPanel.vue`
    - NodeDraftForm：
      - `src/components/node-draft/NodeFormShell.vue`
      - `src/components/node-draft/NodeFieldsBasic.vue`
      - `src/components/node-draft/NodeSubmitActions.vue`
    - WorkflowChannelForm：
      - `src/components/channel-form/ChannelFormShell.vue`
      - `src/components/channel-form/ChannelFieldsBasic.vue`
      - `src/components/channel-form/ChannelSubmitActions.vue`
  - 说明：父组件仅编排 `props/emits`，逻辑下沉至子组件与 `services/`。

## 4. Function & Interface Summary（边界与职责）

### 4.1 Rise · 抽象边界
- `foundational_service/contracts/workflow_exec.py`
  - 责任：定义执行入口（如 `execute(workflow_id, payload, *, timeout_ms)`）；
  - 输入/输出：中立 DTO；
  - 依赖：无（由上层注入具体实现）。
- `foundational_service/contracts/knowledge_io.py`
  - 责任：定义知识快照读取/写入接口与 DTO；
  - 输入/输出：不暴露 BL/BS 具体类型。
- `business_service/conversation/adapters_core.py`
  - 责任：定义与入口层解耦的会话契约 DTO；
  - 依赖：仅标准库/typing；不得 import `interface_entry.*`。
- `business_service/conversation/service.py`
  - 责任：保留“薄编排壳”；组合 `channel_health/runtime_dispatch/contracts_adapter`；
  - 副作用：调用下层（F/PU）或外部队列；不直接依赖 BL。

### 4.2 Up · 组件边界
- 子组件职责：
  - `*FormShell.vue`：布局与外壳；
  - `*FieldsBasic.vue`：表单字段与校验；
  - `*SubmitActions.vue`：保存/提交触发与反馈；
- 交互：父组件通过 `emits` 转发保存结果与错误，服务调用在 `services/` 内完成。

## 5. Best Practices & Guidelines（参考与采纳）
- Clean/分层边界参考：FastAPI 最佳架构与模板（Context7）。
- 回归表征测试：Michael Feathers/DaedTech（Exa）。
- 依赖环路检测：madge（JS/TS）、import-linter（Python）（Exa）。
- 复杂度门禁：radon（Exa）。

## 6. File & Repo Actions（不含实现，仅文件级）
- Rise：
  - 新增：`src/foundational_service/contracts/workflow_exec.py`、`src/foundational_service/contracts/knowledge_io.py`、
    `src/business_service/conversation/{channel_health.py,runtime_dispatch.py,contracts_adapter.py,adapters_core.py}`。
  - 修改：`src/foundational_service/persist/worker.py`、`src/foundational_service/integrations/memory_loader.py`、
    `src/foundational_service/messaging/channel_binding_event_publisher.py`、`src/business_service/conversation/primitives.py`、
    `src/business_service/conversation/service.py`（瘦身为壳）。
  - 不动：`src/one_off/**`（保持隔离）。
- Up：
  - 新增目录：`src/components/prompt-editor/`、`src/components/node-draft/`、`src/components/channel-form/`（见 3.2）。
  - 修改：拆分父组件并迁移样式/校验逻辑至子组件；更新 import 路径与 `props/emits`。
- 工具/配置（仅策划，按 03 承接到脚本或 CI）：
  - 后端：`import-linter` 规则文件（如 `.importlinter` 或 `pyproject.toml` 段落）；`radon` 配置（`setup.cfg/pyproject.toml`）。
  - 前端：`madge` 脚本（`package.json` 的 `scripts` 段）；可选 `madge` 配置。

## 7. Risks & Constraints
- 允许清单（allowlist）短期存在：
  - 风险：误阻断当前迁移；
  - 缓解：仅对“新增违例”失败，存量以 allowlist 记录，并设定 sunset 日期。
- CI 负担：
  - 风险：护栏脚本增加流水线时长；
  - 缓解：P0 护栏进 PR（required checks），P1 放夜间；后续再合并。
- 组件拆分风险：
  - 风险：父子组件边界不清导致反复移动逻辑；
  - 缓解：在 Docs 记录 props/emits 契约，先“壳分离”，再逐步下沉逻辑。

## 8. Implementation Decisions（无开放项）
- 分层边界以“向下依赖”为硬约束；禁止 BS→BL、F→BL/BS、BS→IE。
- `service.py` 保留为薄编排壳；业务细节下沉到同目录子模块。
- Foundational 与 BL/BS 之间通过 `contracts/*` 的中立接口通讯；实现由上层注入。
- Up 组件按“壳/字段/提交动作”三段式落位；父组件不再直接持有复杂逻辑。
- 护栏以 03 测试计划为准：P0 进 PR，P1 夜间；阈值“基线+2%”起步，重构完成后逐步收紧。

---
引用索引（记录来源标识，便于追溯）：
- Context7：/fastapi-practices/fastapi_best_architecture；/jiayuxu0/fastapi-template；/pytest-dev/pytest
- Exa：Michael Feathers—Characterization Testing；DaedTech—Characterization Tests；madge（JS/TS 循环依赖）；import-linter（Python 导入约束）；radon（复杂度 CLI）

