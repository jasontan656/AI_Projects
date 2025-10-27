---
```python
doc:
  id: 01DatabaseIndexAgentPlan
  title: Index Agent 方案与 Knowledge Base 设计工作笔记
  language: zh-CN
  created: 2025-10-25
  updated: 2025-10-27
  owner: owner
  editors:
    - AI Assistant
  status: draft
  schema_version: 1.1.0
  kind: universal-ssot-plan
  family: kobe
  repository_root: AUTO
  focus_note_path: D:\\\\AI_Projects\\\\Kobe\\\\WorkPlan\\\\01DatabaseIndexAgentPlan.md
  knowledge_base_root: AUTO
  all_paths_relative_to: REPO_ROOT
  purpose: >
    作为面向 AI 与开发者的“几乎可执行”设计文档：
    文档优先给出 Telegram ↔ Agents 接入所需的 schema、行为定义、JSON Schema、样例与 SLO；
    所有渠道与服务均须将本文视作单一事实来源（SSOT）。
writing_rules:
  content_ratio: "100% behavior 描述 + 接口字段/Schema 说明，禁止可执行代码"
  universality_policy:
    non_customizable_by_content: true         # 文件头为全局模板，正文不得降低约束
    must_autofill_missing_sections: true      # 未定义项由 AI 按发现顺序自动补齐
    must_align_with_repo_before_write: true   # 生成正文前 MUST 读取并对齐代码库
    autofill_precedence: ["code/constants", "config/*.yaml", "env/.env", "index/knowledge_base", "defaults"]
    conflict_resolution: "header>MUST>repo_contract>content"
    cross_doc_coherence:
      family_docs: ["01DatabaseIndexAgentPlan", "02TelegramBotGCmessagePlan", "03KBtoolUnify"]
      ownership:
        plan_01: "Index/KB schema & routing"
        plan_02: "Channel adapter, interaction prompts/behavior, runtime policies"
        plan_03: "KB 工具与统一化治理"
      precedence:
        index_level: "plan_01 overrides"
        channel_level: "plan_02 overrides"
        tooling_level: "plan_03 extends without override"
  codegen:
    targets:
      - kind: "config"              # 从 Prompt JSON Schema 生成配置
        from: "Prompt JSON Schema"
        to: "{REPO_ROOT}/Config/prompts.{locale}.yaml"
        naming: "snake_case"
      - kind: "python"              # 从 Behavior Contract 生成契约骨架
        from: "Behavior Contract"
        to: "{REPO_ROOT}/Contracts/behavior_contract.py"
        anchors: ["class BehaviorContract", "def apply_contract()"]
      - kind: "python"              # 从 ToolCall Contract 生成工具封装骨架
        from: "ToolCall / FunctionCall Contract"
        to: "{REPO_ROOT}/Contracts/toolcalls.py"
        anchors: ["def call_{tool}()"]
      - kind: "schema"              # 输出契约落盘，供运行期校验
        from: "Output Contract"
        to: "{REPO_ROOT}/Contracts/output.schema.json"
    rules:
      - MUST regenerate all targets when any of [Prompt Catalog, Output Contract, Behavior Contract] changes
      - MUST fail if target file missing or schema‑breaking change detected
      - MUST annotate generated files with "generated-from: {doc.id}@{doc_commit}"
    placeholders:
      allowed: ["{REPO_ROOT}", "{FAMILY}", "{COMPONENT}", "{DOC_ID}", "{DOC_COMMIT}", "{LOCALE}", "{VERSION}"]
      semantics:
        REPO_ROOT: "仓库根目录（自动解析）"
        FAMILY: "产品族/域（例如 kobe）"
        COMPONENT: "子组件名（例如 TelegramBot, OpenaiAgents, KnowledgeBase）"
        DOC_ID: "当前文档 id"
        DOC_COMMIT: "提交哈希缩写"
        LOCALE: "语言区域标识（zh-CN/en-US/...）"
        VERSION: "文档/契约版本，如 prompt_version"
    path_policy:
      - MUST use only placeholders listed in codegen.placeholders.allowed
      - MUST be absolute after placeholder expansion
      - MUST NOT contain user home 或 临时目录占位（如 ~、%TEMP%）
      - SHOULD keep depth <= 4 级目录，便于审计
  structure_order:
    - 标题
    - 设计意图
    - 设计原因
    - 接口锚点
    - 需求字段
    - 二级嵌套
    - 三级嵌套
    - JSON Schema (MUST)
    - Prompt Catalog (MUST)
    - Prompt JSON Schema (MUST)
    - Behavior Contract (MUST)
    - ToolCall / FunctionCall Contract (MUST)
    - Config Contract (MUST)
    - Safety & Refusal Policy (MUST)
    - i18n & Brand Voice (MUST)
    - Output Contract (MUST)
    - Logging & Observability (MUST)
    - Versioning & Traceability (MUST)
    - Golden Sample(s) (MUST >=3)
    - Counter Sample(s) (MUST >=2)
    - 决策表 / 状态机 / 顺序化约束
    - 如何使用
    - agent如何读取
    - 边界与回退
    - SLO / 阈值 / 触发条件
  body_style:
    description: >
      正文仅允许 Python 代码块承载行为描述、字段清单、接口锚点、JSON Schema、示例与决策表；
      允许 import/from/def/class 作为标识符；必须使用 RFC 2119 术语（MUST/SHALL/SHOULD/MAY）表达约束；
      优先使用中文叙述解释业务语义，字段/关键字保持 ASCII；禁止任何可执行代码或赋值；所有逻辑采用 docstring/步骤/表格形式，确保实现可复制。
    python_fenced_block: true
    ascii_punctuation_only: true
    allow_structs: ["dict", "list", "string"]
    allow_keywords: ["if", "else", "try", "except", "return", "True", "False", "None"]
    allow_declarations: ["import", "from", "def", "class"]
    forbid_keywords: ["with", "lambda", "yield", "await", "async", "for", "while"]
    declarations_only: true
    forbid_runtime_ops: ["assignment", "function_call", "comprehension"]
    only_hash_for_titles: true
    inline_cn_after_import_def: true
    pseudo_assignment_labels: ["需求字段", "设计意图", "设计原因", "二级嵌套", "三级嵌套", "如何使用", "agent如何读取", "边界与回退", "模板与占位"]
    def_line_format: "def Name(): ...  中文说明"
    class_line_format: "class Name: ...  中文说明"
  prompt_style:
    human_readable_first: true
    description: >
      每条 Prompt Catalog 需先以中文段落说明“用途、触发条件、变量说明、示例文案”，
      再给出结构化 Prompt 条目与 JSON Schema 以便自动化；若包含多语言提示，说明段落默认中文，必要时附英文原文。
    required_sections: ["用途", "触发条件", "变量说明", "示例文案"]
  policy:
      determinism:
        temperature: 0      # MUST 在正文显式给值
        seed: REQUIRED      # MUST 指定以保证可重现
        top_p: 1            # 建议值，若不同需在正文说明
      token_budget:
        per_call_max_tokens: REQUIRED
        per_flow_max_tokens: REQUIRED
        summarize_threshold_tokens: REQUIRED
      output_mode: "strict-json | markdown-structured"   # MUST 二选一并给出输出契约
      naming:
        prompt_version: REQUIRED
        doc_commit: REQUIRED
      nondeterminism:
        allow_without_seed: false
        provider_fallback_order: ["OpenAI.Responses", "OpenAI.ChatCompletions", "Anthropic.Messages", "Custom"]
        drift_tolerance_tokens: 1
        assert_output_contract: true
      provider_capabilities:
        OpenAI.Responses:
          supports_seed: true
          supports_json_mode: true
          supports_function_call: true
          max_input_tokens: 200000
          notes: "优先使用；strict JSON 建议配合 schema 约束"
        OpenAI.ChatCompletions:
          supports_seed: true
          supports_json_mode: true
          supports_function_call: true
          max_input_tokens: 128000
        Anthropic.Messages:
          supports_seed: false
          supports_json_mode: partial
          supports_function_call: tool_use
          max_input_tokens: 200000
          notes: "seed 不稳定时需放宽 drift 容忍或改用结构化提示"
        Custom:
          supports_seed: unknown
          supports_json_mode: unknown
          supports_function_call: unknown
          max_input_tokens: unknown
      refusal_strategy:
        priority: ["safety", "contract", "budget", "rate_limit", "other"]
        rules:
          safety:
            on: ["safety_triggered", "policy_violation", "pii_detected"]
            action: "refuse"
            audit_log: true
          contract:
            on: ["output_validation_failed", "schema_mismatch", "drift_exceeded"]
            action: "repair_then_refuse_if_unfixable"
            max_repairs: 1
          budget:
            on: ["token_budget_exceeded", "summary_required"]
            action: "degrade_or_summarize"
          rate_limit:
            on: ["rate_limited"]
            action: "retry_with_backoff"
            backoff_ms: [200, 400, 800]
  code_guidelines:
    language: python
    libraries:
      - openai-agents
      - pydantic>=2
  acceptance_criteria:
    - 正文整体包裹在一个 python 代码块中
    - MUST 保证 doc.id 等于当前文件名（去扩展名），focus_note_path 为当前文件绝对路径，repository_root/knowledge_base_root 使用 AUTO 并由工具在生成时解析
    - 每节必须包含 JSON Schema、>=3 正向样例、>=2 反例、至少一张决策表或状态机描述
    - MUST 提供完整 Prompt 清单（system/triage/summarize/compose/clarify/toolcall/refusal/welcome/help/rate_limit/degrade）
    - 每个 Prompt Catalog 条目必须先提供中文“用途/触发条件/变量说明/示例文案”描述块，再给结构化条目，保证人类与机检并行
    - MUST 提供 Prompt 变量表（name/type/required/default/example/description），并与 JSON Schema 对齐
    - MUST 提供 Output Contract（JSON Schema 或 Markdown 结构）以及端到端样例（输入->期望输出）>=3；对抗样例（提示注入/越权/敏感）>=2 并给出期望拒答
    - MUST 指定解码参数（temperature/top_p/seed）与 token 预算（per_call/per_flow/summary_threshold）
    - MUST 明确日志/可观测性字段（request_id/chat_id/convo_id/prompt_version/doc_commit/latency_ms/status_code/error_hint）
    - 字段、路径、模块名必须与仓库真实结构匹配，并在 CI 可机检（schema 校验、锚点存在性）
    - MUST 明确 SLO/阈值/触发条件并使用 RFC 2119 术语
    - MUST 在生成/渲染前执行仓库发现：扫描 anchors （常量/配置/索引）并将解析结果写入正文“Auto‑Discovery”小节；缺失即失败
    - MUST 在变更 Prompt/Behavior/SLO 时 bump prompt_version，并同步更新 Golden/对抗样例
    - MUST 在 changelog 的每条记录中标注 change_type: breaking|nonbreaking；breaking 需附 migration_guide 与 rollback_notes
    - MUST 提供 pii_redaction 规则（字段与掩码）并在运行期启用
    - MUST 记录 prompt_fingerprint(sha256) 与 output_schema_id；运行期开启严格输出校验（不符即拒答/降级）
    - MUST 所有 codegen.targets[*].to 仅使用 codegen.placeholders.allowed 中占位符；展开后路径为绝对路径
    - MUST 所选 provider 属于 policy.provider_capabilities 的键，且调用满足其能力约束；若不满足必须按 provider_fallback_order 切换
    - MUST 运行期对输出执行严格契约校验，不符合则按照 policy.refusal_strategy 执行 refuse/degrade/repair
ci:
  guards:
    - name: schema_validation
      tools: ["ajv", "pydantic"]
    - name: anchors_existence
      tools: ["scripts/check_anchors.py"]
    - name: samples_parse
      tools: ["scripts/validate_samples.py"]
    - name: adversarial_refusal
      tools: ["scripts/validate_safety.py"]
    - name: runtime_output_validation
      tools: ["scripts/validate_runtime_output.py"]
    - name: pii_redaction
      tools: ["scripts/check_pii_redaction.py"]
  required_status: pass
changelog:
  - date: 2025-10-26
    author: AI Assistant
    change: 采用行为描述写作规范，重写 Telegram/Agents 接入方案
---pythonpython
# 标题: 全局运行参数与决定性配置
设计意图: "集中声明可重现所需的解码/预算/版本/脱敏/指纹等参数，作为全局约束。"
设计原因: "保证不同章节在同一组决定性参数下可复现、可校验。"
接口锚点:
class GlobalRuntimePolicy: ...  "Contracts/behavior_contract.py 读取并注入"
需求字段 = {
"determinism": {"temperature": 0, "top_p": 1, "seed": 20251027},
"token_budget": {"per_call_max_tokens": 3000, "per_flow_max_tokens": 6000, "summary_threshold_tokens": 2200},
"output_mode": "markdown-structured",
"versioning": {"prompt_version": "idx-v1", "doc_commit": "local-dev"},
"pii_redaction": [
  {"field": "email", "mask": "***@***"},
  {"field": "phone", "mask": "***-****"},
  {"field": "id_number", "policy": "hash(sha256)"}
],
"fingerprints": {"prompt_fingerprint": "0000000000000000000000000000000000000000000000000000000000000000", "output_schema_id": "kobe/index/outputs@v1"}
}
JSON Schema (MUST):
  {
    "$id": "kobe/global/runtime.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["determinism", "token_budget", "output_mode", "versioning", "pii_redaction", "fingerprints"],
    "properties": {
      "determinism": {"type": "object", "properties": {"temperature": {"type": "number"}, "top_p": {"type": "number"}, "seed": {"type": "integer"}}, "required": ["temperature", "top_p", "seed"]},
      "token_budget": {"type": "object", "properties": {"per_call_max_tokens": {"type": "integer"}, "per_flow_max_tokens": {"type": "integer"}, "summary_threshold_tokens": {"type": "integer"}}, "required": ["per_call_max_tokens", "per_flow_max_tokens", "summary_threshold_tokens"]},
      "output_mode": {"type": "string", "enum": ["strict-json", "markdown-structured"]},
      "versioning": {"type": "object", "properties": {"prompt_version": {"type": "string"}, "doc_commit": {"type": "string"}}, "required": ["prompt_version", "doc_commit"]},
      "pii_redaction": {"type": "array", "items": {"type": "object"}},
      "fingerprints": {"type": "object", "properties": {"prompt_fingerprint": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "output_schema_id": {"type": "string"}}, "required": ["prompt_fingerprint", "output_schema_id"]}
    }
  }
如何使用: "Contracts/behavior_contract.py 在应用启动时读取并注入；各章节不得私自覆盖。"
agent如何读取: "AgentsBridge 从全局 policy 读取种子/预算/输出模式，确保流式行为一致。"
边界与回退: "任一字段缺失 MUST 阻止部署；seed 变更 MUST bump prompt_version。"
SLO / 阈值 / 触发条件: "读取与验证 SHOULD < 10ms；PII redaction 命中率 100%。"# 标题: Agent 基座背景与阅读说明
设计意图:
  - MUST 将 01 文档限定为 Index schema、内存知识库与 Agent 行为的 SSOT，禁止混入第三方项目改造说明。
  - MUST 在写入正文前完成仓库自动勘察（目录/配置/知识库文件），并记录发现结果供 codegen、CI 重放。
  - SHOULD 向 02 文档暴露本篇提供的字段/契约清单，确保 channel 层直接引用，无需重复解释。
设计原因:
  - 仓库当前仅存在 `.venv`, `KnowledgeBase/`, `OpenaiAgents/`, `SharedUtility/`, `TelegramBot/`, `Tests/`, `WorkPlan/`；缺少 core/ 与 app.py，需要文档明确待建结构。
  - 旧文本仍讨论 ApplicationBuilder/minimal injection，与现行 aiogram/FastAPI 策略冲突，必须剔除。
接口锚点:
  - from OpenaiAgents import __all__  "{REPO_ROOT}/OpenaiAgents/ 存在但无 UnifiedCS，本文定义的 schema 需落盘于此"
  - from KnowledgeBase import KnowledgeBase_index  "{REPO_ROOT}/KnowledgeBase/ 现存，需按照本计划补充 index.yaml"
  - from WorkPlan import plan_family  "{REPO_ROOT}/WorkPlan/ 包含 02 文档，需 cross-reference plan_02"
需求字段:
  - auto_discovery:
      repo_root: "D:/AI_Projects/Kobe"
      existing_dirs: ["KnowledgeBase", "OpenaiAgents", "SharedUtility", "TelegramBot", "Tests", "WorkPlan", ".venv", "logs"]
      missing_dirs: ["core", "app.py", "Config", "Contracts"]
      knowledge_base_seed: ["KnowledgeBase/README.md? (absent)", "KnowledgeBase_index.yaml (absent)"]
  - scope_sections: ["Agent 链路", "Memory Snapshot", "Index Schema"]
  - plan_links: {"02": "Kobe/WorkPlan/02TelegramBotGCmessagePlan.md", "03": "待建立"}
二级嵌套:
  - AutoDiscovery:
      steps: ["listdir(REPO_ROOT)", "detect files per requirement", "emit report"]
      output_fields: ["existing_dirs", "missing_dirs", "evidence_paths"]
  - PlanAlignment:
      inputs: ["plan_02 anchors", "plan_03 placeholders"]
      policy: "plan_01 overrides at index level"
三级嵌套:
  - AutoDiscovery.evidence_paths:
      KnowledgeBase: "exists -> True"
      Config: "exists -> False"
      Contracts: "exists -> False"
    interpretation: "缺失路径需在后续章节给出创建指引"
JSON Schema (MUST):
  {
    "$id": "kobe/agents/plan_overview.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["repo_root", "existing_dirs", "missing_dirs", "scope_sections", "plan_links"],
    "properties": {
      "repo_root": {"type": "string", "pattern": "^D:/AI_Projects/Kobe$"},
      "existing_dirs": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1
      },
      "missing_dirs": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1
      },
      "scope_sections": {
        "type": "array",
        "items": {"type": "string", "enum": ["Agent 链路", "Memory Snapshot", "Index Schema"]},
        "minItems": 3
      },
      "plan_links": {
        "type": "object",
        "required": ["02"],
        "properties": {
          "02": {"type": "string", "const": "Kobe/WorkPlan/02TelegramBotGCmessagePlan.md"},
          "03": {"type": "string"}
        },
        "additionalProperties": false
      }
    },
    "additionalProperties": false
  }
Prompt Catalog (MUST):
  - plan_autodiscovery_status（locale=zh-CN, audience=devops）
    用途: 汇报自动勘察结果，提醒仓库缺失目录或文件。
    触发条件: auto_discovery 流程完成后，无论是否存在缺失目录都发送。
    变量说明: {existing_dirs}: 已发现目录数组；{missing_dirs}: 缺失目录数组；{repo_root}: 仓库根路径。
    示例文案: "AutoDiscovery 完成：现有 ['KnowledgeBase','OpenaiAgents']，缺失 ['Config','Contracts']，repo_root=D:/AI_Projects/Kobe。"
    结构化定义:
      prompt_id=plan_autodiscovery_status locale=zh-CN audience=devops
      text="AutoDiscovery 完成：现有 {existing_dirs}，缺失 {missing_dirs}，repo_root={repo_root}"
  - plan_alignment_gap（locale=en-US, audience=arch）
    用途: 提示某章节缺失必填块，便于架构审核。
    触发条件: call_validate_plan_alignment 检测到 missing_blocks 非空时。
    变量说明: {section}: 章节名；{block}: 缺失块名称。
    示例文案: "Plan-01 alignment gap detected: section Agent 链路 missing required block Prompt Catalog."
    结构化定义:
      prompt_id=plan_alignment_gap locale=en-US audience=arch
      text="Plan-01 alignment gap detected: section {section} missing required block {block}"
  - plan_scope_ack（locale=zh-CN, audience=engineering）
    用途: 告知团队本计划只覆盖 Agent 链路/Memory/Index，避免引用 legacy 改造。
    触发条件: 文档入口渲染完成后主动发送。
    变量说明: {scope_sections}: 三个核心范围数组。
    示例文案: "本计划聚焦 ['Agent 链路','Memory Snapshot','Index Schema']，其它项目改造已废弃，请勿引用旧文档。"
    结构化定义:
      prompt_id=plan_scope_ack locale=zh-CN audience=engineering
      text="本计划聚焦 {scope_sections}，其余改造（如第三方 bot）已废弃，请勿引用旧文档"
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/plan_overview.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["prompt_id", "locale", "text", "audience"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^plan_"},
      "locale": {"type": "string", "enum": ["zh-CN", "en-US"]},
      "text": {"type": "string", "minLength": 8},
      "audience": {"type": "string"}
    },
    "additionalProperties": false
  }
Behavior Contract (MUST):
  - def behavior_plan_overview(): ...  文档入口合约
        """
        Steps:
          1. MUST run auto_discovery(repo_root) before rendering任何章节。
          2. MUST compare findings with structure_order requirements,记录缺口。
          3. MUST emit prompts plan_autodiscovery_status + plan_scope_ack to Config/prompts.*.
          4. SHOULD attach plan_alignment_gap for每个缺失块，供后续章节填补。
        Inputs: repo_root, expected_dirs, plan_links.
        Outputs: plan_overview_payload (符合 JSON Schema)。
        """
ToolCall / FunctionCall Contract (MUST):
  - def call_auto_discovery(repo_root: str) -> dict: ...  列目录并返回 existing/missing
        """MUST read filesystem只在 REPO_ROOT 内；失败 raise AutoDiscoveryError。"""
  - def call_validate_plan_alignment(section: str, required_blocks: list[str]) -> dict: ...  对齐校验
        """返回 {"section": section, "missing_blocks": [...]}；若为空则 status=ok。"""
Config Contract (MUST):
  - {REPO_ROOT}/Config/prompts.zh-CN.yaml MUST 包含 plan_autodiscovery_status 与 plan_scope_ack。
  - {REPO_ROOT}/Config/prompts.en-US.yaml MUST 包含 plan_alignment_gap。
  - {REPO_ROOT}/Contracts/behavior_contract.py MUST 实现 behavior_plan_overview。
Safety & Refusal Policy (MUST):
  - 若 auto_discovery 检测到 repo_root 不为 D:/AI_Projects/Kobe MUST refuse 生成并提示配置错误。
  - 若缺失 scope_sections 中任一项 MUST refuse 并输出 plan_alignment_gap。
  - 禁止引用 legacy TelegramBot ApplicationBuilder；检测到关键词 MUST refuse。
i18n & Brand Voice (MUST):
  - zh-CN：结构化、命令式语气；en-US：incident-style concise。
  - 所有提示禁止 emoji/俚语。
Output Contract (MUST):
  {
    "plan_overview_payload": {
      "$ref": "kobe/agents/plan_overview.schema.json"
    }
  }
Logging & Observability (MUST):
  - Logs MUST 包含 request_id (UUID), repo_root, discovery_lat_ms, missing_count, emitted_prompts。
  - Metrics: plan_autodiscovery_latency_ms histogram, plan_alignment_gaps_total counter。
  - Traces: span name="plan.overview".
Versioning & Traceability (MUST):
  - prompt_version=idx-v1; 修改本章节需 bump 并记录在 changelog。
  - 输出 plan_overview_payload 需打上 doc_commit 与 prompt_fingerprint(sha256)。
Golden Sample(s) (MUST >=3):
  - Sample A: repo_root=D:/AI_Projects/Kobe, existing_dirs=["KnowledgeBase","OpenaiAgents","WorkPlan"], missing_dirs=["Config","Contracts","core","app.py"], scope_sections=三项全，plan_links={"02":"Kobe/WorkPlan/02TelegramBotGCmessagePlan.md"}。
  - Sample B: existing_dirs 包含 TelegramBot 与 logs，missing_dirs 仅 ["core","app.py"]。
  - Sample C: plan_links 同上，并额外声明 plan_links.03="(pending)"。
Counter Sample(s) (MUST >=2):
  - Counter A: repo_root="E:/tmp" -> MUST fail pattern。
  - Counter B: scope_sections 少于 3 -> MUST fail minItems。
决策表 / 状态机 / 顺序化约束:
  | Step | Condition | Action |
  | auto_discovery | missing_dirs 非空 | emit plan_alignment_gap + mark status=degraded |
  | auto_discovery | missing_dirs 为空 | status=ready |
  | plan_alignment | required block 缺失 | refuse section 渲染 |
如何使用:
  - 渲染本文任何章节前运行 behavior_plan_overview -> 产出 plan_overview_payload -> 作为上下文写入后续章节。
agent如何读取:
  - Agents 仅需读取 plan_overview_payload.repo_root 与 scope_sections 以确定 index/KB 入口；其余字段供构建脚本使用。
边界与回退:
  - 如 auto_discovery 脚本失败（权限/路径）MUST 立即 halt 并提示手动校验。
  - 若 missing_dirs 包含 WorkPlan，应视为配置损坏，需从版本控制恢复后重试。
SLO / 阈值 / 触发条件:
  - Auto discovery latency SHOULD < 1s。
  - 缺口修复前禁止进入后续章节（门禁合规率 MUST 100%）。
  - 触发条件：missing_dirs 变为 0 且 scope_sections 满足 → 标记 ready 并允许 codegen。

# 标题: Agent 链路与运行编排
设计意图:
  - MUST 定义从用户意图判断到响应生成的完整链路（triage -> consult -> plan -> compose -> finalize），并与 02 文档 channel 层对接。
  - MUST 描述 AgentsBridge/AgentsGateway/Workflow Orchestrator 的接口契约、Streaming 行为、降级路径。
  - SHOULD 给出 token 预算、工具调用顺序、内存快照注入点，便于未来扩展其他渠道或 KB。
设计原因:
  - 仓库缺少 app.py/core 目录，Agent 层需要在 `OpenaiAgents/UnifiedCS` 下自建可复用基座。
  - Index 设计要求 Agent 执行 deterministic routing，必须提前冻结 Behavior/Tool 合约和输出格式。
接口锚点:
  - from OpenaiAgents.UnifiedCS.bridge import AgentsBridge  "{REPO_ROOT}/OpenaiAgents/UnifiedCS/bridge.py（待创建）"
  - from OpenaiAgents.UnifiedCS.gateway import AgentsGateway  "{REPO_ROOT}/OpenaiAgents/UnifiedCS/gateway.py（待创建）"
  - class WorkflowOrchestrator  "{REPO_ROOT}/OpenaiAgents/UnifiedCS/workflow.py：封装 triage→consult→plan→compose"
  - from KnowledgeBase.loader import MemoryLoader  "{REPO_ROOT}/KnowledgeBase/loader.py：加载 index / snapshot"
需求字段:
  - pipeline_stages: ["triage", "prepare_context", "consult_flow", "plan_flow", "compose_response", "finalize"]
  - inputs:
      core_envelope: "来自 channel 的统一 schema"
      memory_snapshot: "MemoryLoader 输出"
      agent_policies: ["llm_policy", "token_budget", "safety_rules"]
  - outputs:
      response_stream: "Markdown-structured 或 strict-json"
      telemetry: ["request_id", "convo_id", "stage_metrics", "tool_calls"]
      audit_log: ["prompt_version", "doc_commit", "usage"]
二级嵌套:
  - StageTransitions:
      triage -> prepare_context: "根据 intent_hint/kb_scope 选择 domain_profile"
      consult_flow -> plan_flow: "若 intent=consult 则跳过 plan_flow"
      plan_flow -> compose_response: "plan_flow 带来 structured plan，compose 渲染成 Markdown"
  - ResourceGuards:
      token_budget_per_call: 3000
      max_plan_depth: 3
      max_tool_calls: 4
三级嵌套:
  - Telemetry.stage_metrics.item: {"stage": "triage", "latency_ms": int, "tokens_in": int, "tokens_out": int}
  - ToolCall.record: {"tool": "mem_read", "args": dict, "result_ref": "blob://snapshot/..." }
  - SafetyRules: {"category": "policy_violation", "action": "refuse", "template": "refusal_policy#category"}
JSON Schema (MUST):
  {
    "$id": "kobe/agents/agent_pipeline.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["request_id", "convo_id", "stage", "status", "payload"],
    "properties": {
      "request_id": {"type": "string", "pattern": "^[a-f0-9-]{36}$"},
      "convo_id": {"type": "string"},
      "stage": {"type": "string", "enum": ["triage", "prepare_context", "consult_flow", "plan_flow", "compose", "finalize", "fallback"]},
      "status": {"type": "string", "enum": ["ok", "degraded", "refused", "error"]},
      "payload": {
        "type": "object",
        "required": ["core_envelope", "memory_ref", "agent_policy"],
        "properties": {
          "core_envelope": {"$ref": "kobe/core/core_envelope.schema.json"},
          "memory_ref": {"type": "string"},
          "agent_policy": {
            "type": "object",
            "required": ["token_budget", "llm_policy_key"],
            "properties": {
              "token_budget": {"type": "integer", "minimum": 1000},
              "llm_policy_key": {"type": "string"},
              "safety_rules": {"type": "array", "items": {"type": "string"}}
            }
          },
          "tool_calls": {"type": "array", "items": {"type": "string"}}
        },
        "additionalProperties": false
      },
      "telemetry": {
        "type": "object",
        "properties": {
          "stage_metrics": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["stage", "latency_ms"],
              "properties": {
                "stage": {"type": "string"},
                "latency_ms": {"type": "number", "minimum": 0},
                "tokens_in": {"type": "integer"},
                "tokens_out": {"type": "integer"}
              }
            }
          }
        }
      }
    },
    "additionalProperties": false
  }
Prompt Catalog (MUST):
  - agent_triage_system（locale=en-US, audience=llm）
    用途: 引导 LLM 判断用户意图（咨询/方案/操作）并选择 domain_profile。
    触发条件: 每次 pipeline 进入 triage 阶段。
    变量说明: {core_envelope.user_message}、{intent_candidates}、{domain_profiles.summary}。
    示例文案: "You are the Index Agent triage core... classify the request: {user_message}."
    结构化定义:
      prompt_id=agent_triage_system locale=en-US audience=llm
      text="You are the Index Agent triage core. Determine user intent for {core_envelope.user_message} using candidates {intent_candidates}，pick domain profile from {domain_profiles.summary}."
  - agent_consult_compose（locale=zh-CN, audience=llm）
    用途: 在咨询意图下生成简洁答案。
    触发条件: triage 判定 intent=consult。
    变量说明: {context_snippets}: 选定 entries；{tone}: 语气；{token_budget}: 最大 tokens。
    示例文案: "请基于{context_snippets}，以{tone}语气回答，长度限制 {token_budget} tokens。"
    结构化定义:
      prompt_id=agent_consult_compose locale=zh-CN audience=llm
      text="请用简洁段落回答用户问题。上下文：{context_snippets}，语气：{tone}，最大 {token_budget} tokens。"
  - agent_plan_executor（locale=en-US, audience=llm）
    用途: 生成步骤化方案。
    触发条件: intent=plan 或 operation。
    变量说明: {plan_context}: slot/selector 结果；{constraints}: 约束列表。
    示例文案: "Given context {plan_context} and constraints {constraints}, produce a numbered plan with reasons."
    结构化定义:
      prompt_id=agent_plan_executor locale=en-US audience=llm
      text="Given context {plan_context} and constraints {constraints}, produce stepwise plan with rationale."
  - agent_refusal_policy（locale=zh-CN, audience=llm）
    用途: 当安全/政策触发时输出拒绝模板。
    触发条件: safety rule 命中或 contract 校验失败。
    变量说明: {rule}: 触发规则；{contact}: 联系方式。
    示例文案: "因触发 {rule}，无法提供信息。若需了解更多，请联系 {contact}。"
    结构化定义:
      prompt_id=agent_refusal_policy locale=zh-CN audience=llm
      text="因触发 {rule}，无法提供信息。若需了解更多，请联系 {contact}。"
Prompt 变量表 (MUST):
  - 名称: core_envelope.user_message | 类型: string | 必填: 是 | 默认: 无 | 示例: "请给我销售日报" | 说明: triage 输入文本。
  - 名称: intent_candidates | 类型: list[string] | 必填: 是 | 默认: ["consult","plan","operation"] | 示例: ["consult","plan"] | 说明: 可选意图集合。
  - 名称: context_snippets | 类型: list[string] | 必填: 是 | 示例: ["销售额同比+12%"] | 说明: consult compose 用的上下文字段。
  - 名称: tone | 类型: string | 必填: 否 | 默认: "业务口吻" | 示例: "正式" | 说明: 输出语气。
  - 名称: plan_context | 类型: dict | 必填: 是 | 示例: {"slots":["流程","表格"]} | 说明: plan executor 的结构化输入。
  - 名称: constraints | 类型: list[string] | 必填: 否 | 示例: ["完成时间<=2天"] | 说明: 方案约束。
  - 名称: rule | 类型: string | 必填: 是 | 示例: "policy_violation" | 说明: 触发的拒绝策略编码。
  - 名称: contact | 类型: string | 必填: 否 | 默认: "support@company.com" | 示例: "ops@company.com" | 说明: 拒绝提示里的联系人。
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/agent_pipeline.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["prompt_id", "locale", "text", "audience"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^agent_"},
      "locale": {"type": "string", "enum": ["zh-CN", "en-US"]},
      "text": {"type": "string", "minLength": 20},
      "audience": {"type": "string"}
    },
    "additionalProperties": false
  }
Behavior Contract (MUST):
  - def behavior_agent_pipeline(): ...  Agent 链路行为合约
        """
        Inputs: core_envelope, memory_snapshot, agent_policy.
        Steps:
          1. MUST run triage_prompt -> classify intent (consult vs plan) and domain_profile。
          2. MUST call prepare_context: clip history, attach memory_snapshot slices, enforce token_budget。
          3. consult_flow: if intent=consult -> compose direct answer via agent_consult_compose prompt。
          4. plan_flow: if intent in ["plan","procedure"] -> run planner prompt -> produce structured plan。
          5. compose_response: unify plan/consult outputs into Markdown or strict JSON per agent_policy.output_mode。
          6. finalize: attach telemetry + audit log; if validation fails -> go to fallback stage。
        Outputs: streaming chunks + final payload matching agent_pipeline.schema。
        """
ToolCall / FunctionCall Contract (MUST):
  - def call_mem_read(slot: str, selectors: dict) -> dict: ...  读取 MemorySnapshot
        """MUST validate selectors via index schema; returns excerpt list; failure -> raise MemoryMissError。"""
  - def call_compose_reply(context: dict, plan: dict | None) -> str: ...  渲染回答
        """MUST respect output_mode; Markdown 模式需 escape；JSON 模式需校验 schema。"""
  - def call_summarize_history(convo_id: str) -> dict: ...  汇总上下文
        """用于超过 token_budget 时触发 summary_threshold。"""
Config Contract (MUST):
  - `{REPO_ROOT}/Config/prompts.zh-CN.yaml` MUST include agent_consult_compose, agent_refusal_policy。
  - `{REPO_ROOT}/Config/prompts.en-US.yaml` MUST include agent_triage_system, agent_plan_executor。
  - `{REPO_ROOT}/Contracts/toolcalls.py` MUST export call_mem_read/call_compose_reply/call_summarize_history。
  - `{REPO_ROOT}/Contracts/behavior_contract.py` MUST expose behavior_agent_pipeline。
Safety & Refusal Policy (MUST):
  - Safety rules triggered -> use agent_refusal_policy prompt, mark status=refused。
  - Token budget exceeded -> call_summarize_history;若 summary 失败 -> degrade (status=degraded)。
  - 不得触发外部工具无 schema 的调用；检测到 unauthorized tool -> refuse。
i18n & Brand Voice (MUST):
  - zh-CN 回复：专业、精炼，禁止口语/emoji。
  - en-US 回复：concise enterprise tone。
  - 所有 prompts 必须声明 locale 并匹配输出模式。
Output Contract (MUST):
  {
    "agent_response": {
      "type": "object",
      "required": ["mode", "content", "telemetry", "usage"],
      "properties": {
        "mode": {"type": "string", "enum": ["markdown-structured", "strict-json"]},
        "content": {"type": "string"},
        "telemetry": {"type": "object", "$ref": "kobe/agents/agent_pipeline.schema.json#/properties/telemetry"},
        "usage": {
          "type": "object",
          "required": ["input_tokens", "output_tokens", "total_tokens"],
          "properties": {
            "input_tokens": {"type": "integer"},
            "output_tokens": {"type": "integer"},
            "total_tokens": {"type": "integer"}
          }
        }
      }
    }
  }
Logging & Observability (MUST):
  - 每 stage MUST log {request_id, stage, status, latency_ms, tokens_in, tokens_out}。
  - Metrics: agent_pipeline_stage_latency_ms, agent_pipeline_fallback_total, agent_pipeline_refusal_total。
  - Distributed tracing: span per stage，parent span trace_id=request_id。
Versioning & Traceability (MUST):
  - prompt_version=agent-pipeline-v1；修改 Pipeline 或 prompts 必须 bump。
  - output_schema_id="agent_pipeline.schema.json@v1"；commit 时写入 doc_commit。
Golden Sample(s) (MUST >=3):
  - Sample A: intent=consult，直接 compose；mode=markdown-structured；usage total_tokens=1200。
  - Sample B: intent=plan，plan_flow 生成 3 steps -> compose -> strict-json 输出。
  - Sample C: intent=consult，但 token over limit -> summarize_history -> degrade status=degraded。
Counter Sample(s) (MUST >=2):
  - Counter A: stage missing -> schema validation fail。
  - Counter B: tool_calls 包含未知工具 -> refuse per policy。
决策表 / 状态机 / 顺序化约束:
  | Stage | Condition | Action |
  | triage | safety triggered | goto fallback(status=refused) |
  | prepare_context | tokens > budget | call summarize_history |
  | compose | output validation fail | attempt repair once else refuse |
如何使用:
  - AgentsBridge 将 core_envelope + memory_snapshot 输入 behavior_agent_pipeline，逐阶段 streaming 输出。
agent如何读取:
  - WorkflowOrchestrator 在 compose_response 阶段将 chunk feeding Telegram adapter（参照 plan_02）。
边界与回退:
  - Memory read miss -> fallback to summary snippet + degrade。
  - AgentsGateway error -> retry up to 2 次；仍失败则 fallback stage 输出固定模板。
SLO / 阈值 / 触发条件:
  - 首字节延迟 SHOULD < 1s。
  - 全流程成功率 MUST >= 98%。
  - fallback ratio > 2% -> trigger incident。

# 标题: Memory Snapshot 与 Loader
设计意图:
  - MUST 定义 KnowledgeBase → MemorySnapshot 的加载/刷新/查询流程，确保 Agent 链路能在内存中零磁盘访问。
  - SHOULD 支持 org-level 与 agency-level index 合并，输出可用于 mem_read/compose_reply 的视图。
  - MUST 提供热更新/健康检查指标，便于监控 snapshot 与底层文件一致性。
设计原因:
  - 仓库已有 `KnowledgeBase/` 目录但缺少 index YAML；需文档先定义 schema，再由 Loader 生成 snapshot。
  - Agent pipeline 依赖 deterministic context slices，必须有可验证的 Loader 契约与 JSON Schema。
接口锚点:
  - class MemoryLoader  "{REPO_ROOT}/OpenaiAgents/UnifiedCS/memory/loader.py: load_all() + watch()"
  - class MemorySnapshot  "{REPO_ROOT}/OpenaiAgents/UnifiedCS/memory/snapshot.py: immutable view"
  - from KnowledgeBase.index import load_org_index  "{REPO_ROOT}/KnowledgeBase/index.py"
  - from KnowledgeBase.agency import load_agency_index  "{REPO_ROOT}/KnowledgeBase/{agency}/index.py"
需求字段:
  - snapshot_fields: ["org_metadata", "agencies", "routing_table", "domain_profiles", "compose_rules", "entries"]
  - loader_config:
      base_path: "{REPO_ROOT}/KnowledgeBase"
      hot_reload: {"enabled": false, "interval_s": 300}
      checksum: "sha256"
  - health_checks: ["last_loaded_at", "file_count", "checksum_mismatch", "missing_agencies"]
二级嵌套:
  - Snapshot.agencies: dict keyed by agency_id -> AgencySnapshot
  - AgencySnapshot:
      fields: ["agency_id", "synonyms", "routing", "domain_profiles", "entries", "pricing"]
三 级嵌套:
  - DomainProfile: {"id": str, "selectors": list, "compose_rules": dict, "render_policy": dict}
  - Entry: {"slot": str, "content": str, "metadata": {"source": str, "updated_at": str}}
JSON Schema (MUST):
  {
    "$id": "kobe/kb/memory_snapshot.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["org_metadata", "agencies", "routing_table", "created_at"],
    "properties": {
      "org_metadata": {
        "type": "object",
        "required": ["org_id", "default_language"],
        "properties": {
          "org_id": {"type": "string"},
          "default_language": {"type": "string", "enum": ["zh-CN", "en-US"]},
          "description": {"type": "string"}
        },
        "additionalProperties": false
      },
      "routing_table": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["match", "agency_id"],
          "properties": {
            "match": {"type": "string"},
            "agency_id": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
          }
        }
      },
      "agencies": {
        "type": "object",
        "patternProperties": {
          "^[a-z0-9_-]+$": {
            "type": "object",
            "required": ["agency_id", "domain_profiles", "entries"],
            "properties": {
              "agency_id": {"type": "string"},
              "synonyms": {"type": "array", "items": {"type": "string"}},
              "domain_profiles": {"type": "array", "items": {"type": "string"}},
              "entries": {"type": "array", "items": {"type": "object"}},
              "pricing": {"type": "object"},
              "compose_rules": {"type": "object"},
              "render_policy": {"type": "object"}
            }
          }
        }
      },
      "created_at": {"type": "string", "format": "date-time"},
      "checksum": {"type": "string", "pattern": "^[a-f0-9]{64}$"}
    },
    "additionalProperties": false
  }
Prompt Catalog (MUST):
  - memory_loader_alert（locale=en-US, audience=ops）
    用途: 通知运维 MemoryLoader 在某个 agency 上检测到异常。
    触发条件: behavior_memory_loader 捕获 issue（schema error、文件缺失等）。
    变量说明: {issue}: 异常描述；{agency_id}: 机构 ID。
    示例文案: "MemoryLoader detected schema_error for agency biz_cd"
    结构化定义:
      prompt_id=memory_loader_alert locale=en-US audience=ops text="MemoryLoader detected {issue} for agency {agency_id}"
  - memory_snapshot_ready（locale=zh-CN, audience=engineering）
    用途: 宣布 snapshot 构建成功以及机构/条目数量，方便工程确认。
    触发条件: snapshot 构建结束且状态 ok。
    变量说明: {agency_count}: 机构数；{entry_count}: 条目数。
    示例文案: "MemorySnapshot 构建完成：机构 5，entries 420"
    结构化定义:
      prompt_id=memory_snapshot_ready locale=zh-CN audience=engineering text="MemorySnapshot 构建完成：机构 {agency_count}，entries {entry_count}"
  - memory_checksum_mismatch（locale=en-US, audience=devops）
    用途: 告警文件校验和与记录不一致。
    触发条件: checksum 比对失败。
    变量说明: {path}: 文件路径；{expected}: 期望值；{actual}: 实际值。
    示例文案: "Checksum mismatch for KnowledgeBase/biz_cd/index.yaml, expected abcd, got 1234"
    结构化定义:
      prompt_id=memory_checksum_mismatch locale=en-US audience=devops text="Checksum mismatch for {path}, expected {expected}, got {actual}"
Prompt 变量表:
  - 名称:path | 类型:string | 必填:是 | 默认:"" | 示例:"KnowledgeBase/biz_cd/index.yaml" | 说明: 出错文件路径。
  - 名称:agency_count | 类型:integer | 必填:是 | 默认:0 | 示例:5 | 说明: snapshot 中的机构数量。
  - 名称:entry_count | 类型:integer | 必填:是 | 默认:0 | 示例:420 | 说明: snapshot 条目数量。
  - 名称:issue | 类型:string | 必填:是 | 默认:"" | 示例:"schema_error" | 说明: 异常简称。
  - 名称:agency_id | 类型:string | 必填:是 | 默认:"" | 示例:"biz_cd" | 说明: 受影响机构。
  - 名称:expected | 类型:string | 必填:是 | 默认:"" | 示例:"abcd..." | 说明: 期望 checksum。
  - 名称:actual | 类型:string | 必填:是 | 默认:"" | 示例:"1234..." | 说明: 实际 checksum。
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/memory_loader.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["prompt_id", "locale", "text", "audience"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^memory_"},
      "locale": {"type": "string", "enum": ["zh-CN", "en-US"]},
      "text": {"type": "string", "minLength": 10},
      "audience": {"type": "string"}
    },
    "additionalProperties": false
  }
Behavior Contract (MUST):
  - def behavior_memory_loader(): ...  内存加载流程
        """
        Steps:
          1. MUST scan base_path for KnowledgeBase_index.yaml + agency subdirs。
          2. MUST validate YAML against index schema；失败 -> raise SchemaError。
          3. MUST compute sha256 checksum per file并记录在 snapshot。
          4. MUST emit health metrics (agency_count, entry_count, checksum_status)。
          5. SHOULD support refresh(refresh_reason) to rebuild snapshot under lock。
        Outputs: MemorySnapshot (immutable, JSON Schema compliant)。
        """
ToolCall / FunctionCall Contract (MUST):
  - def call_load_org_index(path: str) -> dict: ...  读取顶层 index
  - def call_load_agency_index(path: str) -> dict: ...  读取 agency index
  - def call_build_snapshot(org_index: dict, agency_indexes: dict) -> MemorySnapshot: ...  构建快照
Config Contract (MUST):
  - `{REPO_ROOT}/Config/prompts.en-US.yaml` MUST include memory_loader_alert & memory_checksum_mismatch。
  - `{REPO_ROOT}/Config/prompts.zh-CN.yaml` MUST include memory_snapshot_ready。
  - `{REPO_ROOT}/Contracts/toolcalls.py` MUST 暴露上述 tool 函数。
Safety & Refusal Policy (MUST):
  - YAML schema 验证失败 -> refuse snapshot 构建并触发 memory_loader_alert。
  - 缺失 agency index -> refuse 该 agency 并标记 missing_agencies；若 critical agency 缺失 -> stop pipeline。
  - checksum mismatch -> refuse promote snapshot，直到人工确认。
i18n & Brand Voice (MUST):
  - Ops 通知 (en-US) -> incident tone。
  - Dev 通知 (zh-CN) -> 结构化语句。
Output Contract (MUST):
  {
    "memory_snapshot": {
      "$ref": "kobe/kb/memory_snapshot.schema.json"
    }
  }
Logging & Observability (MUST):
  - Logs: {request_id, agency_id, file_path, checksum, status, latency_ms}。
  - Metrics: memory_loader_latency_ms, memory_loader_failures_total, memory_checksum_mismatch_total。
  - Health endpoint: `/internal/memory_health` 返回最新 snapshot 元数据。
Versioning & Traceability (MUST):
  - snapshot_version = "kb-snapshot-v1"；修改 schema 必须 bump version + doc_commit。
  - 记录 `snapshot_fingerprint=sha256(memory_snapshot JSON)`。
Golden Sample(s) (MUST >=3):
  - Sample A: org_id="kobe", agencies={"biz_cd": {...}}，entries=120。
  - Sample B: agencies 含多个 synonyms，routing_table 3 条。
  - Sample C: hot_reload.enabled=false，checksum=64 hex。
Counter Sample(s) (MUST >=2):
  - Counter A: missing org_metadata -> schema fail。
  - Counter B: checksum 长度非 64 -> fail。
决策表 / 状态机 / 顺序化约束:
  | Event | Condition | Action |
  | load | schema ok | build snapshot |
  | load | schema fail | abort + alert |
  | refresh | checksum mismatch | rebuild + alert |
如何使用:
  - Startup: call behavior_memory_loader -> produce snapshot -> pass to Agent pipeline。
  - Periodic refresh: optional watcher triggers refresh()。
agent如何读取:
  - AgentsBridge 只读 snapshot via MemorySnapshotView；禁止写入。
边界与回退:
  - 若 KnowledgeBase 目录缺失 -> fallback to empty snapshot, status=degraded（需告警）。
  - refresh 失败 -> 保留旧 snapshot 并记录 stale_since。
SLO / 阈值 / 触发条件:
  - 初次加载 SHOULD < 2s。
  - checksum mismatch MUST < 0.5% of files。
  - missing_agencies > 0 -> degrade 并阻止部署。

# 标题: 顶层 KnowledgeBase Index Schema（org 级）
设计意图:
  - MUST 定义 `KnowledgeBase_index.yaml`（org级）的字段、嵌套与校验，供 MemoryLoader 与后续工具引用。
  - SHOULD 提供 routing_table、agency list、global render policy，使 Agent 可快速定位 agency。
设计原因:
  - 目前 `KnowledgeBase_index.yaml` 不存在；文档需给出完整结构以生成初稿。
  - 需保证多 agency 并存时 deterministic routing，避免 channel 层重复逻辑。
接口锚点:
  - file: `{REPO_ROOT}/KnowledgeBase/KnowledgeBase_index.yaml`
  - class OrgIndexModel  `{REPO_ROOT}/OpenaiAgents/UnifiedCS/memory/models.py`
  - from scripts import validate_kb_index  `scripts/validate_kb_index.py`
需求字段:
  - org_metadata: {"org_id": str, "display_name": str, "default_language": "zh-CN|en-US", "timezone": "Asia/Shanghai"}
  - agencies: list of {"agency_id": str, "name": str, "path": str, "synonyms": list[str], "priority": int}
  - routing_table: list of {"patterns": list[str], "agency_id": str, "weight": float}
  - knowledge_assets: {"docs_path": str, "vector_index": str? (optional)}
  - prompts_overrides: {"welcome": str, "signoff": str}
二级嵌套:
  - agencies[].path -> `{REPO_ROOT}/KnowledgeBase/{agency_id}/{agency_id}_index.yaml`
  - routing_table[].patterns -> glob/regex strings
三级嵌套:
  - prompts_overrides.welcome: {"locale": str, "text": str}
  - knowledge_assets.vector_index: {"provider": "qdrant|pinecone|local", "dsn": str}
JSON Schema (MUST):
  {
    "$id": "kobe/kb/org_index.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["org_metadata", "agencies", "routing_table", "created_at"],
    "properties": {
      "org_metadata": {
        "type": "object",
        "required": ["org_id", "display_name", "default_language", "timezone"],
        "properties": {
          "org_id": {"type": "string"},
          "display_name": {"type": "string"},
          "default_language": {"type": "string", "enum": ["zh-CN", "en-US"]},
          "timezone": {"type": "string"},
          "description": {"type": "string"}
        }
      },
      "agencies": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["agency_id", "name", "path"],
          "properties": {
            "agency_id": {"type": "string"},
            "name": {"type": "string"},
            "path": {"type": "string"},
            "synonyms": {"type": "array", "items": {"type": "string"}},
            "priority": {"type": "integer", "minimum": 0, "maximum": 10}
          }
        },
        "minItems": 1
      },
      "routing_table": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["agency_id", "patterns"],
          "properties": {
            "agency_id": {"type": "string"},
            "patterns": {"type": "array", "items": {"type": "string"}},
            "weight": {"type": "number", "minimum": 0, "maximum": 1}
          }
        }
      },
      "knowledge_assets": {
        "type": "object",
        "properties": {
          "docs_path": {"type": "string"},
          "vector_index": {
            "type": "object",
            "properties": {
              "provider": {"type": "string"},
              "dsn": {"type": "string"}
            }
          }
        }
      },
      "prompts_overrides": {
        "type": "object",
        "properties": {
          "welcome": {"type": "string"},
          "signoff": {"type": "string"}
        }
      },
      "created_at": {"type": "string", "format": "date-time"}
    },
    "additionalProperties": false
  }
Prompt Catalog (MUST):
  - kb_index_missing_agency（locale=zh-CN, audience=kb-admin）
    用途: 提醒 KB 管理员某 agency 未在 org index 注册。
    触发条件: behavior_org_index_builder 检测 agencies[].path 缺失或文件不存在。
    变量说明: {agency_id}。
    示例文案: "机构 biz_cd 未在 KnowledgeBase_index.yaml 注册"
    结构化定义:
      prompt_id=kb_index_missing_agency locale=zh-CN audience=kb-admin text="机构 {agency_id} 未在 KnowledgeBase_index.yaml 注册"
  - kb_routing_conflict（locale=en-US, audience=arch）
    用途: 报告 routing patterns 发生冲突。
    触发条件: call_emit_routing_graph 检测到 pattern overlap。
    变量说明: {agency_a}, {agency_b}, {pattern}。
    示例文案: "Routing conflict between biz_cd and sales_ops pattern .*报表.*"
    结构化定义:
      prompt_id=kb_routing_conflict locale=en-US audience=arch text="Routing conflict between {agency_a} and {agency_b} pattern {pattern}"
  - kb_index_ready（locale=zh-CN, audience=engineering）
    用途: 通知工程团队顶层索引创建成功。
    触发条件: schema 验证与路径检查全部通过。
    变量说明: {agency_count}。
    示例文案: "KB 顶层索引创建完成，机构数 5"
    结构化定义:
      prompt_id=kb_index_ready locale=zh-CN audience=engineering text="KB 顶层索引创建完成，机构数 {agency_count}"
Prompt 变量表:
  - 名称:agency_id | 类型:string | 必填:是 | 示例:"biz_cd" | 说明: 机构标识。
  - 名称:agency_a | 类型:string | 必填:是 | 默认:"" | 示例:"biz_cd" | 说明: 冲突中的机构 A。
  - 名称:agency_b | 类型:string | 必填:是 | 默认:"" | 示例:"sales_ops" | 说明: 冲突中的机构 B。
  - 名称:pattern | 类型:string | 必填:是 | 默认:"" | 示例: ".*报表.*" | 说明: 冲突路由模式。
  - 名称:agency_count | 类型:integer | 必填:是 | 示例:5 | 说明: 索引中的机构数量。
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/org_index.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["prompt_id", "locale", "text", "audience"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^kb_"},
      "locale": {"type": "string"},
      "text": {"type": "string"},
      "audience": {"type": "string"}
    }
  }
Behavior Contract (MUST):
  - def behavior_org_index_builder(): ...  生成与校验逻辑
        """
        MUST ensure agencies[].path 存在；若不存在 -> refuse。
        MUST normalize patterns to regex；weight sum per agency <= 1。
        SHOULD generate default prompts_overrides 若缺失 locale。
        """
ToolCall / FunctionCall Contract (MUST):
  - def call_validate_org_index(data: dict) -> None
  - def call_emit_routing_graph(routing_table: list) -> str  "# returns dot graph path for CI"
Config Contract (MUST):
  - `{REPO_ROOT}/Config/prompts.zh-CN.yaml` MUST include kb_index_missing_agency, kb_index_ready。
  - `{REPO_ROOT}/Config/prompts.en-US.yaml` MUST include kb_routing_conflict。
Safety & Refusal Policy (MUST):
  - agency path missing -> refuse index 发布。
  - routing patterns overlap with same weight -> refuse until resolved。
  - default_language unsupported -> refuse。
i18n & Brand Voice (MUST):
  - zh-CN 条目 -> 业务口吻。
  - en-US -> architecture tone。
Output Contract (MUST):
  {
    "org_index": {
      "$ref": "kobe/kb/org_index.schema.json"
    }
  }
Logging & Observability (MUST):
  - Logs: {request_id, agency_id, pattern_count, weight_sum, status}。
  - Metrics: kb_index_agency_count, kb_routing_conflict_total。
Versioning & Traceability (MUST):
  - org_index_version=v1；修改 schema -> bump + doc_commit。
Golden Sample(s) (MUST >=3):
  - Sample A: agencies=["biz_cd"], routing_table 2 entries。
  - Sample B: agencies 两个，含 synonyms。
  - Sample C: knowledge_assets.vector_index provider="qdrant"。
Counter Sample(s) (MUST >=2):
  - Counter A: agencies 空 -> fail。
  - Counter B: routing_table item 缺 patterns -> fail。
决策表 / 状态机 / 顺序化约束:
  | Condition | Action |
  | agencies missing path | refuse + kb_index_missing_agency |
  | routing conflict | emit prompt kb_routing_conflict + block merge |
如何使用:
  - 初次创建 `KnowledgeBase_index.yaml` 时按 schema 填写；CI 运行 call_validate_org_index。
agent如何读取:
  - MemoryLoader.load_org_index -> produce org metadata + routing_table 供 triage 使用。
边界与回退:
  - 若 agencies>0 但 routing_table 空 -> fallback to priority order，标记 degraded。
SLO / 阈值 / 触发条件:
  - schema validation SHOULD 完成 <500ms。
  - routing conflict 必须在 PR 合并前解决（合规率 100%）。

# 标题: Agency Index Schema 与 Compose 规则
设计意图:
  - MUST 描述 `{REPO_ROOT}/KnowledgeBase/{agency}/{agency}_index.yaml` 的字段、compose_rules、render_policy。
  - SHOULD 允许 agency 自定义 slots/entries/pricing，同时保持核心 schema 稳定。
设计原因:
  - Agent pipeline 依赖 agency-specific metadata（domain_profiles、compose_rules、render_policy），需在 index 中定义。
接口锚点:
  - file pattern: `{REPO_ROOT}/KnowledgeBase/{agency}/{agency}_index.yaml`
  - class AgencyIndexModel  `{REPO_ROOT}/OpenaiAgents/UnifiedCS/memory/models.py`
  - from KnowledgeBase.compose import render_frame  `{REPO_ROOT}/OpenaiAgents/UnifiedCS/compose/frame.py`
需求字段:
  - agency_metadata: {"agency_id", "display_name", "locale", "timezone", "contact"}
  - domain_profiles: list of {"id", "intent", "selectors", "compose_rules"}
  - compose_rules:
      structure: {"header": str, "body": list[str], "footer": str}
      tokens_budget: {"max_tokens": int, "buffer": int}
  - render_policy: {"markdown": {"allow_code": bool}, "json": {"schema_id": str}}
  - entries:
      list of {"slot": str, "content": str, "summary": str, "source": str, "updated_at": str}
  - pricing: {"currency": "CNY|USD", "unit": str, "calculation": "deterministic expression"}
二级嵌套:
  - domain_profiles[].selectors -> list of {"slot": str, "operator": "equals|contains|regex", "value": str}
  - compose_rules.body -> array of template strings referencing {slot} placeholders
三级嵌套:
  - pricing.calculation -> AST nodes {"type": "multiply|add|lookup", "args": [...]}
JSON Schema (MUST):
  {
    "$id": "kobe/kb/agency_index.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["agency_metadata", "domain_profiles", "entries", "compose_rules", "render_policy"],
    "properties": {
      "agency_metadata": {
        "type": "object",
        "required": ["agency_id", "display_name", "locale"],
        "properties": {
          "agency_id": {"type": "string"},
          "display_name": {"type": "string"},
          "locale": {"type": "string"},
          "timezone": {"type": "string"},
          "contact": {"type": "string"}
        }
      },
      "domain_profiles": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["id", "intent", "selectors"],
          "properties": {
            "id": {"type": "string"},
            "intent": {"type": "string", "enum": ["consult", "plan", "operation"]},
            "selectors": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["slot", "operator", "value"],
                "properties": {
                  "slot": {"type": "string"},
                  "operator": {"type": "string", "enum": ["equals", "contains", "regex"]},
                  "value": {"type": "string"}
                }
              }
            },
            "compose_rules": {"type": "object"}
          }
        }
      },
      "entries": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["slot", "content", "source"],
          "properties": {
            "slot": {"type": "string"},
            "content": {"type": "string"},
            "summary": {"type": "string"},
            "source": {"type": "string"},
            "updated_at": {"type": "string", "format": "date-time"}
          }
        }
      },
      "compose_rules": {
        "type": "object",
        "required": ["header", "body", "footer"],
        "properties": {
          "header": {"type": "string"},
          "body": {"type": "array", "items": {"type": "string"}},
          "footer": {"type": "string"},
          "tokens_budget": {
            "type": "object",
            "properties": {
              "max_tokens": {"type": "integer"},
              "buffer": {"type": "integer"}
            }
          }
        }
      },
      "render_policy": {
        "type": "object",
        "properties": {
          "markdown": {"type": "object", "properties": {"allow_code": {"type": "boolean"}}},
          "json": {"type": "object", "properties": {"schema_id": {"type": "string"}}}
        }
      },
      "pricing": {"type": "object"}
    },
    "additionalProperties": false
  }
Prompt Catalog (MUST):
  - agency_compose_header（locale=zh-CN, audience=llm）
    用途: 生成回答顶部框架，展示机构与领域名称。
    触发条件: compose_response 初始化 header。
    变量说明: {agency_display_name}, {domain_name}。
    示例文案: "### 零售事业部 | 销售洞察"
    结构化定义:
      prompt_id=agency_compose_header locale=zh-CN audience=llm text="### {agency_display_name} | {domain_name}"
  - agency_compose_body（locale=zh-CN, audience=llm）
    用途: 渲染主体段落或列表。
    触发条件: compose_response 渲染 body 模板。
    变量说明: {body_template}, {slot_values}。
    示例文案: "{body_template}"（模板内嵌 slot 占位符）。
    结构化定义:
      prompt_id=agency_compose_body locale=zh-CN audience=llm text="{body_template}"
  - agency_pricing_alert（locale=en-US, audience=ops）
    用途: 报告 agency pricing 计算失败。
    触发条件: call_calculate_pricing 抛错。
    变量说明: {agency_id}, {error}.
    示例文案: "Pricing calculation failed for biz_cd: divide-by-zero"
    结构化定义:
      prompt_id=agency_pricing_alert locale=en-US text="Pricing calculation failed for {agency_id}"
Prompt 变量表:
  - 名称:agency_display_name | 类型:string | 必填:是 | 默认:"" | 示例:"零售事业部" | 说明: 展示名称。
  - 名称:domain_name | 类型:string | 必填:是 | 默认:"" | 示例:"销售洞察" | 说明: 当前 domain。
  - 名称:body_template | 类型:string | 必填:是 | 默认:"" | 示例:"- 指标：{metric}" | 说明: 模板文本。
  - 名称:slot_values | 类型:list[string] | 必填:否 | 默认:[] | 示例:["指标：12%"] | 说明: 填充模板的值。
  - 名称:agency_id | 类型:string | 必填:是 | 示例:"biz_cd" | 说明: 机构 identifier。
  - 名称:error | 类型:string | 必填:是 | 示例:"divide-by-zero" | 说明: 错误详情。
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/agency_index.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["prompt_id", "locale", "text"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^agency_"},
      "locale": {"type": "string"},
      "text": {"type": "string"}
    }
  }
Behavior Contract (MUST):
  - def behavior_agency_index_builder(): ...  机构索引构建
        """
        MUST merge domain_profiles + entries -> AgencySnapshot。
        MUST validate tokens_budget against pipeline policy。
        SHOULD auto-generate compose rules (header/body/footer) when placeholders detected。
        """
ToolCall / FunctionCall Contract (MUST):
  - def call_render_compose_template(compose_rules: dict, slots: dict) -> str
  - def call_calculate_pricing(pricing_config: dict, inputs: dict) -> dict
Config Contract (MUST):
  - prompts zh-CN -> agency_compose_header/body。
  - prompts en-US -> agency_pricing_alert。
Safety & Refusal Policy (MUST):
  - missing entries -> refuse compose。
  - pricing calculation exception -> refuse quoting，发出警报。
i18n & Brand Voice (MUST):
  - zh-CN compose -> BI 风格，提供“概览/指标/建议”模板。
  - en-US pricing -> concise numeric phrasing。
Output Contract (MUST):
  {
    "agency_index": {
      "$ref": "kobe/kb/agency_index.schema.json"
    }
  }
Logging & Observability (MUST):
  - Metrics: agency_index_slot_count, agency_compose_render_latency。
  - Logs: {agency_id, domain_id, slot, template_version}。
Versioning & Traceability (MUST):
  - agency_index_version=v1；SLO 变更需 bump。
Golden Sample(s):
  - Sample A: agency=finance_kb，domain_profiles=consult+plan。
  - Sample B: render_policy.markdown.allow_code=false。
  - Sample C: pricing currency="CNY"，calculation=deterministic AST。
Counter Sample(s):
  - Counter A: compose_rules.body empty -> schema fail。
  - Counter B: locale unsupported -> fail。
决策表:
  | Condition | Action |
  | entries missing slot | refuse publish |
  | tokens_budget < pipeline requirement | raise error |
如何使用:
  - 每个 agency 维护独立 index；MemoryLoader 合并后提供给 pipeline。
agent如何读取:
  - consult_flow 读取 compose_rules.body -> 组装 Markdown。
边界与回退:
  - 若 agency index 失效 -> fallback to org default response + degrade。
SLO:
  - agency index 校验 SHOULD < 300ms。
  - compose 渲染成功率 MUST >= 99%。

# 标题: Selectors 与 Slots 契约
设计意图:
  - MUST 定义 selectors/slots 字段及匹配语义，供 triage/plan_flow/compose 使用。
  - SHOULD 允许可扩展的 slot 类型（text/table/metric）并提供验证规则。
设计原因:
  - Agent pipeline 的 domain_profiles 依赖 selectors 决定 context；需统一 matcher 语法。
接口锚点:
  - from OpenaiAgents.UnifiedCS.selectors import SelectorEngine  "{REPO_ROOT}/OpenaiAgents/UnifiedCS/selectors/engine.py"
  - class SlotDefinition  "{REPO_ROOT}/OpenaiAgents/UnifiedCS/selectors/slots.py"
  - scripts/validate_selectors.py
需求字段:
  - selector_fields: {"slot": str, "operator": "equals|contains|regex|range", "value": str|dict}
  - slot_types: ["text", "metric", "table", "faq"]
  - slot_schema:
      base: {"slot": str, "type": slot_types, "content": str, "metadata": dict}
      metric: {"value": number, "unit": str, "period": str}
      table: {"columns": list[str], "rows": list[list[str]]}
  - normalization_rules: {"case_sensitive": false, "trim": true}
二级嵌套:
  - SelectorEngine:
      pipelines: ["preprocess", "match", "score", "resolve"]
      preprocess: {"lowercase": true, "strip_punctuation": true}
  - SlotRegistry:
      required_fields: ["slot", "type", "content"]
      optional_fields: ["summary", "source", "tags"]
三级嵌套:
  - range operator value -> {"min": number, "max": number, "inclusive": bool}
  - metric metadata -> {"data_source": str, "currency": str?}
JSON Schema (MUST):
  {
    "$id": "kobe/kb/slot.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["slot", "type", "content"],
    "properties": {
      "slot": {"type": "string"},
      "type": {"type": "string", "enum": ["text", "metric", "table", "faq"]},
      "content": {"type": "string"},
      "metadata": {"type": "object"},
      "metric": {
        "type": "object",
        "properties": {
          "value": {"type": "number"},
          "unit": {"type": "string"},
          "period": {"type": "string"}
        }
      },
      "table": {
        "type": "object",
        "properties": {
          "columns": {"type": "array", "items": {"type": "string"}},
                      "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}
        }
      }
    },
    "additionalProperties": false
  }
Prompt Catalog (MUST):
  - selector_match_debug（locale=en-US, audience=engineering）
    用途: 在调试 selector 结果时输出匹配轨迹。
    触发条件: 行为 behavior_selector_engine 开启 debug 标志。
    变量说明: {stage}, {slot}, {operator}, {score}.
    示例文案: "Selector match trace: stage=triage, slot=report, operator=regex, score=0.82"
    结构化定义:
      prompt_id=selector_match_debug locale=en-US text="Selector match trace: stage={stage}, slot={slot}, operator={operator}, score={score}"
  - slot_validation_error（locale=zh-CN, audience=kb-admin）
    用途: 提醒 slot 定义不符合 schema。
    触发条件: call_validate_slot 抛出异常。
    变量说明: {slot}, {reason}.
    示例文案: "Slot sales_table 校验失败: 缺少 columns"
    结构化定义:
      prompt_id=slot_validation_error locale=zh-CN text="Slot {slot} 校验失败: {reason}"
  - slot_missing（locale=zh-CN, audience=kb-admin）
    用途: 提醒 agency index 漏填需要的 slot。
    触发条件: selectors 匹配到 slot 但 entries 中不存在。
    变量说明: {slot}.
    示例文案: "缺少 slot plan_steps，请在 agency index 中补齐"
    结构化定义:
      prompt_id=slot_missing locale=zh-CN text="缺少 slot {slot}，请在 agency index 中补齐"
Prompt 变量表:
  - 名称:stage | 类型:string | 必填:是 | 默认:"" | 示例:"triage" | 说明: 所在阶段。
  - 名称:slot | 类型:string | 必填:是 | 默认:"" | 示例:"report" | 说明: slot 标识。
  - 名称:operator | 类型:string | 必填:是 | 默认:"equals" | 示例:"regex" | 说明: selector 运算符。
  - 名称:score | 类型:number | 必填:是 | 默认:0 | 示例:0.82 | 说明: 匹配得分。
  - 名称:reason | 类型:string | 必填:是 | 默认:"" | 示例:"缺少 columns 字段" | 说明: 校验失败原因。
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/selector_slot.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["prompt_id", "locale", "text"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^slot_|^selector_"},
      "locale": {"type": "string"},
      "text": {"type": "string"}
    }
  }
Behavior Contract (MUST):
  - def behavior_selector_engine(): ...  选择器流程
        """
        MUST preprocess user_message -> tokens。
        MUST evaluate selectors in order of priority。
        SHOULD compute scores and log top 3 matches。
        """
  - def behavior_slot_validator(): ...  slot 校验
        """
        MUST validate slot schema per type。
        MUST enforce normalization rules。
        """
ToolCall / FunctionCall Contract (MUST):
  - def call_match_selectors(core_envelope: dict, selectors: list[dict]) -> dict
  - def call_validate_slot(slot: dict) -> None
Config Contract (MUST):
  - prompts: selector_match_debug (en-US), slot_validation_error/missing (zh-CN)。
Safety & Refusal Policy (MUST):
  - selector 无匹配 -> degrade consult_flow (status=degraded)。
  - slot 校验失败 -> refuse deploy until fixed。
i18n & Brand Voice (MUST):
  - Debug prompts -> English。
  - QA prompts -> Chinese instructions。
Output Contract (MUST):
  {
    "selector_result": {
      "type": "object",
      "required": ["matched_slots", "scores"],
      "properties": {
        "matched_slots": {"type": "array", "items": {"type": "string"}},
        "scores": {"type": "array", "items": {"type": "number"}}
      }
    }
  }
Logging & Observability (MUST):
  - Metrics: selector_latency_ms, selector_miss_total, slot_validation_fail_total。
  - Logs: {convo_id, stage, slot, operator, score}。
Versioning & Traceability (MUST):
  - selector_engine_version=v1；slot_schema_version=v1。
Golden Sample(s):
  - Sample A: slot type text, selector equals "report".
  - Sample B: slot type metric (value 1234, unit "CNY").
  - Sample C: table slot with columns ["KPI","Value"]。
Counter Sample(s):
  - Counter A: slot type "video" -> fail。
  - Counter B: range operator missing min/max -> fail。
决策表:
  | Condition | Action |
  | match score < threshold | fallback to default domain |
  | slot missing | emit prompt slot_missing |
如何使用:
  - DomainProfiles 在 index 中引用 selectors；Engine 在 triage/plan 流中调用。
agent如何读取:
  - consult_flow receives matched_slots -> load entries -> compose。
边界与回退:
  - 若 selectors 全失败 -> route to org default agency。
SLO:
  - selector latency SHOULD < 10ms。
  - slot validation failure MUST < 1%。

# 标题: Pricing 聚合与预算策略
设计意图:
  - MUST 定义定价字段、聚合器逻辑、token/费用预算，使 Agent 输出可引用 deterministic 定价。
  - SHOULD 允许 agency 自定义 pricing 模板，同时提供 fallback 逻辑。
设计原因:
  - BI 场景需要稳定的价格/成本输出； index 必须提供 deterministic aggregator，避免 LLM 随意估算。
接口锚点:
  - from OpenaiAgents.UnifiedCS.aggregators.pricing import PricingAggregator
  - from KnowledgeBase.pricing import pricing_expression.yaml
  - scripts/validate_pricing.py
需求字段:
  - pricing_inputs: {"base_fee": number, "unit_fee": number, "currency": "CNY|USD", "tiers": list}
  - aggregator_config:
      expression: "base_fee + units * unit_fee"
      rounding: {"mode": "half_up", "precision": 2}
      currency_format: {"CNY": "¥{value}", "USD": "${value}"}
  - budget_policy:
      per_call_tokens: 3000
      per_flow_tokens: 6000
      summary_threshold_tokens: 2200
二级嵌套:
  - tiers[]: {"threshold": int, "unit_fee": number}
  - currency_format -> string templates
三级嵌套:
  - expression AST -> nodes {"type": "add|multiply|number|variable"}
JSON Schema (MUST):
  {
    "$id": "kobe/pricing/aggregator.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["currency", "expression", "rounding"],
    "properties": {
      "currency": {"type": "string", "enum": ["CNY", "USD"]},
      "expression": {"type": "string"},
      "rounding": {
        "type": "object",
        "required": ["mode", "precision"],
        "properties": {
          "mode": {"type": "string", "enum": ["half_up", "floor", "ceil"]},
          "precision": {"type": "integer", "minimum": 0, "maximum": 4}
        }
      },
      "tiers": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["threshold", "unit_fee"],
          "properties": {
            "threshold": {"type": "integer", "minimum": 0},
            "unit_fee": {"type": "number", "minimum": 0}
          }
        }
      }
    },
    "additionalProperties": false
  }
Prompt Catalog (MUST):
  - pricing_summary（locale=zh-CN, audience=llm）
    用途: 在回复中展示费用拆解。
    触发条件: pricing_result 计算成功且需要展示。
    变量说明: {base_fee}, {units}, {total}。
    示例文案: "费用：基础 100，用量 3，总计 160"
    结构化定义:
      prompt_id=pricing_summary locale=zh-CN text="费用：基础 {base_fee}，用量 {units}，总计 {total}"
  - budget_alert（locale=en-US, audience=ops）
    用途: 当 token usage 超过阈值时告警。
    触发条件: behavior_budget_guard 检测 tokens > policy。
    变量说明: {stage}, {tokens}。
    示例文案: "Token budget exceeded: stage=compose, tokens=3500"
    结构化定义:
      prompt_id=budget_alert locale=en-US text="Token budget exceeded: stage={stage}, tokens={tokens}"
  - pricing_error（locale=en-US, audience=ops）
    用途: 报告聚合器计算失败。
    触发条件: call_calculate_total 抛错。
    变量说明: {error}.
    示例文案: "Pricing calc failed: divide-by-zero"
    结构化定义:
      prompt_id=pricing_error locale=en-US text="Pricing calc failed: {error}"
Prompt 变量表:
  - 名称:base_fee | 类型:number | 必填:是 | 默认:0 | 示例:100 | 说明: 基础费用。
  - 名称:units | 类型:number | 必填:是 | 默认:0 | 示例:3 | 说明: 用量。
  - 名称:total | 类型:number | 必填:是 | 默认:0 | 示例:160 | 说明: 合计费用。
  - 名称:stage | 类型:string | 必填:是 | 示例:"compose" | 说明: 触发阶段。
  - 名称:tokens | 类型:integer | 必填:是 | 默认:0 | 示例:3500 | 说明: 使用 tokens。
  - 名称:error | 类型:string | 必填:是 | 示例:"divide-by-zero" | 说明: 错误详情。
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/pricing.schema.json",
    "type": "object",
    "required": ["prompt_id", "locale", "text"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^pricing_|^budget_"},
      "locale": {"type": "string"},
      "text": {"type": "string"}
    }
  }
Behavior Contract (MUST):
  - def behavior_pricing_aggregator(): ...  费用聚合
        """
        Inputs: pricing_inputs, aggregator_config。
        MUST validate expression variables exist。
        MUST apply tiers for units > threshold。
        SHOULD format currency per locale。
        """
  - def behavior_budget_guard(): ...  token 预算守卫
        """
        MUST enforce per_call/per_flow limits。
        MUST trigger summarize when summary_threshold exceeded。
        """
ToolCall / FunctionCall Contract (MUST):
  - def call_calculate_total(pricing_inputs: dict, aggregator: dict) -> dict
  - def call_check_budget(stage: str, tokens_used: int, policy: dict) -> dict
Config Contract:
  - prompts zh-CN -> pricing_summary；en-US -> budget_alert/pricing_error。
Safety & Refusal Policy:
  - Pricing calculation error -> refuse quoting, fallback to "价格稍后提供" 模板。
  - Token budget exceed and summary fails -> refuse with budget_alert。
i18n & Brand Voice:
  - zh-CN pricing -> “费用说明”模板；en-US budget -> alert tone。
Output Contract:
  {
    "pricing_result": {
      "type": "object",
      "required": ["currency", "total", "breakdown"],
      "properties": {
        "currency": {"type": "string"},
        "total": {"type": "number"},
        "breakdown": {"type": "object"}
      }
    }
  }
Logging & Observability:
  - Metrics: pricing_calc_latency_ms, budget_exceed_total。
  - Logs: {request_id, stage, units, total, tokens}.
Versioning:
  - pricing_aggregator_version=v1；policy changes require bump。
Golden Sample(s):
  - Sample A: base_fee=100, units=3, result=160。
  - Sample B: tier threshold triggered -> total 250。
  - Sample C: USD currency template。
Counter Sample(s):
  - Counter A: rounding precision >4 -> fail。
  - Counter B: expression uses undefined variable -> fail。
决策表:
  | Condition | Action |
  | tokens > per_flow | trigger summarize |
  | pricing error | emit pricing_error prompt + refuse |
如何使用:
  - compose_response 引用 pricing_result 生成“费用说明”段落。
agent如何读取:
  - plan_flow attaches pricing_result to output JSON。
边界与回退:
  - 缺少 pricing config -> fallback to “暂未提供”模板 + degrade。
SLO:
  - pricing 计算 SHOULD < 20ms。
  - budget_alert 触发率 MUST < 5%。

# 标题: Index 构建与发布流程
设计意图:
  - MUST 给出 KnowledgeBase 索引从编辑→校验→发布→部署的流水线，确保文档与 snapshot 一致。
  - SHOULD 定义 CI 脚本、review 清单、回滚策略。
设计原因:
  - 目前缺少任何自动化脚本；需要文档驱动 scripts/check_* 的实现。
接口锚点:
  - scripts/check_kb_index.py
  - scripts/generate_snapshot.py
  - github workflow `.github/workflows/kb-validate.yml` (待建)
需求字段:
  - pipeline_steps: ["lint_yaml", "schema_validate", "diff_snapshot", "publish", "notify"]
  - required_tools: ["yamllint", "ajv", "pydantic", "sha256sum"]
  - approvals: {"kb_owner": 1, "arch": 1}
二级嵌套:
  - Notifications: prompts -> plan_autodiscovery_status, memory_snapshot_ready
  - Publish targets: {snapshot_path: "{REPO_ROOT}/OpenaiAgents/UnifiedCS/memory/snapshots/{timestamp}.json"}
三级嵌套:
  - Rollback plan: {"restore_snapshot": path, "invalidate_cache": command, "notify": prompt_id}
JSON Schema (MUST):
  {
    "$id": "kobe/kb/pipeline.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["pipeline_steps", "approvals"],
    "properties": {
      "pipeline_steps": {"type": "array", "items": {"type": "string"}},
      "approvals": {
        "type": "object",
        "properties": {
          "kb_owner": {"type": "integer", "minimum": 1},
          "arch": {"type": "integer", "minimum": 1}
        }
      },
      "publish_targets": {"type": "object"}
    }
  }
Prompt Catalog (MUST):
  - kb_pipeline_failed（locale=en-US, audience=ops）
    用途: 通知流水线某步骤失败。
    触发条件: pipeline 任一步骤错误。
    变量说明: {step}, {reason}.
    示例文案: "KB pipeline step schema_validate failed: missing routing_table"
    结构化定义:
      prompt_id=kb_pipeline_failed locale=en-US text="KB pipeline step {step} failed: {reason}"
  - kb_pipeline_success（locale=zh-CN, audience=engineering）
    用途: 宣告成功发布并提供 snapshot 路径。
    触发条件: 所有步骤成功并完成发布。
    变量说明: {snapshot_path}.
    示例文案: "索引发布成功：snapshot=OpenaiAgents/UnifiedCS/memory/snapshots/2025-10-27.json"
    结构化定义:
      prompt_id=kb_pipeline_success locale=zh-CN text="索引发布成功：snapshot={snapshot_path}"
Prompt 变量表:
  - 名称:step | 类型:string | 必填:是 | 示例:"schema_validate" | 说明: 出错步骤。
  - 名称:reason | 类型:string | 必填:是 | 示例:"routing_table missing" | 说明: 错误原因。
  - 名称:snapshot_path | 类型:string | 必填:是 | 默认:"" | 示例:"OpenaiAgents/.../snapshot.json" | 说明: 发布的快照路径。
Prompt JSON Schema (MUST):
  {
    "$id": "kobe/prompts/kb_pipeline.schema.json",
    "type": "object",
    "required": ["prompt_id", "locale", "text"],
    "properties": {
      "prompt_id": {"type": "string", "pattern": "^kb_pipeline_"},
      "locale": {"type": "string"},
      "text": {"type": "string"}
    }
  }
Behavior Contract (MUST):
  - def behavior_kb_pipeline(): ...  端到端流程
        """
        Steps: lint_yaml -> schema_validate (org + agency) -> run selector/slot validation -> build snapshot -> diff with previous -> publish -> notify。
        MUST abort on first failure。
        """
ToolCall / FunctionCall Contract:
  - def call_run_lint(paths: list[str]) -> None
  - def call_diff_snapshot(old: str, new: str) -> dict
Config Contract:
  - prompts zh-CN -> kb_pipeline_success；en-US -> kb_pipeline_failed。
Safety & Refusal Policy:
  - lint 或 schema fail -> refuse publish。
  - approvals 未满足 -> refuse。
i18n & Brand Voice:
  - success -> zh-CN 简报；failure -> en-US incident。
Output Contract:
  {
    "kb_pipeline_report": {
      "type": "object",
      "required": ["status", "snapshot_path", "issues"],
      "properties": {
        "status": {"type": "string", "enum": ["success", "failed"]},
        "snapshot_path": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
Logging & Observability:
  - Metrics: kb_pipeline_duration_ms, kb_pipeline_fail_total。
  - Logs: {request_id, step, status, duration_ms}。
Versioning:
  - pipeline_version=v1；workflow 更新需 bump + doc_commit。
Golden Sample(s):
  - Sample A: 所有 steps 成功 -> status success。
  - Sample B: schema_validate fail -> issues list 包含 path。
  - Sample C: diff_snapshot detect changes -> publish target created。
Counter Sample(s):
  - Counter A: approvals.kb_owner=0 -> schema fail。
  - Counter B: pipeline_steps 空 -> fail。
决策表:
  | Step | Condition | Action |
  | schema_validate | fail | emit kb_pipeline_failed |
  | publish | success | emit kb_pipeline_success |
如何使用:
  - CI workflow 调用 behavior_kb_pipeline，阻止未通过的索引合并。
agent如何读取:
  - Agent 仅依赖最终 snapshot；pipeline 报告供运维审计。
边界与回退:
  - publish 失败 -> restore previous snapshot +通知。
SLO:
  - pipeline duration SHOULD < 3min。
  - failure rate MUST < 2%。


 ``` 
 ``` 
