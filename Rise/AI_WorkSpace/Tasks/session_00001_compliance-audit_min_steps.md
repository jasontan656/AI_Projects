# Session 00001 · compliance-audit · 最小执行计划

## 1. Inputs
- AI_WorkSpace\Requirements\session_00001_compliance-audit.md · 2025-11-13 04:59:34
- AI_WorkSpace\notes\session_00001_compliance-audit.md · 2025-11-13 05:32:51
- AI_WorkSpace\Test\session_00001_compliance-audit_testplan.md · 2025-11-13 05:19:06
- AI_WorkSpace\DevDoc\On\session_00001_compliance-audit_tech.md · 2025-11-13 05:24:26
- AI_WorkSpace\index.yaml · 2025-11-13 02:16:44
- AI_WorkSpace\PROJECT_STRUCTURE.md · 2025-11-13 01:26:28

## 2. 能力总览
- Rise API/后端：FastAPI + aiogram，具备多层目录但存在跨层依赖与胖文件，需要依赖守护与模块拆分以满足 Requirements P0/A1-A3。
- Up Admin UI：Vue3 + Vite，当前组件层次不均衡（PromptEditor/NodeDraftForm/WorkflowChannelForm 为超大组件），缺少父子 props/emit 契约文档，需要组件拆分与文档补全（Requirements Findings#5-6, Acceptance A4）。
- Telegram Bot & Channel Bindings：由 aiogram/Redis/Mongo 提供状态，当前无需改动但需确保 refactor 不破坏 webhook 契约；验证方式依赖结构护栏脚本而非实时联调。
- 基础设施（Redis/Mongo/OpenAI）：保持现状，仅需在测试时 stub/禁用外部连接，重点是结构性验证脚本。
- 自动化脚本：`AI_WorkSpace/Scripts/session_00001_compliance-audit/` 将承载 import/size/cycle/golden-sample 脚本，需在步骤内逐个落地并在 CI 中可复用。

## 3. 差距分析
1. G1：缺少“上行依赖”门禁，导致 business_service/foundational_service 直接 import business_logic / interface_entry（Requirements Findings#1-3，Test Plan RG-DEP-001）。
2. G2：`src/foundational_service` 仍持有业务类型，未按 Tech Doc §3.1 建立 contracts 层（Acceptance A2）。
3. G3：`src/business_service/conversation/service.py` 仍为 1286 行胖文件，违背 Tech Doc §3.1 拆分方案（Acceptance A3）。
4. G4：`business_service` 仍 import `interface_entry` 适配器，违背分层守则（Requirements Findings#3，Tech Doc §3.1）。
5. G5：Up 侧超大组件未拆分且缺少 props/emit 契约说明（Requirements Findings#5-6，Acceptance A4）。
6. G6：结构护栏仅在文档层，缺乏可执行脚本去检测文件体量/循环依赖/one_off 隔离（Test Plan RG-SIZE-001、RG-CYCLE-001、RG-ONEOFF-001、UP-CYCLE-001）。
7. G7：缺乏 API/日志金样本，无法支撑 RG-API-001/RG-LOG-001（Test Plan §3）。

## 4. 步骤计划
### Step-01 建立上行依赖守护脚本（RG-DEP-001/RG-PATH-001 基线）
- 目标：在 `AI_WorkSpace/Scripts/session_00001_compliance-audit/Step-01_import_guard.py` 中解析 `src/**` import 图，落地 allowlist+CI 退出码，引用 Context7:/fastapi-practices/fastapi_best_architecture 的分层范式与 PROJECT_STRUCTURE.md 约束。
- 开发：扫描 `src`，构建层级映射（project_utility=0, foundational=1, business_service=2, business_logic=3, interface_entry=4），识别 “向上” import；输出 JSON 报表供后续步骤复用。
- 测试：运行 `python AI_WorkSpace\Scripts\session_00001_compliance-audit\Step-01_import_guard.py --ci` 并确认仅列出已知违例；在 `git diff --stat` 为空时退出码=0，有新增违例时=1。
- 依赖：无（首步）。
- 估算：0.5 人日。

