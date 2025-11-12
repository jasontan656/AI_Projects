# Session 00001 · compliance-audit (Assessment Focus · Full Rewrite)

Generated at: 2025-11-12

说明：本文件为“审计/盘点现状”版本，仅列出结构合规相关的发现（Findings）、证据（Evidence）、影响（Impact）与优先级（Priority）。不包含未来方案与改造设计；若需进入方案阶段，将在收到明确指示后另行编写。

## Scope
- 范围：对照 `AI_WorkSpace/PROJECT_STRUCTURE.md`、`Rise/AGENTS.md`、`Up/AGENTS.md`，检查分层依赖、目录落位、文件职责粒度与（项目仓库内的）文档痕迹。
- 不在范围：安全/合法性、零信任、网关/WAF 等非结构性议题。
- 明确排除：整棵 `AI_WorkSpace\` 树（仅用于元信息与 AI 产物，不属于项目代码）；本审计只读取/写入 `Requirements` 与 `session_notes`，不将 `AI_WorkSpace` 作为被审计对象。
- 参考（记录 Context7/Exa 引用 ID，用于可追溯）：
  - Context7: `/fastapi-practices/fastapi_best_architecture`, `/jiayuxu0/fastapi-template`
  - Exa: `https://www.scrums.com/checklists/modernize-your-legacy-software`, `https://nix-united.com/blog/legacy-application-modernization-strategies/`, `https://ardura.consulting/our-blog/modernizing-legacy-systems-when-to-rebuild-refactor-or-replace/`

## Findings (with Evidence, Impact, Priority)

1) Business Service 反向依赖 Business Logic · Priority P0
- Evidence
  - path: `src/business_service/conversation/service.py:16`
  - code: `from business_logic.workflow import WorkflowRunResult, WorkflowStageResult`
- Impact
 - 违反“自上而下单向依赖”的架构约束（Business Service 不应依赖 Business Logic），削弱可替换性与可测试性，增加变更扩散风险。

2) Foundational 反向依赖 Business Logic/Service · Priority P0
- Evidence
  - path: `src/foundational_service/persist/worker.py:12`
  - code: `from business_logic.workflow import WorkflowExecutionContext, WorkflowOrchestrator, WorkflowRunResult`
  - path: `src/foundational_service/persist/worker.py:13`
  - code: `from business_service.workflow import StageRepository, WorkflowRepository`
  - path: `src/foundational_service/integrations/memory_loader.py:10-11`
  - code: `from business_service.knowledge import KnowledgeSnapshotService` / `from business_service.knowledge.models import AssetGuardReport, SnapshotResult`
  - path: `src/foundational_service/messaging/channel_binding_event_publisher.py:10`
  - code: 引用 `business_service.channel.events`
- Impact
  - 基础层（Foundational）不应上行依赖业务逻辑/业务服务；该类依赖提高层间耦合，阻碍抽换与复用。

3) Business Service 依赖 Interface/Entry 适配器 · Priority P0
- Evidence
  - path: `src/business_service/conversation/primitives.py:9`
  - code: `from interface_entry.telegram.adapters import append_streaming_buffer, telegram_update_to_core`
- Impact
  - 业务服务层不应引用入口适配器（协议/界面细节应停留在入口层），导致业务层携带界面形态，降低可移植性。

4) 超大“胖文件”且多职责混杂（后端） · Priority P0
- Evidence
  - path: `src/business_service/conversation/service.py`
  - size: 约 1286 行；聚合频道健康、Runtime 网关、Pipeline、入/出站契约、重试与观测等多种职责。
- Impact
  - 评审与测试困难；任何小改动都可能牵动多处逻辑，极易产生回归。

5) Up 组件过度承载（前端） · Priority P1
- Evidence
  - `Up/src/components/PromptEditor.vue` ≈ 437 行：混合布局、表单校验、编辑器状态与样式切换；
  - `Up/src/components/NodeDraftForm.vue` ≈ 396 行；`Up/src/components/WorkflowChannelForm.vue` ≈ 388 行。
- Impact
  - 单组件承担多变更原因（UI 布局、业务校验、网络调用），可复用与测试难度大；与“窄职责+文档契约”不符。

6) Up 文档缺口 · Priority P2
- Evidence
  - `Up/docs/ProjectDev` 未检到 “WorkflowBuilder/PromptEditor” 的父子组件契约说明（orchestrated 子组件清单/事件契约）。
- Impact
  - Orchestrator 组件边界不清晰，影响后续拆分与接入的一致性。

7) one_off 与核心路径隔离（合规） · Info

## Supplemental Evidence — Largest Files（行数）
- 后端 Top
  - 1286: `src/business_service/conversation/service.py`
  - 731: `src/interface_entry/bootstrap/application_builder.py`
  - 575: `src/interface_entry/http/workflows/routes.py`
  - 507: `src/project_utility/logging.py`
  - 400: `src/interface_entry/http/dependencies.py`
  - 392: `src/interface_entry/http/channels/routes.py`
  - 383: `src/foundational_service/persist/redis_queue.py`
  - 380: `src/interface_entry/telegram/handlers.py`
  - 368: `src/foundational_service/persist/worker.py`
  - 362: `src/foundational_service/contracts/telegram.py`
  - 360: `src/foundational_service/telemetry/bus.py`
- 前端 Top
  - 832: `Up/src/views/PipelineWorkspace.vue`
  - 454: `Up/src/components/WorkflowEditor.vue`
  - 449: `Up/src/components/NodeActionList.vue`
  - 437: `Up/src/components/PromptEditor.vue`
  - 396: `Up/src/components/NodeDraftForm.vue`
  - 388: `Up/src/components/WorkflowChannelForm.vue`
  - 274: `Up/src/views/WorkflowBuilder.vue`
- Evidence
  - `src/one_off/*` 目录未见被核心执行路径 import 的反向引用。
- Impact
  - 当前符合“核心不依赖一次性脚本”的要求。

## Recommended Priority (Behavior-Preserving)
- P0（当周内建议处理）：
  - 移除 `business_service → business_logic` 的直接依赖（保留接口/DTO 或由更高层注入结果）。
  - 将 `conversation/service.py` 瘦身为编排壳，拆出子模块（不改变对外行为）；必要的说明记录在项目仓库内（如 `docs/` 或源码 docstring），不使用 `AI_WorkSpace`。
  - 消除 `foundational_service → business_logic`/`business_service` 的上行 import；改为向下可注入抽象或通过中立契约交互。
  - 去除 `business_service → interface_entry` 的适配器引用；协议转换在入口层完成。
- P1（两周内建议处理）：
  - 拆分 Up 大组件为窄职责子组件，服务调用下沉至 services，父组件仅编排。
- P2（一个月内建议处理）：
  - 增补 Up 文档契约（WorkflowBuilder/PromptEditor），形成可追溯的父子组件清单与事件约定。

## Acceptance (for this Audit Round)
- 验收以“事实对齐”与“差距收敛”为准：
  - [A1] 依赖图中不再存在 `business_service → business_logic` 上行 import；
  - [A2] 依赖图中不再存在 `foundational_service → business_logic`/`business_service` 上行 import；
  - [A3] `conversation/service.py` 行数显著下降，父文件仅保留编排逻辑；
  - [A4] Up 组件单个文件行数下降且功能聚焦，存在明确的子组件与 props/emit 契约。

## Notes
- 本文件为 Assessment Focus，旨在“列出问题 + 证据 + 影响 + 优先级”。若需进入 Strategy Focus（方案与改造细化），请在聊天中明确指示，再进行后续写作。
