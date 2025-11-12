# 回归护栏测试计划 · Session 00001 · compliance-audit

生成时间：2025-11-12
范围：仅为“结构合规审计”的回归护栏（Assessment Focus）。不做端到端全链路，不验证业务功能正确性；只确保重构不引入新的结构性违例、关键文件不增胖、关键对外契约（选取少量）不退化。

来源文档：
- Requirements：`AI_WorkSpace/Requirements/session_00001_compliance-audit.md`
- Notes：`AI_WorkSpace/notes/session_00001_compliance-audit.md`

引用（Context7/Exa）：
- Pytest 官方：fixture/markers/CI 组织最佳实践（/pytest-dev/pytest）。
- Characterization Tests（回归表征测试理念）：Michael Feathers, Erik Dietrich（exa: silvrback/daedtech）。

## 一、环境矩阵（最小集）
- 本地开发（Windows/WSL 任一）：
  - Python ≥3.11，ripgrep（rg）可用；Node 环境只在前端样例中使用。
  - 不要求 Redis/Mongo/Telegram/Chrome DevTools，本轮仅跑静态扫描+契约金样本比对。

## 二、数据与夹具
- 无持久化数据；所有脚本针对工作副本代码树运行。
- 金样本（可选）：保存 1–2 个 FastAPI 接口响应与 1 条结构化日志的“字段子集”JSON 作为对比基线。

## 三、测试套件设计（回归护栏）

### RG-DEP-001 层级依赖护栏（P0 自动化）
- 目的：禁止新增“上行 import”。允许现存违例（allowlist），但新新增立即失败。
- 范围：
  - Rise 后端：`src/**`，排除 `AI_WorkSpace/**`；
  - 检查模式：
    1) business_service → business_logic（违例）
    2) foundational_service → business_logic/business_service（违例）
    3) business_service → interface_entry（违例）
- 命令（建议由脚本封装）：
  - `rg -n --glob '!AI_WorkSpace/**' "\b(from|import)\s+business_logic\b" src`
  - `rg -n --glob '!AI_WorkSpace/**' "\b(from|import)\s+business_service\b" src | rg -v "^src/business_service"`
 - `rg -n --glob '!AI_WorkSpace/**' "\b(from|import)\s+interface_entry\b" src/business_service`
 - 断言：输出中不得出现“非 allowlist”行；出现则失败，打印文件:行号:语句。

### RG-SIZE-001 关键文件体量护栏（P0 自动化）
- 目的：关键胖文件行数不得增长（允许 2% 浮动）。
- 基线：
  - `src/business_service/conversation/service.py` = 1286 行
  - `Up/src/views/PipelineWorkspace.vue` = 832 行
- 命令（建议脚本）：统计行数与基线对比；超出（基线×1.02）失败。

### RG-ONEOFF-001 one_off 隔离护栏（P0 自动化）
- 目的：核心路径不得 import `src/one_off/**`。
- 命令：`rg -n --glob '!src/one_off/**' "from\s+one_off|import\s+one_off" src`；无输出为通过。

### RG-CYCLE-001 进口环路护栏（P0 自动化）
- 目的：阻断新增的 Python/TS 导入环路（允许历史环路以 allowlist 兜底）。
- 后端：对 `Rise/src` 扫描 `import/from` 关系构图（仅内部包），检测环路；命中且不在 allowlist 则失败。
- 前端：对 `Up/src` 扫描 `import ... from '...';` 的相对/别名导入，检测环路；命中且不在 allowlist 则失败。

### RG-PATH-001 路径-分层落位护栏（P0 自动化）
- 目的：禁止“层级与落位不一致”的新增文件（例如把业务逻辑放入 foundational_service）。
- 规则：
  - `src/business_logic/**` 不得被下层 import；
  - `src/foundational_service/**` 不得 import 上层；
  - 新文件若不匹配所在层的命名/落位（通过正则/映射规则判定），直接失败；存量以 allowlist 保留。

### UP-CYCLE-001 前端循环依赖护栏（P0 自动化）
- 目的：阻断新增 `.vue/.js` 间的循环依赖（相对路径与 `@/` 别名）。
- 方法：解析 import 图（仅 Up/src），DFS 检测环路，报告路径链；非 allowlist 即失败。

### UP-SIZE-ALL-001 全局组件体量护栏（P1 可开关）
- 目的：除了“关键文件体量”，为所有 `.vue` 组件设上限以防整体回归。
- 规则：默认 500 行/文件（或“基线+2%”两者取大值）；超出失败。

### RG-API-001 关键接口 JSON 形态护栏（P1 可选）
- 目的：保证接口响应字段集不倒退（仅字段存在与类型，不校验语义）。
- 步骤：
  1) 运行被测接口（如 `/healthz` 或简易业务读接口）获取响应保存为 `golden/api_healthz.json`；
  2) 重构后再次获取响应，与金样本比对字段存在与类型（可用 Python jsonschema/pydantic 校验）。

### RG-LOG-001 结构化日志字段护栏（P1 可选）
- 目的：关键日志字段（如 requestId、layer、module、event）仍存在。
- 方法：采集一条日志行，做字段子集断言（忽略时间戳与随机数）。

## 四、执行计划
- 触发：每次 PR + 夜间定时。
- 责任：平台/后端维护 RG-DEP/RG-SIZE/RG-ONEOFF；前端在涉及大组件改动的 PR 运行体量护栏。
- 失败处理：打印命中行与基线；PR 阻断并附“如何采证”提示，不给出修复方案（由 01/04 流转）。

## 五、报告模板
| 时间 | 提交SHA | 用例ID | 命令 | 结果 | 证据路径 | 备注 |
|------|--------|-------|------|------|---------|------|

## 六、覆盖检查
- 对应 Requirements 的 P0/P1 项逐一映射：
  - P0：RG-DEP-001、RG-CYCLE-001、RG-PATH-001、RG-ONEOFF-001、RG-SIZE-001
  - P1：UP-SIZE-ALL-001、RG-API-001、RG-LOG-001（可选）
- 覆盖声明：本计划只提供“结构护栏”，不覆盖功能正确性与端到端渠道。

## 七、参考
- Pytest fixtures/markers/parametrize（/pytest-dev/pytest）。
- Characterization Testing 概念（Michael Feathers；DaedTech 综述）。

## 附：脚本骨架（仅示意，建议放置 `AI_WorkSpace\Scripts\session_00001_compliance-audit\`）

### check_import_layers.py（P0）
```
# 伪代码：解析 Rise/src 下所有 .py 的 import/from 行，
# 根据层级映射判定是否出现上行依赖；支持 --allowlist 文件。
LAYER_ORDER = [
  ("business_logic", 3),
  ("business_service", 2),
  ("foundational_service", 1),
  ("project_utility", 0),
]
# 解析 -> 得到 (src_file, imported_layer, src_layer)
# 若 imported_layer.level > src_layer.level 且不在 allowlist: fail
```

### check_cycles.py（P0）
```
# 伪代码：
# 后端：解析 import 图（仅内部包），DFS 检测环路。
# 前端：解析 Up/src 中 import 路径（相对与 '@/...'），标准化后建图，DFS 检测环路。
```

### check_file_sizes.py（P0/P1）
```
# 伪代码：读取基线 json {path: lines}；现状统计行数；
# 若 lines_now > lines_baseline * 1.02: fail
```