### Step-02 建立 foundational contracts 并替换 worker/import（A2）
- 目标：按 Tech Doc §3.1 创建 `src/foundational_service/contracts/{workflow_exec.py,knowledge_io.py}`，重写 `persist/worker.py`、`integrations/memory_loader.py`、`messaging/channel_binding_event_publisher.py` 以依赖新 contracts。
- 开发：
  1. 新建协议类/TypedDict，禁止引用 business_logic/business_service。
  2. 更新调用点，通过依赖注入（组合根 `interface_entry/bootstrap/application_builder.py`）传入实现。
  3. 更新 DevDoc 标注注入点。
- 测试：
  - `pytest tests/foundational_service -k workflow_exec`（若无则新建 characterization test）。
  - 运行 Step-01 脚本确认无新增 F→BS/BL import。
- 依赖：Step-01 报表作为验收基线。
- 估算：1.0 人日。

### Step-03 拆分 conversation/service.py（A1/A3）
- 目标：依 Tech Doc §3.1 把 `service.py` 瘦身为编排壳，新建 `channel_health.py`、`runtime_dispatch.py`、`contracts_adapter.py`，并在 `service.py` 中只组合导入；记录行数下降。
- 开发：
  1. 移动频道健康、Runtime 队列、契约转换逻辑到对应文件。
  2. `service.py` 仅保留 orchestrator、依赖注入与错误处理。
  3. 更新 `__all__` 与 typing 引用。
- 测试：
  - `pytest tests/business_service -k conversation`。
  - `python - <<'PY' ...` 使用 `inspect.getsource` 统计 `service.py` 行数 ≤ 原基线 *0.6。
  - Step-01 脚本确认无 business_logic import。
- 依赖：Step-02（contracts 输出）确保上下游 DTO 稳定。
- 估算：1.5 人日。

### Step-04 去除 business_service→interface_entry 依赖（A1）
- 目标：新增 `business_service/conversation/adapters_core.py` 并更新 `primitives.py`、interface_entry 适配器，使入口层完成协议转换。
- 开发：
  1. 定义中立 DTO/转换函数。
  2. `interface_entry/telegram/adapters.py` 改为依赖 adapters_core。
  3. 更新 aiogram handler/Bootstrap wiring。
- 测试：
  - `pytest tests/interface_entry -k telegram`。
  - Step-01 脚本确认 `business_service` 不再 import `interface_entry`。
- 依赖：Step-02/03 完成后执行，确保 contracts/模块已落地。
- 估算：0.75 人日。

### Step-05 拆分 PromptEditor 组件（A4）
- 目标：依 Tech Doc §3.2 在 `Up/src/components/prompt-editor/` 建立 `PromptMetaForm.vue`、`PromptContentEditor.vue`、`PromptPreviewPanel.vue`，父组件仅编排。
- 开发：
  1. 建目录与 barrel 导出，迁移模板/脚本/样式。
  2. 把服务调用迁移到 `src/services/promptService.ts`（若需要新建）。
  3. 更新 `PipelineWorkspace.vue` 与其他引用路径。
- 测试：
  - `cd D:\AI_Projects\Up; npm run lint && npm run test:unit PromptEditor`。
  - `npx madge --circular src/components/prompt-editor --ts-config tsconfig.json`（参考 Exa:devto-madge 循环检测实践）。
- 依赖：Step-08/09 的脚本可复用，但可先行使用本地 madge。
- 估算：1.0 人日。

### Step-06 拆分 NodeDraftForm & WorkflowChannelForm（A4）
- 目标：延续 Step-05 模式完成 `node-draft/*`、`channel-form/*` 子组件与 services 分层，并更新 store/路由。
- 开发：
  1. 拆分字段/动作/壳结构，复用 mixins/composables（若无则新增）。
  2. 更新 `WorkflowBuilder.vue`、`PipelineWorkspace.vue` 引用。
- 测试：
  - `npm run test:unit NodeDraftForm WorkflowChannelForm`。
  - `npx madge --circular src/components/node-draft src/components/channel-form --ts-config tsconfig.json`。
- 依赖：Step-05 确立的目录/模式。
- 估算：1.5 人日。

### Step-07 Up 文档契约补全（Findings#6）
- 目标：在 `Up/docs/ProjectDev/` 新增/更新 WorkflowBuilder & PromptEditor 契约文档，描述父子组件清单、props、emit、事件流。
- 开发：撰写 Markdown，列出组件树与字段表；引用 Step-05/06 输出。
- 测试：人工校对+同伴审阅（对照 Requirements Acceptance A4）；在 PR 模板添加“文档已同步”复选框。
- 依赖：Step-05/06 完成后执行。
- 估算：0.5 人日。

### Step-08 文件体量守护脚本（RG-SIZE-001/UP-SIZE-ALL-001）
- 目标：在 `AI_WorkSpace/Scripts/session_00001_compliance-audit/Step-08_file_size_guard.py` 内维护 JSON 基线并比较当前行数（阈值=基线×1.02），覆盖后端/前端关键文件。
- 开发：从 `rg --files` + `Measure-Object` 收集行数，写入 `size_baseline.json`；脚本接受 `--update-baseline` 参数。
- 测试：
  - `python ... Step-08_file_size_guard.py --ci`。
  - 故意增行（本地）验证脚本失败再回滚。
- 依赖：Step-01（共享报表格式）。
- 估算：0.5 人日。

### Step-09 循环依赖守护脚本（RG-CYCLE-001/UP-CYCLE-001/one_off 隔离）
- 目标：在 `Step-09_cycle_guard.py` 中集成 import-linter（后端）+ madge（前端）调用，读取 allowlist，检测循环 & one_off 引用。
- 开发：
  1. `pip install import-linter`, `npm install madge --save-dev`（在 Up）。
  2. 脚本顺序调用 `poetry run lint-imports` / `npx madge --circular src --extensions ts,tsx,vue` 并解析输出。
  3. one_off 检查：`rg -n "from\s+one_off" src`。
- 测试：`python ... Step-09_cycle_guard.py --ci` 应在违例时退出 1。
- 依赖：Step-01/08 报表，用于共享 allowlist 格式；Step-05/06 之后再更新前端图。
- 估算：0.75 人日。

### Step-10 API/日志金样本采集（RG-API-001/RG-LOG-001）
- 目标：在 `Step-10_capture_golden.py` 中调用最小 FastAPI/日志路径，保存字段子集金样本供 diff。
- 开发：
  1. 启动 `uvicorn app:app --env-file .env.dev --reload`（或复用现有脚本）。
  2. 请求 `/healthz` 与一个典型 workflow 读接口，截取字段子集写入 `golden/api_healthz.json`。
  3. Tail 结构化日志写入 `golden/log_sample.jsonl`。
- 测试：
  - 再次运行脚本：若字段缺失或类型变化即失败。
  - `pytest tests/interface_entry -k golden`（若需要加特定断言）。
- 依赖：Step-02~04 需完成以稳定 API 结构；Step-08 baseline 供日志字段检查。
- 估算：0.75 人日。

### Step-11 全量护栏 + 验收回归
- 目标：串联 Step-01/08/09/10 脚本，并运行前后端测试形成交付证据，映射 Acceptance A1-A4。
- 开发：在 `AI_WorkSpace/Scripts/session_00001_compliance-audit/Step-11_run_compliance_suite.ps1`（或 Makefile 目标）中依次调用：
  1. `python Step-01_import_guard.py --ci`
  2. `python Step-08_file_size_guard.py --ci`
  3. `python Step-09_cycle_guard.py --ci`
  4. `python Step-10_capture_golden.py --verify`
  5. `pytest tests -m "not e2e"`
  6. `cd ..\Up; npm run test:unit && npm run build`
- 测试：上述脚本本身即测试；另需审阅 `reports/compliance_suite_<timestamp>.json`（由脚本生成）。
- 依赖：所有前置步骤完成。
- 估算：0.5 人日。

## 5. 覆盖矩阵
| Requirement/Test ID | 覆盖 Step |
|--------------------|-----------|
| A1（移除 BS→BL/IE 依赖） | Step-01, Step-03, Step-04, Step-11 |
| A2（Foundational 不上行） | Step-01, Step-02, Step-11 |
| A3（瘦身 service.py） | Step-03, Step-08, Step-11 |
| A4（Up 组件聚焦+文档） | Step-05, Step-06, Step-07, Step-08, Step-09 |
| RG-DEP-001 | Step-01, Step-02, Step-03, Step-04, Step-11 |
| RG-SIZE-001 | Step-08, Step-11 |
| RG-ONEOFF-001 | Step-09, Step-11 |
| RG-CYCLE-001 / UP-CYCLE-001 | Step-09, Step-11 |
| UP-SIZE-ALL-001 | Step-05, Step-06, Step-08 |
| RG-API-001 / RG-LOG-001 | Step-10, Step-11 |

若未来新增场景未被映射，请在 Step 计划区补充“未覆盖”条目。

## 6. 工具与命令摘要
- Python 结构守护：`python AI_WorkSpace\Scripts\session_00001_compliance-audit\Step-0X_*.py`（统一 `--ci`/`--update-baseline` 参数）。
- pytest：`pytest tests/foundational_service -k workflow_exec`、`pytest tests/business_service -k conversation`、`pytest tests/interface_entry -k telegram`、全量 `pytest tests -m "not e2e"`。
- 前端：`npm run lint`、`npm run test:unit <Component>`、`npm run build`（在 `D:\AI_Projects\Up`）。
- Madge：`npx madge --circular src/... --ts-config tsconfig.json --extensions ts,tsx,vue`（参考 Exa:devto-madge）。
- Import-linter：配置 `.importlinter` 后运行 `import-linter --config .importlinter` 或由 Step-09 脚本触发。
- 其他：`rg -n`, `Measure-Object -Line`, `uvicorn app:app --env-file .env.dev` 用于金样本。

## 7. 脚本工件
| 文件 | 作用 |
|------|------|
| Step-01_import_guard.py | 检测上行依赖/层级落位，输出 JSON 报表供 CI。|
| Step-08_file_size_guard.py | 维持关键文件行数基线并做 2% 容差比较。|
| Step-09_cycle_guard.py | 聚合 import-linter、madge、one_off 扫描。|
| Step-10_capture_golden.py | 拉取 API/日志字段金样本并做对比。|
| Step-11_run_compliance_suite.ps1 | 串联脚本与测试命令，生成汇总报告。|

其余步骤如需脚本（例如自动统计 service.py 行数），应在实现时按 Step ID 命名追加到同目录。

## 8. 风险与缓解
- 旧违例过多导致守护脚本频繁失败：通过 allowlist + sunset 日期并在 Notes 中登记，逐步清零。
- 模块拆分可能影响 Telegram Webhook 行为：在 Step-04 后运行 characterization 测试与金样本比较，确保 DTO 未变。
- 前端组件拆分引入状态同步 bug：在 Step-05/06 中通过 Pinia store 单元测试 + Storybook/手动验证 props/emit，必要时增加 vitest 快照。
- 脚本与 CI 依赖第三方工具（madge/import-linter）版本波动：锁定版本写入 `requirements.lock`、`package.json` 并在 runbook 记录安装步骤。
- 金样本漂移：在 Step-10 中要求显式 `--update-golden` 参数并记审查人，避免随意覆盖。
