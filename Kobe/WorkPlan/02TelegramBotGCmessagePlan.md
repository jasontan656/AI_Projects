---
doc:
  id: 02TelegramBotGCmessagePlan
  title: Telegram BI/Index 方案与 Agent 开发工作笔记
  language: zh-CN
  created: 2025-10-25
  updated: 2025-10-26
  owner: owner
  editors:
    - AI Assistant
  status: draft
  schema_version: 1.1.0
  kind: universal-ssot-plan
  family: kobe
  repository_root: AUTO
  focus_note_path: D:\\\\AI_Projects\\\\Kobe\\\\WorkPlan\\\\02TelegramBotGCmessagePlan.md
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
  - date: 2025-10-27
    author: AI Assistant
    change_type: breaking
    change: 增补人类可读 Prompt 规范、修正元数据、引入全局决定性配置与变量表
    migration_guide: 更新 repository_root/focus_note_path/knowledge_base_root 为绝对路径；在正文首部声明 seed/token 预算等；为各 Prompt 增加中文说明与变量表
    rollback_notes: 如需回退，请将 doc.id 恢复为历史值并移除全局配置小节；但不建议
```python
# 标题: Auto‑Discovery 仓库锚点扫描
设计意图: "在渲染正文前自动扫描仓库锚点与目录结构，并落盘扫描结果，供 CI 与 codegen 使用。"
设计原因: "确保 repository_root/knowledge_base_root 为 AUTO 时，工具仍能依据本文记录进行一致解析。"
接口锚点:
from scripts.check_anchors import scan_repo  "scripts/check_anchors.py"
需求字段 = {
"repo_root": "D:/AI_Projects/Kobe",
"existing_dirs": ["KnowledgeBase","SharedUtility","WorkPlan","OpenaiAgents","TelegramBot","Tests","logs","core","Config","Contracts"],
"missing_dirs": [],
"status": "ready",
"actions": ["app.py created; core/Config/Contracts present (placeholders)"] ,
"env_files": [".env"],
"notes": "OpenaiAgents/、TelegramBot/、Tests/ 当前为空占位；仅用于后续重建"
}
JSON Schema (MUST):
  {
    "$id": "kobe/anchors/auto_discovery.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["repo_root", "existing_dirs", "missing_dirs"],
    "properties": {
      "repo_root": {"type": "string"},
      "existing_dirs": {"type": "array", "items": {"type": "string"}},
      "missing_dirs": {"type": "array", "items": {"type": "string"}},
      "env_files": {"type": "array", "items": {"type": "string"}},
      "notes": {"type": "string"}
    }
  }
如何使用: "CI 读取本节 JSON，校验 missing_dirs 为空后再运行 codegen；否则 fail。"
agent如何读取: "Agents 层无需消费，仅供渠道与构建工具使用。"
边界与回退: "若扫描失败，部署 MUST 阻断；人工补齐目录后重试。"
SLO / 阈值 / 触发条件: "扫描 SHOULD < 1s；missing_dirs==[] 触发通过。"# 标题: 全局运行参数与决定性配置
设计意图: "集中声明可重现所需的解码/预算/版本/脱敏/指纹等参数，作为全局约束。"
设计原因: "保证不同章节实现与生成的代码在同一组决定性参数下可复现、可校验。"
接口锚点:
class GlobalRuntimePolicy: ...  "Contracts/behavior_contract.py 读取并注入"
需求字段 = {
"determinism": {"temperature": 0, "top_p": 1, "seed": 20251027},
"token_budget": {"per_call_max_tokens": 3000, "per_flow_max_tokens": 6000, "summary_threshold_tokens": 2200},
"output_mode": "markdown-structured",
"versioning": {"prompt_version": "tg-v1", "doc_commit": "local-dev"},
"pii_redaction": [
  {"field": "email", "mask": "***@***"},
  {"field": "phone", "mask": "***-****"},
  {"field": "id_number", "policy": "hash(sha256)"}
],
"fingerprints": {"prompt_fingerprint": "0000000000000000000000000000000000000000000000000000000000000000", "output_schema_id": "kobe/telegram/outputs@v1"}
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
SLO / 阈值 / 触发条件: "读取与验证 SHOULD < 10ms；PII redaction 命中率 100%。"# 标题: aiogram 基座重构确认
def section_aiogram_base(): ...  aiogram 基座章节
    """
    设计意图:
      - Telegram 入口 MUST 统一由 aiogram v3 Router 驱动並将 Update 串行穿过 CoreMessageSchema 与 AgentsBridge。
      - Webhook 生命周期 MUST 可回放并记录，以便 codegen targets 复现实装。
    设计原因:
      - polling 架构与多渠道扩展冲突，且无法满足 FastAPI webhook 与 codegen requirements。
      - 统一基座便于在 Config/prompts.{locale}.yaml 与 Contracts/* 自动填充依赖。
    接口锚点:
      - from aiogram import Router  TelegramBot/runtime.py: Router 声明及 handler 绑定
      - from TelegramBot.runtime import bootstrap_aiogram_service  TelegramBot/runtime.py: Bot Dispatcher Router 工厂
      - from TelegramBot.routes import register_routes  TelegramBot/routes.py: FastAPI + aiogram webhook 装配
    需求字段:
      - 必备配置: TELEGRAM_TOKEN WEBHOOK_SECRET TELEGRAM_PUBLIC_URL {REPO_ROOT}/.env
      - 依赖集合: aiogram>=3.14 fastapi uvicorn md2tgmd redis openai-agents opentelemetry-sdk(optional)
      - 可观察性字段: request_id chat_id convo_id latency_ms status_code error_hint
      - 存储挂载: RedisStorage 在 redis:// URL 存在时启用 否则使用 MemoryStorage 单实例
    二级嵌套:
      - RuntimeStack: Bot Dispatcher Router Middlewares
      - ObservabilityLayer: logging tracing metrics sinks/logs/telegram_service
    三级嵌套:
      - Middlewares: LoggingMiddleware ContextBridgeMiddleware RateLimitMiddleware(optional)
      - Hooks: pre_startup -> OpenaiAgents.memory_preload -> bootstrap_aiogram_service -> FastAPI route bind
    JSON Schema (MUST):
      {
        "$id": "kobe/telegrambot/aiogram_bootstrap.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["telegram_token", "webhook_secret", "repo_root"],
        "properties": {
          "telegram_token": {"type": "string", "minLength": 40},
          "webhook_secret": {"type": "string", "minLength": 16},
          "repo_root": {"type": "string", "pattern": "^D:/AI_Projects/"},
          "redis_url": {"type": "string", "pattern": "^redis://"},
          "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARN", "ERROR"]},
          "enable_tracing": {"type": "boolean", "default": false}
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - aiogram_bootstrap_status（locale=zh-CN, audience=ops）
        用途: 提醒运维确认启动状态与 Router。
        触发条件: bootstrap 成功或处于待确认状态。
        变量说明: {status}, {router_name}, {request_id}。
        示例文案: "请确认 aiogram 服务 ok，Router=main_router，request_id=1234"
        结构化定义:
          prompt_id=aiogram_bootstrap_status locale=zh-CN
            text="请确认 aiogram 服务 {status}，Router={router_name}，request_id={request_id}" audience=ops
      - aiogram_bootstrap_alert（locale=en-US, audience=devops）
        用途: 通知 devops 启动失败及步骤。
        触发条件: behavior_bootstrap 抛异常。
        变量说明: {step}, {request_id}。
        示例文案: "aiogram bootstrap failed at step set_webhook. request_id=abcd"
        结构化定义:
          prompt_id=aiogram_bootstrap_alert locale=en-US
            text="aiogram bootstrap failed at step {step}. request_id={request_id}." audience=devops
    Prompt 变量表:
      - 名称:status | 类型:string | 必填:是 | 默认:"ok" | 示例:"ok" | 说明: 启动状态。
      - 名称:router_name | 类型:string | 必填:是 | 默认:"main_router" | 示例:"main_router" | 说明: Router 标识。
      - 名称:request_id | 类型:string | 必填:是 | 默认:"" | 示例:"1234-..." | 说明: 请求 ID。
      - 名称:step | 类型:string | 必填:是 | 默认:"" | 示例:"set_webhook" | 说明: 失败步骤。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/aiogram_bootstrap.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^aiogram_"},
          "locale": {"type": "string", "enum": ["zh-CN", "en-US"]},
          "text": {"type": "string", "minLength": 10},
          "audience": {"type": "string", "enum": ["ops", "devops", "dev"]}
        }
      }
    Behavior Contract (MUST):
      - def behavior_bootstrap(): ...  描述
        """
        Steps:
          1. MUST load env via dotenv then verify TELEGRAM_TOKEN WEBHOOK_SECRET TELEGRAM_PUBLIC_URL。
          2. MUST call OpenaiAgents.memory_preload before Dispatcher creation。
          3. MUST instantiate Bot/Dispatcher/Router exactly once per process；reuse singletons via ContextBridge。
          4. MUST register logging + context middlewares before handlers。
          5. MUST raise RuntimeError if webhook registration fails twice。
        Outputs:
          - bootstrap_state: {"bot": Bot, "dispatcher": Dispatcher, "router": Router}
          - telemetry tags: request_id chat_id None at startup
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_register_webhook(url, secret): ...  注册 webhook
        """Parameters MUST match Telegram Bot API setWebhook；Failure MUST bubble for monitoring。"""
      - def call_preload_agents(repo_root): ...  预热 Agents
        """Returns bool success；False MUST stop startup。"""
    Config Contract (MUST):
      - target path: {REPO_ROOT}/Config/prompts.zh-CN.yaml includes aiogram_bootstrap_status prompt text
      - regen rule: 修改 Prompt Catalog 时 MUST regenerate Config/prompts.*
      - placeholders allowed: {REPO_ROOT} {DOC_ID} {DOC_COMMIT}
    Safety & Refusal Policy (MUST):
      - 若 TELEGRAM_TOKEN 缺失 MUST refuse to start with message "bootstrap_refused_missing_token"。
      - 若 webhook URL 非 https MUST refuse 并写 log error_hint="insecure_webhook"。
    i18n & Brand Voice (MUST):
      - zh-CN: 正式、简洁；en-US: concise incident tone。
      - All prompts MUST avoid emoji 与俚语。
    Output Contract (MUST):
      {
        "bootstrap_state": {
          "type": "object",
          "required": ["bot", "dispatcher", "router"],
          "properties": {
            "bot": {"type": "string", "pattern": "^aiogram\.Bot"},
            "dispatcher": {"type": "string", "pattern": "^aiogram\.Dispatcher"},
            "router": {"type": "string", "pattern": "^aiogram\.Router"}
          }
        }
      }
    Logging & Observability (MUST):
      - Logs MUST include request_id, stage (env_load|preload|router|webhook), duration_ms。
      - Metrics: telegram_bootstrap_latency histogram, telegram_bootstrap_errors counter。
      - Traces SHOULD annotate span name="aiogram.bootstrap"。
    Versioning & Traceability (MUST):
      - schema_version=1.1.0 doc_id=TelegramBotGCmessagePlan
      - generated-from 标记写入 Contracts/behavior_contract.py。
      - 每次改动 MUST bump change-set in changelog。
    Golden Sample(s) (MUST >=3):
      - Sample A: telegram_token=prod_46chars webhook_secret=sha256 repo_root=D:/AI_Projects/Kobe redis_url=redis://127.0.0.1:6379/3 log_level=INFO enable_tracing=false
      - Sample B: telegram_token=staging_44chars webhook_secret=uuid repo_root=D:/AI_Projects/Kobe log_level=DEBUG enable_tracing=true
      - Sample C: telegram_token=local_50chars webhook_secret=localsecret repo_root=D:/AI_Projects/Kobe redis_url=redis://cache:6379/0 log_level=WARN
    Counter Sample(s) (MUST >=2):
      - Counter A: missing webhook_secret -> MUST raise ValueError and refuse startup。
      - Counter B: repo_root=E:/tmp -> MUST fail alignment with REPO_ROOT。
    决策表 / 状态机 / 顺序化约束:
      | Condition | Action | Notes |
      | missing redis_url | use MemoryStorage | reject multi instance deployment |
      | OpenaiAgents preload failure | abort startup | raise RuntimeError 并记录 telemetry_id |
      | Bot.set_webhook return False twice | stop | require manual fix |
    如何使用:
      - app.py 调用 bootstrap_aiogram_service -> register_routes -> uvicorn run。
      - Ops 可调用 call_register_webhook 以 out-of-band 恢复。
    agent如何读取:
      - AgentsBridge 通过 ContextBridgeMiddleware 注入 message context；bootstrap_state.router 提供 decorators。
    边界与回退:
      - 初始化任一步骤失败 MUST 阻塞 FastAPI 启动。
      - redis 不可达 MUST 切 MemoryStorage 并标记 degrade_mode=true。
    SLO / 阈值 / 触发条件:
      - bootstrap 完成时间 SHOULD < 3s P95。
      - Webhook 注册成功率 MUST >= 99%。
      - 连续 3 次失败 MUST 触发 PagerDuty。
    """
# 标题: 资产拆解与迁移
def section_asset_transition(): ...  资产拆解章节
    """
    设计意图:
      - MUST 记录 legacy 目录与保留模块，保证 codegen 与 docs 同步。
      - SHOULD 提供自动化 checklist 以便脚本阻止遗留代码回流。
    设计原因:
      - polling 旧版与 webhook 重构冲突，必须清空旧实现。
      - 资产台账是跨文档 family coherence 的基础。
    接口锚点:
      - WorkPlan/02TelegramBotGCmessagePlan.md 本文为 SSOT
      - scripts/ci/fs_guard.py (计划) 调用 assert_absent()
      - WorkPlan/01DatabaseIndexAgentPlan.md: LegacyNote
    需求字段:
      - removed_directories: Kobe/TelegramBot/legacy Kobe/config
      - preserved_modules: Kobe/OpenaiAgents Kobe/KnowledgeBase Kobe/SharedUtility
      - migration_actions: mkdir TelegramBot, generate env template, rebuild docker
      - audit_trail: doc_id + git commit
    二级嵌套:
      - RemovalChecklist: existence_check backup_confirm delete_confirm
      - PreservationChecklist: module_path git_status expected_owner
    三级嵌套:
      - existence_check: fs path presence check -> fail fast
      - backup_confirm: optional tarball -> retention 7 days
      - delete_confirm: git rm + commit referencing本章节
    JSON Schema (MUST):
      {
        "$id": "kobe/workplan/asset_transition.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["removed_directories", "preserved_modules", "migration_actions"],
        "properties": {
          "removed_directories": {
            "type": "array",
            "items": {"type": "string", "pattern": "^Kobe/(TelegramBot|config)"},
            "minItems": 1
          },
          "preserved_modules": {
            "type": "array",
            "items": {"type": "string", "pattern": "^Kobe/(OpenaiAgents|KnowledgeBase|SharedUtility)"},
            "minItems": 1
          },
          "migration_actions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3
          },
          "audit_trail": {"type": "string", "pattern": "^WorkPlan/"}
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - asset_guard_violation（locale=zh-CN, audience=devops）
        用途: 提示 CI 发现 legacy 目录。
        触发条件: behavior_asset_guard 检测 removed_directories 仍存在。
        变量说明: {path}。
        示例文案: "发现遗留目录 Kobe/TelegramBot/legacy，阻止合并"
        结构化定义:
          prompt_id=asset_guard_violation locale=zh-CN text="发现遗留目录 {path}，阻止合并" audience=devops
      - asset_cleanup_summary（locale=en-US, audience=maintainer）
        用途: 记录清理动作，便于审计。
        触发条件: call_record_audit 完成。
        变量说明: {dir}, {timestamp}, {commit}.
        示例文案: "Removed Kobe/config at 2025-10-27 10:00 commit abcd1234"
        结构化定义:
          prompt_id=asset_cleanup_summary locale=en-US text="Removed {dir} at {timestamp} commit {commit}" audience=maintainer
    Prompt 变量表:
      - 名称:path | 类型:string | 必填:是 | 默认:"" | 示例:"Kobe/TelegramBot/legacy" | 说明: 检测到的遗留目录。
      - 名称:dir | 类型:string | 必填:是 | 默认:"" | 示例:"Kobe/config" | 说明: 已清理目录。
      - 名称:timestamp | 类型:string | 必填:是 | 默认:"" | 示例:"2025-10-27T10:00:00+08:00" | 说明: 清理时间。
      - 名称:commit | 类型:string | 必填:是 | 默认:"" | 示例:"abcd1234" | 说明: 关联提交。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/asset_transition.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^asset_"},
          "locale": {"type": "string", "enum": ["zh-CN", "en-US"]},
          "text": {"type": "string", "minLength": 8},
          "audience": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_asset_guard(): ...  检查流程
        """
        Steps:
          - MUST scan removed_directories before build。
          - MUST fail pipeline if任何目录存在。
          - SHOULD log preserved_modules git status并提示 owner。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_assert_absent(path): ...  断言目录不存在
        """返回 bool；False MUST raise LegacyAssetError。"""
      - def call_record_audit(entry): ...  记录审计
        """entry 包含 path action timestamp。"""
    Config Contract (MUST):
      - Config/prompts.zh-CN.yaml MUST 包含 asset_guard_violation
      - Config/prompts.en-US.yaml MUST 包含 asset_cleanup_summary
      - Contracts/behavior_contract.py MUST 暴露 behavior_asset_guard 钩子
    Safety & Refusal Policy (MUST):
      - 若发现 legacy 目录 MUST 拒绝部署并提示清理步骤。
      - 若 preserved_modules git status 脏 MUST 拒绝 release。
    i18n & Brand Voice (MUST):
      - 中文提醒直接、具备执行指令。
      - 英文提醒面向维护者，强调行动项。
    Output Contract (MUST):
      {
        "asset_report": {
          "type": "object",
          "required": ["removed", "preserved", "status"],
          "properties": {
            "removed": {"type": "array", "items": {"type": "string"}},
            "preserved": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string", "enum": ["clean", "violation"]}
          }
        }
      }
    Logging & Observability (MUST):
      - 指标 asset_violation_total, asset_scan_latency_ms。
      - 日志字段: path action request_id doc_id。
    Versioning & Traceability (MUST):
      - schema_version=1.1.0 -> asset contract revision a1。
      - audit entries MUST embed doc_id。
    Golden Sample(s) (MUST >=3):
      - Sample A: removed=["Kobe/TelegramBot/legacy"] preserved=["Kobe/OpenaiAgents"] status="clean"
      - Sample B: removed=["Kobe/config"] preserved=["Kobe/KnowledgeBase","Kobe/SharedUtility"] status="clean"
      - Sample C: removed=["Kobe/TelegramBot/legacy","Kobe/config"] status="violation"
    Counter Sample(s) (MUST >=2):
      - Counter A: removed=[] => MUST fail schema
      - Counter B: preserved 包含 "Kobe/Deprecated" => MUST fail pattern
    决策表 / 状态机 / 顺序化约束:
      | Step | Condition | Action |
      | detect legacy dir | path exists | stop deployment raise LegacyAssetError |
      | verify preserved module | git status dirty | block release 直到 clean |
      | audit record | action success | append to asset_report |
    如何使用:
      - CI 调用 behavior_asset_guard 并根据输出决定 pass/fail。
      - Ops 更新文档后同步更新 audit_trail。
    agent如何读取:
      - Agents 无需直接消费，但 Channel adapters MUST 尊重最新目录列表。
    边界与回退:
      - 回滚 legacy 仅可通过 git 历史且需记录 reason。
      - 临时目录命名若命中 pattern MUST 标记并删除。
    SLO / 阈值 / 触发条件:
      - asset 扫描耗时 SHOULD < 1s。
      - 发现 violation MUST 在 5m 内通知负责人。
      - 资产台账更新延迟 MUST < 1 个工作日。
    """
# 标题: Schema 统一与 Adapter 策略
def section_core_strategy(): ...  Schema 统一章节
    """
    设计意图:
      - MUST 以 CoreEnvelope 作为渠道与 Agents 间唯一语义边界。
      - SHOULD 为 Prompt/Behavior/Output 合同提供统一来源，供 codegen 使用。
    设计原因:
      - 多渠道接入需要稳定字段，防止 prompt 与 adapter 漂移。
      - 统一 Schema 能让日志、SLO 跨渠道比较。
    接口锚点:
      - from core.schema import CoreMessageSchema  {REPO_ROOT}/core/schema.py
      - from core.adapters import build_core_schema  {REPO_ROOT}/core/adapters.py
      - from TelegramBot.adapters.telegram import telegram_update_to_core  {REPO_ROOT}/TelegramBot/adapters/telegram.py
    需求字段:
      - metadata: chat_id convo_id channel language timestamp_iso
      - payload: user_message context_quotes attachments
      - ext_flags: intent_hint reply_to_bot kb_scope safety_level
      - telemetry: request_id trace_id latency_ms tokens_prompt tokens_completion
    二级嵌套:
      - CoreEnvelope: metadata payload ext_flags telemetry version
      - AdapterContract: inbound_adapter outbound_adapter validation_hooks
    三级嵌套:
      - metadata: chat_id convo_id channel language timestamp_iso
      - payload.context_quotes: speaker role timestamp excerpt
      - telemetry: counters spans error_hint
    JSON Schema (MUST):
      {
        "$id": "kobe/core/core_envelope.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["metadata", "payload", "ext_flags", "version"],
        "properties": {
          "metadata": {
            "type": "object",
            "required": ["chat_id", "convo_id", "channel", "language"],
            "properties": {
              "chat_id": {"type": "string"},
              "convo_id": {"type": "string"},
              "channel": {"type": "string", "enum": ["telegram", "web", "whatsapp"]},
              "language": {"type": "string", "pattern": "^[a-z]{2}(-[A-Z]{2})?$"},
              "timestamp_iso": {"type": "string", "format": "date-time"}
            },
            "additionalProperties": false
          },
          "payload": {
            "type": "object",
            "required": ["user_message"],
            "properties": {
              "user_message": {"type": "string", "minLength": 1},
              "context_quotes": {"type": "array", "items": {"type": "string"}},
              "attachments": {"type": "array", "items": {"type": "object"}}
            }
          },
          "ext_flags": {
            "type": "object",
            "properties": {
              "intent_hint": {"type": "string"},
              "reply_to_bot": {"type": "boolean"},
              "kb_scope": {"type": "array", "items": {"type": "string"}},
              "safety_level": {"type": "string", "enum": ["normal", "sensitive", "restricted"]}
            }
          },
          "telemetry": {
            "type": "object",
            "properties": {
              "request_id": {"type": "string"},
              "trace_id": {"type": "string"},
              "latency_ms": {"type": "number", "minimum": 0}
            }
          },
          "version": {"type": "string", "pattern": "^v?\d+\.\d+\.\d+$"}
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - core_schema_violation（locale=zh-CN, audience=dev）
        用途: 通知开发者 CoreEnvelope 校验失败。
        触发条件: behavior_core_envelope 捕获 SchemaValidationError。
        变量说明: {error}。
        示例文案: "CoreEnvelope 校验失败: 缺少 chat_id"
        结构化定义:
          prompt_id=core_schema_violation locale=zh-CN text="CoreEnvelope 校验失败: {error}" audience=dev
      - core_schema_alert（locale=en-US, audience=ops）
        用途: 告警 channel 字段与 schema 不符。
        触发条件: call_emit_schema_alert 被调用。
        变量说明: {channel}, {field}。
        示例文案: "Schema mismatch on telegram: ext_flags.kb_scope"
        结构化定义:
          prompt_id=core_schema_alert locale=en-US text="Schema mismatch on {channel}: {field}" audience=ops
    Prompt 变量表:
      - 名称:error | 类型:string | 必填:是 | 默认:"" | 示例:"missing chat_id" | 说明: 校验失败原因。
      - 名称:channel | 类型:string | 必填:是 | 默认:"telegram" | 示例:"telegram" | 说明: 出错渠道。
      - 名称:field | 类型:string | 必填:是 | 默认:"" | 示例:"ext_flags.kb_scope" | 说明: 出错字段。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/core_envelope.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^core_"},
          "locale": {"type": "string"},
          "text": {"type": "string"},
          "audience": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_core_envelope(): ...  Core 构建
        """
        MUST steps:
          - Validate inbound payload against core_envelope.schema.json。
          - Normalize language -> default zh-CN when missing。
          - Merge telemetry.request_id from RequestIDMiddleware。
          - Provide to_agent_request() and to_logging_dict() methods。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_build_core_schema(update, channel): ...  构建 envelope
        """Returns CoreEnvelope dict；on failure raise SchemaValidationError。"""
      - def call_emit_schema_alert(error): ...  告警
        """Uses prompt core_schema_alert 推送到 DevOps。"""
    Config Contract (MUST):
      - Contracts/behavior_contract.py MUST include behavior_core_envelope。
      - Config/prompts.*.yaml MUST 包含 core_schema_* prompts。
      - Contracts/output.schema.json MUST 引用 core_envelope schema。
    Safety & Refusal Policy (MUST):
      - Schema invalid -> MUST refuse to forward to AgentsBridge。
      - Unknown channel -> MUST refuse with code "channel_not_supported"。
    i18n & Brand Voice (MUST):
      - zh-CN 用技术语气，英文强调行动。
    Output Contract (MUST):
      {
        "core_envelope": {
          "type": "object",
          "$ref": "kobe/core/core_envelope.schema.json"
        }
      }
    Logging & Observability (MUST):
      - Log keys: channel, convo_id, schema_version, validation_ms。
      - Metrics: core_envelope_validation_latency, core_envelope_failure_total。
    Versioning & Traceability (MUST):
      - version tag v1.1.0 -> update changelog entry。
      - Each schema change MUST bump $id suffix。
    Golden Sample(s) (MUST >=3):
      - Sample A: telegram zh-CN message "你好" reply_to_bot False version v1.0.0
      - Sample B: web en-US message "Hello" context_quotes["Q1"] intent_hint "faq"
      - Sample C: telegram ja-JP attachments placeholder safety_level sensitive
    Counter Sample(s) (MUST >=2):
      - Counter A: missing metadata.chat_id -> fail schema
      - Counter B: version="1.0" -> fail semver
    决策表 / 状态机 / 顺序化约束:
      | Phase | Condition | Action |
      | inbound parsing | schema ok | continue |
      | inbound parsing | schema fail | reject update 400 |
      | outbound render | latency_ms > slo | mark degraded |
    如何使用:
      - 渠道 adapter MUST 调用 call_build_core_schema。
      - AgentsBridge 仅消费 core_envelope 产物。
    agent如何读取:
      - AgentsBridge uses core_envelope.to_agent_request() for Responses API。
    边界与回退:
      - version mismatch -> run compatibility shim + log warning。
      - attachments unsupported channel -> return 422。
    SLO / 阈值 / 触发条件:
      - Validation SHOULD < 5ms P95。
      - Failure rate MUST < 0.5% daily。
      - Failure > 1% triggers incident。
    """
# 标题: CoreMessageSchema 字段定义
def section_core_schema_fields(): ...  字段章节
    """
    设计意图:
      - MUST 冻结 CoreMessageSchema 字段语义以自动生成 pydantic 模型与输出 schema。
      - SHOULD 定义 Attachment 结构与 ext_flags 默认，支撑多模态。
    设计原因:
      - 多渠道字段易漂移，需要集中定义。
      - Pydantic v2 validators 依赖此章节派生。
    接口锚点:
      - class CoreMessageSchema  {REPO_ROOT}/core/schema.py
      - class Attachment  {REPO_ROOT}/core/schema.py
      - class ExtFlags  {REPO_ROOT}/core/schema.py
    需求字段:
      - base_metadata: chat_id convo_id channel language thread_id message_ts
      - payload: user_message context_quotes attachments system_tags
      - attachments: kind source summary mime_size_bytes checksum_sha256(optional)
      - ext_flags: reply_to_bot intent_hint kb_scope safety_level
    二级嵌套:
      - Attachment.kind: text image file audio voice
      - Attachment.source: channel specific file_id or URL
    三级嵌套:
      - context_quotes.item: speaker role timestamp excerpt
      - kb_scope.item: knowledge_base slug
      - safety_level: enum normal sensitive restricted
    JSON Schema (MUST):
      {
        "$id": "kobe/core/core_message.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["chat_id", "convo_id", "channel", "language", "user_message", "version"],
        "properties": {
          "chat_id": {"type": "string"},
          "convo_id": {"type": "string"},
          "channel": {"type": "string"},
          "language": {"type": "string", "pattern": "^[a-z]{2}(-[A-Z]{2})?$"},
          "thread_id": {"type": "string"},
          "message_ts": {"type": "string", "format": "date-time"},
          "user_message": {"type": "string", "minLength": 1},
          "context_quotes": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["speaker", "excerpt"],
              "properties": {
                "speaker": {"type": "string"},
                "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                "timestamp": {"type": "string", "format": "date-time"},
                "excerpt": {"type": "string"}
              },
              "additionalProperties": false
            }
          },
          "attachments": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["kind", "source"],
              "properties": {
                "kind": {"type": "string", "enum": ["text", "image", "file", "audio", "voice"]},
                "source": {"type": "string"},
                "summary": {"type": "string"},
                "mime_size_bytes": {"type": "integer", "minimum": 0},
                "checksum_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}
              },
              "additionalProperties": false
            }
          },
          "system_tags": {"type": "array", "items": {"type": "string"}},
          "ext_flags": {
            "type": "object",
            "properties": {
              "reply_to_bot": {"type": "boolean"},
              "intent_hint": {"type": "string"},
              "kb_scope": {"type": "array", "items": {"type": "string"}},
              "safety_level": {"type": "string", "enum": ["normal", "sensitive", "restricted"]}
            },
            "additionalProperties": false
          },
          "version": {"type": "string", "const": "v1.0.0"}
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - core_fields_gap（locale=zh-CN, audience=dev）
        用途: 通知开发者 CoreMessageSchema 缺字段或顺序错误。
        触发条件: behavior_core_message_schema 检测字段缺失。
        变量说明: {field}。
        示例文案: "CoreMessageSchema 缺少字段 context_quotes[0].excerpt"
        结构化定义:
          prompt_id=core_fields_gap locale=zh-CN text="CoreMessageSchema 缺少字段 {field}" audience=dev
      - core_fields_attachment（locale=en-US, audience=ops）
        用途: 报告附件校验失败信息以便运维定位。
        触发条件: call_validate_core_message 中 attachments.kind 不合法。
        变量说明: {kind}.
        示例文案: "Attachment validation failed for video"
        结构化定义:
          prompt_id=core_fields_attachment locale=en-US text="Attachment validation failed for {kind}" audience=ops
    Prompt 变量表:
      - 名称:field | 类型:string | 必填:是 | 示例:"context_quotes[0].excerpt" | 说明: 缺失字段路径。
      - 名称:kind | 类型:string | 必填:是 | 示例:"video" | 说明: 附件类型。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/core_message_fields.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^core_fields_"},
          "locale": {"type": "string"},
          "text": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_core_message_schema(): ...  字段合约
        """
        MUST enforce max context_quotes=5 by trimming oldest。
        MUST cap attachments to 3 items else raise PayloadTooLarge。
        SHOULD default kb_scope to ["global"] when empty。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_validate_core_message(payload): ...  校验
        """返回 validated data；失败 raise SchemaValidationError。"""
      - def call_normalize_context_quotes(quotes): ...  归一化
        """确保 speaker role timestamp 统一格式。"""
    Config Contract (MUST):
      - Contracts/output.schema.json MUST include $ref core_message.schema。
      - Contracts/behavior_contract.py MUST expose behavior_core_message_schema。
    Safety & Refusal Policy (MUST):
      - 空 user_message MUST 拒绝。
      - attachments.kind 未列举 MUST 拒绝。
    i18n & Brand Voice (MUST):
      - 错误提示遵循 CLI 式，无 emoji。
    Output Contract (MUST):
      {
        "core_message": {
          "$ref": "kobe/core/core_message.schema.json"
        }
      }
    Logging & Observability (MUST):
      - 记录 context_quote_count attachment_count safety_level。
      - 指标 core_message_trim_total, core_message_attachment_reject_total。
    Versioning & Traceability (MUST):
      - version 固定 v1.0.0；若升级 MUST 记录迁移指南。
      - Trace id 映射到 AgentsBridge tokens。
    Golden Sample(s) (MUST >=3):
      - Sample A: group chat, context_quotes 2, attachments []
      - Sample B: private chat, attachments image + summary
      - Sample C: voice attachment with checksum_sha256 provided
    Counter Sample(s) (MUST >=2):
      - Counter A: user_message "" -> reject
      - Counter B: attachments.kind "video" -> reject
    决策表 / 状态机 / 顺序化约束:
      | Field | Condition | Action |
      | context_quotes | count > 5 | drop oldest |
      | attachments | count > 3 | raise PayloadTooLarge |
      | safety_level | missing | default normal |
    如何使用:
      - 渠道 handler 构造 CoreMessageSchema(**validated_data)。
    agent如何读取:
      - AgentsBridge uses to_agent_request() output。
    边界与回退:
      - ext_flags 缺失 -> apply defaults。
      - version upgrade -> provide migration doc。
    SLO / 阈值 / 触发条件:
      - 校验失败率 SHOULD < 0.2%。
      - context trim MUST 完成 < 2ms。
      - attachments 缺 checksum > 5% -> trigger audit。
    """
# 标题: Telegram Adapter 与 Agents Adapter
def section_telegram_agents_adapter(): ...  Adapter 章节
    """
    设计意图:
      - MUST 将 Telegram 入站 update 统一映射到 CoreEnvelope 并输出 Agents 响应。
      - SHOULD 记录 streaming 编辑策略与降级行为，供行为合约消费。
    设计原因:
      - 群聊与私聊字段差异大，需要明确定义转换。
      - Responses API streaming 需要精准的缓冲策略。
    接口锚点:
      - from TelegramBot.adapters.telegram import telegram_update_to_core  {REPO_ROOT}/TelegramBot/adapters/telegram.py
      - from core.adapters import core_to_agent_request  {REPO_ROOT}/core/adapters.py
      - from TelegramBot.adapters.response import core_to_telegram_response  {REPO_ROOT}/TelegramBot/adapters/response.py
    需求字段:
      - inbound: update.message.message_id chat.id text reply_to_message language_code
      - outbound: chat_id reply_to_message_id parse_mode MarkdownV2 disable_web_page_preview True streaming_buffer
      - agent_bridge: prompt convo_id language intent_hint tokens_budget
    二级嵌套:
      - InboundFlow: pre_validation -> normalization -> CoreMessageSchema build -> telemetry logging
      - OutboundFlow: placeholder -> streaming edit -> finalization -> fallback
    三级嵌套:
      - pre_validation: ensure text len>0 ensure user not blocked ensure webhook signature pass
      - normalization: detect group vs private compute convo_id derive language fallback
      - streaming: chunk buffer, edit interval, fallback path
    JSON Schema (MUST):
      {
        "$id": "kobe/telegrambot/adapter_contract.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["inbound", "agent_bridge", "outbound"],
        "properties": {
          "inbound": {
            "type": "object",
            "required": ["message_id", "chat_id", "text"],
            "properties": {
              "message_id": {"type": "integer", "minimum": 1},
              "chat_id": {"type": "integer"},
              "thread_id": {"type": "integer"},
              "text": {"type": "string", "minLength": 1},
              "language_code": {"type": "string"},
              "reply_to_bot": {"type": "boolean"}
            }
          },
          "agent_bridge": {
            "type": "object",
            "required": ["prompt", "convo_id", "language"],
            "properties": {
              "prompt": {"type": "string"},
              "convo_id": {"type": "string"},
              "language": {"type": "string"},
              "intent_hint": {"type": "string"}
            }
          },
          "outbound": {
            "type": "object",
            "required": ["chat_id", "parse_mode"],
            "properties": {
              "chat_id": {"type": "integer"},
              "reply_to_message_id": {"type": "integer"},
              "parse_mode": {"type": "string", "const": "MarkdownV2"},
              "fallback_text": {"type": "string"}
            }
          }
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - telegram_prompt_missing（locale=zh-CN, audience=user）
        用途: 提示用户发送文本。
        触发条件: inbound 没有 text。
        变量说明: 无。
        示例文案: "请发送文本内容"
        结构化定义:
          prompt_id=telegram_prompt_missing locale=zh-CN text="请发送文本内容" audience=user
      - telegram_streaming_error（locale=en-US, audience=ops）
        用途: 告知运维 streaming 出错。
        触发条件: streaming pipeline 抛异常。
        变量说明: {request_id}。
        示例文案: "Streaming failed request 1234"
        结构化定义:
          prompt_id=telegram_streaming_error locale=en-US text="Streaming failed request {request_id}" audience=ops
    Prompt 变量表:
      - 名称:request_id | 类型:string | 必填:是 | 默认:"" | 示例:"abcd" | 说明: 异常请求 ID。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/telegram_adapter.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^telegram_"},
          "locale": {"type": "string"},
          "text": {"type": "string"},
          "audience": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_telegram_inbound(): ...  入站
        """
        MUST reject empty text with prompt telegram_prompt_missing。
        MUST compute convo_id = chat_id if private else chat_id:thread_id。
        SHOULD set ext_flags.reply_to_bot True when reply_to bot message。
        """
      - def behavior_telegram_outbound(): ...  出站
        """
        MUST send placeholder message strings.message_think。
        MUST edit message every 1.5s or 500 chars。
        MUST send fallback prompt telegram_streaming_error on exception。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_md_escape(text): ...  Markdown 转义
        """Uses md2tgmd.escape ensure Telegram safe。"""
      - def call_send_placeholder(bot, chat_id): ...  占位
        """Returns message_id for streaming edits。"""
    Config Contract (MUST):
      - Config/prompts.zh-CN.yaml includes telegram_prompt_missing
      - Config/prompts.en-US.yaml includes telegram_streaming_error
      - Contracts/toolcalls.py includes call_md_escape call_send_placeholder
    Safety & Refusal Policy (MUST):
      - Messages exceeding 4096 chars MUST be refused with trimmed summary。
      - Photos/files unsupported in V1 MUST trigger polite refusal。
    i18n & Brand Voice (MUST):
      - User facing zh-CN prompts: 简洁、带敬语。
      - System prompts en-US: incident concise。
    Output Contract (MUST):
      {
        "telegram_adapter_result": {
          "type": "object",
          "required": ["core_envelope", "response_status"],
          "properties": {
            "core_envelope": {"$ref": "kobe/core/core_envelope.schema.json"},
            "response_status": {"type": "string", "enum": ["ok", "fallback", "refused"]}
          }
        }
      }
    Logging & Observability (MUST):
      - Log per chunk: chunk_index chunk_size edit_latency request_id。
      - Metrics: telegram_inbound_total, telegram_streaming_failures, telegram_placeholder_latency。
    Versioning & Traceability (MUST):
      - adapter contract version v1.1.0 documented。
      - Tools referencing call_md_escape MUST note doc_id。
    Golden Sample(s) (MUST >=3):
      - Sample A: group thread message -> convo_id "-100:1" -> streaming ok
      - Sample B: private chat -> reply_to bot -> ext_flags.reply_to_bot True
      - Sample C: command message leading slash -> normalized user_message
    Counter Sample(s) (MUST >=2):
      - Counter A: text "" -> prompt telegram_prompt_missing
      - Counter B: parse_mode != MarkdownV2 -> fail schema
    决策表 / 状态机 / 顺序化约束:
      | Step | Condition | Action |
      | pre_validation | text missing | send prompt + exit |
      | normalization | reply_to_bot True | hydrate context_quotes |
      | streaming | edit failure | retry once then fallback |
    如何使用:
      - aiogram handler -> behavior_telegram_inbound -> AgentsBridge -> behavior_telegram_outbound。
    agent如何读取:
      - AgentsBridge consumes AgentRequest produced via core_to_agent_request。
    边界与回退:
      - Telegram API 429 -> exponential backoff + log degraded。
      - OpenAI error -> fallback prompt + telemetry.
    SLO / 阈值 / 触发条件:
      - 入站解析 latency SHOULD < 20ms。
      - streaming 成功率 MUST >= 98%。
      - fallback ratio > 2% -> incident。
    """
# 标题: FastAPI + aiogram Webhook 服务
def section_fastapi_webhook(): ...  Webhook 章节
    """
    设计意图:
      - MUST 用 FastAPI 统一所有 webhook，封装 aiogram dispatcher。
      - SHOULD 提供可机检的构建流程、签名校验、监控钩子。
    设计原因:
      - Webhook 模式需要精确的生命周期与安全策略。
      - FastAPI 提供依赖注入，便于扩展多渠道。
    接口锚点:
      - from infra.fastapi_app import create_app  {REPO_ROOT}/infra/fastapi_app.py
      - from TelegramBot.routes import register_routes  {REPO_ROOT}/TelegramBot/routes.py
      - from TelegramBot.runtime import bootstrap_aiogram_service  {REPO_ROOT}/TelegramBot/runtime.py
    需求字段:
      - routes: /healthz /telegram/webhook /telegram/setup_webhook /metrics
      - middleware: RequestIDMiddleware LoggingMiddleware SignatureVerifyMiddleware
      - deps: aiogram Bot Dispatcher Router AgentsBridge logger redis_pool
      - secrets: TELEGRAM_WEBHOOK_SECRET TELEGRAM_PUBLIC_URL OPENAI_API_KEY
    二级嵌套:
      - StartupFlow: load_env -> memory_preload -> bootstrap_aiogram_service -> create_app -> register_routes -> uvicorn startup
      - RequestFlow: middleware -> signature check -> dispatcher.feed_update
    三级嵌套:
      - SignatureVerifyMiddleware: compare header X-Telegram-Bot-Api-Secret-Token -> mismatch => 403
      - MetricsHook: expose Prometheus counters telegram_updates_total webhook_latency_ms
    JSON Schema (MUST):
      {
        "$id": "kobe/infra/webhook_service.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["webhook_path", "secret_header", "dispatcher_ref"],
        "properties": {
          "webhook_path": {"type": "string", "const": "/telegram/webhook"},
          "setup_path": {"type": "string", "const": "/telegram/setup_webhook"},
          "secret_header": {"type": "string", "const": "X-Telegram-Bot-Api-Secret-Token"},
          "dispatcher_ref": {"type": "string", "const": "TelegramBot.runtime.dispatcher"},
          "health_path": {"type": "string", "const": "/healthz"},
          "metrics_path": {"type": "string", "const": "/metrics"}
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - webhook_signature_fail（locale=zh-CN, audience=ops）
        用途: 提醒运维有签名不匹配。
        触发条件: middleware 校验 header 失败。
        变量说明: {request_id}。
        示例文案: "Webhook 签名验证失败 1234"
        结构化定义:
          prompt_id=webhook_signature_fail locale=zh-CN text="Webhook 签名验证失败 {request_id}" audience=ops
      - webhook_register_retry（locale=en-US, audience=devops）
        用途: 记录 setWebhook 重试次数。
        触发条件: call_register_webhook 第一次失败后进入重试。
        变量说明: {retry}。
        示例文案: "Webhook registration retry step 2"
        结构化定义:
          prompt_id=webhook_register_retry locale=en-US text="Webhook registration retry step {retry}" audience=devops
    Prompt 变量表:
      - 名称:request_id | 类型:string | 必填:是 | 示例:"abcd" | 说明: 请求 ID。
      - 名称:retry | 类型:integer | 必填:是 | 默认:1 | 示例:2 | 说明: 当前重试次数。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/webhook_service.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^webhook_"},
          "locale": {"type": "string"},
          "text": {"type": "string"},
          "audience": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_webhook_startup(): ...  启动
        """
        MUST call bootstrap_aiogram_service before FastAPI app creation。
        MUST register routes only after dispatcher ready。
        MUST abort uvicorn if webhook registration fails twice。
        """
      - def behavior_webhook_request(): ...  请求
        """
        MUST verify signature header equals TELEGRAM_WEBHOOK_SECRET。
        MUST attach request_id to dispatcher context。
        SHOULD emit telemetry per request。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_verify_signature(headers, secret): ...  校验
        """返回 bool；False -> raise HTTPException 403。"""
      - def call_register_webhook(bot, url, secret): ...  注册
        """调用 Bot.set_webhook；失败 -> RuntimeError。"""
    Config Contract (MUST):
      - Contracts/toolcalls.py MUST expose call_verify_signature。
      - Config/prompts.*.yaml MUST 包含 webhook_*。
      - Contracts/behavior_contract.py MUST include behavior_webhook_startup/request。
    Safety & Refusal Policy (MUST):
      - 非 https webhook URL MUST 拒绝。
      - 缺少签名 header MUST 返回 403。
    i18n & Brand Voice (MUST):
      - zh-CN 提示技术化，en-US 强调 incident。
    Output Contract (MUST):
      {
        "webhook_response": {
          "type": "object",
          "required": ["status", "request_id"],
          "properties": {
            "status": {"type": "string", "enum": ["accepted", "rejected"]},
            "request_id": {"type": "string"}
          }
        }
      }
    Logging & Observability (MUST):
      - Logs: request_id route latency_ms signature_status。
      - Metrics: webhook_rtt_ms histogram, webhook_signature_failures counter。
      - Traces: span name "telegram.webhook"。
    Versioning & Traceability (MUST):
      - doc schema_version=1.1.0 -> update register_routes docstring。
      - Each route change MUST reference doc_id in git commit。
    Golden Sample(s) (MUST >=3):
      - Sample A: secret header match -> status accepted。
      - Sample B: signature mismatch -> status rejected 403。
      - Sample C: webhook registration success after retry。
    Counter Sample(s) (MUST >=2):
      - Counter A: webhook_path=/bot -> schema fail。
      - Counter B: missing secret header -> HTTP 403。
    决策表 / 状态机 / 顺序化约束:
      | Phase | Condition | Action |
      | startup | bootstrap ok | register routes |
      | startup | webhook register fail twice | abort |
      | request | signature mismatch | return 403 |
    如何使用:
      - create_app(factory) -> bootstrap -> register_routes -> uvicorn.run。
      - /telegram/setup_webhook endpoint call call_register_webhook。
    agent如何读取:
      - AgentsBridge 通过 FastAPI lifespan 预热上下文。
    边界与回退:
      - set_webhook 409 -> delete webhook -> retry once。
      - middleware error -> log with request_id。
    SLO / 阈值 / 触发条件:
      - Webhook RTT SHOULD < 500ms P95。
      - signature mismatch MUST < 0.1%。
      - Dispatcher.feed_update error rate > 1% -> degrade。
    """
# 标题: AgentsBridge 现状与约束
def section_agents_bridge(): ...  AgentsBridge 章节
    """
    设计意图:
      - MUST 映射 CoreEnvelope -> AgentRequest 并记录 streaming 行为。
      - SHOULD 定义 Responses API 与 ComposeRenderer 降级策略。
    设计原因:
      - 双路径并存，需统一文档与实现。
      - tokens 使用量与上下文压缩需可追踪。
    接口锚点:
      - from OpenaiAgents.UnifiedCS.bridge import AgentsBridge  {REPO_ROOT}/OpenaiAgents/UnifiedCS/bridge.py
      - from OpenaiAgents.UnifiedCS.types import AgentRequest  {REPO_ROOT}/OpenaiAgents/UnifiedCS/types.py
      - from OpenaiAgents.UnifiedCS.gateway import AgentsGateway  {REPO_ROOT}/OpenaiAgents/UnifiedCS/gateway.py
    需求字段:
      - AgentRequest: prompt convo_id language intent_hint system_tags attachments
      - AgentsBridge.state: conversation tokens_usage last_error_ts snapshot_revision
      - Gateway modes: responses_api compose_renderer offline_cache
    二级嵌套:
      - Responses API path: build request -> dispatch_stream -> map chunk -> yield
      - Compose path: detect missing API key -> load KB -> render -> yield
    三级嵌套:
      - conversation store: key=convo_id value=deque(maxlen=50)
      - tokens_usage: key=convo_id value=int resets on inactivity 30m
    JSON Schema (MUST):
      {
        "$id": "kobe/openaiagents/agent_request.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["prompt", "convo_id", "language"],
        "properties": {
          "prompt": {"type": "string", "minLength": 1},
          "convo_id": {"type": "string"},
          "language": {"type": "string", "pattern": "^[a-z]{2}(-[A-Z]{2})?$"},
          "intent_hint": {"type": "string"},
          "system_tags": {"type": "array", "items": {"type": "string"}},
          "attachments": {"type": "array", "items": {"type": "string"}}
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - agent_bridge_offline（locale=zh-CN, audience=ops）
        用途: 提醒运维 AgentsBridge 进入 compose_renderer 离线模式。
        触发条件: OPENAI_API_KEY 缺失或 API 错误后降级。
        变量说明: 无。
        示例文案: "AgentsBridge 离线模式，使用 KB 渲染"
        结构化定义:
          prompt_id=agent_bridge_offline locale=zh-CN text="AgentsBridge 离线模式，使用 KB 渲染" audience=ops
      - agent_bridge_retry（locale=en-US, audience=devops）
        用途: 记录 Responses API 重试次数。
        触发条件: Gateway retry.
        变量说明: {count}, {request_id}。
        示例文案: "AgentsBridge retry 2 for request 1234"
        结构化定义:
          prompt_id=agent_bridge_retry locale=en-US text="AgentsBridge retry {count} for request {request_id}" audience=devops
    Prompt 变量表:
      - 名称:count | 类型:integer | 必填:是 | 默认:0 | 示例:2 | 说明: 重试次数。
      - 名称:request_id | 类型:string | 必填:是 | 示例:"abcd" | 说明: 请求 ID。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/agents_bridge.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^agent_bridge_"},
          "locale": {"type": "string"},
          "text": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_agents_bridge(): ...  streaming
        """
        MUST build AgentRequest from CoreEnvelope via to_agent_request()。
        MUST call AgentsGateway.dispatch_stream when OPENAI_API_KEY present。
        MUST fall back to ComposeRenderer when key missing or Responses API errors after 2 retries。
        SHOULD append chunks to conversation store and update tokens_usage。
        MUST emit events on chunk yield (chunk_index, tokens_used)。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_dispatch_stream(request): ...  调用网关
        """Returns async iterator of chunks。"""
      - def call_compose_render(prompt, kb_scope): ...  离线渲染
        """Reads KnowledgeBase and yields markdown text。"""
    Config Contract (MUST):
      - Contracts/behavior_contract.py MUST include behavior_agents_bridge。
      - Contracts/toolcalls.py MUST include call_dispatch_stream + call_compose_render。
      - Config/prompts.*.yaml MUST include agent_bridge_* prompts。
    Safety & Refusal Policy (MUST):
      - If prompt contains disallowed content flagged by Responses API, MUST stop streaming and send refusal via adapters。
      - If tokens_usage > 8k, MUST summarize conversation before continuing。
    i18n & Brand Voice (MUST):
      - zh-CN 提示强调降级说明。
      - en-US 说明包含 request_id。
    Output Contract (MUST):
      {
        "agent_bridge_result": {
          "type": "object",
          "required": ["mode", "chunks", "tokens_usage"],
          "properties": {
            "mode": {"type": "string", "enum": ["responses_api", "compose_renderer"]},
            "chunks": {"type": "array", "items": {"type": "string"}},
            "tokens_usage": {"type": "integer", "minimum": 0}
          }
        }
      }
    Logging & Observability (MUST):
      - Metrics: agent_bridge_first_chunk_latency, agent_bridge_retry_total, agent_bridge_offline_total。
      - Logs: request_id convo_id mode tokens_usage error_type。
    Versioning & Traceability (MUST):
      - doc version=1.1.0 -> AgentsBridge contract revision b1。
      - Each fallback event MUST record doc_id in telemetry。
    Golden Sample(s) (MUST >=3):
      - Sample A: Responses API path success mode responses_api tokens_usage 1200。
      - Sample B: ComposeRenderer fallback mode compose_renderer tokens_usage 0。
      - Sample C: Responses API error then fallback recorded with prompt id agent_bridge_retry。
    Counter Sample(s) (MUST >=2):
      - Counter A: prompt "" -> schema fail。
      - Counter B: retries > 2 -> MUST escalate, no silent continue。
    决策表 / 状态机 / 顺序化约束:
      | Condition | Action | Notes |
      | API key present | use Responses API | stream chunk size 128 |
      | API key missing | use ComposeRenderer | add system_tag "offline" |
      | Gateway retryable error count >=2 | fallback + notify |
    如何使用:
      - CoreEnvelope 调用 behavior_agents_bridge -> streaming -> adapters.response。
    agent如何读取:
      - AgentsGateway handles actual LLM or KB retrieval。
    边界与回退:
      - conversation store > 50 -> pop oldest, log compression。
      - tokens_usage > 8k -> run summarization plugin。
    SLO / 阈值 / 触发条件:
      - 首字节延迟 SHOULD < 1s。
      - streaming 中断率 MUST < 1%。
      - tokens_usage overflow 3 times -> open incident。
    """
# 标题: Kobe 顶层入口与目录布局
def section_top_entry(): ...  顶层入口章节
    """
    设计意图:
      - MUST 指定 app.py 为单一入口，明确 infra core TelegramBot 目录职责。
      - SHOULD 为 codegen target 提供路径占位符。
    设计原因:
      - 防止 channel 特化入口污染平台。
      - 提前规划 services/<channel> 扩展位。
    接口锚点:
      - app.py  {REPO_ROOT}/app.py
      - infra/fastapi_app.py  {REPO_ROOT}/infra/fastapi_app.py
      - core/schema.py core/adapters.py core/context.py  {REPO_ROOT}/core/
      - TelegramBot/routes.py runtime.py handlers/message.py adapters/*
    需求字段:
      - app.py duties: env load memory_preload logging bootstrap FastAPI register routes
      - infra duties: HTTP server creation dependency wiring observability
      - core duties: schema adapters context bridging Agents
      - TelegramBot duties: aiogram runtime handlers adapters
    二级嵌套:
      - EntryFlow: env bootstrap -> memory preload -> FastAPI init -> channel registration -> run server
      - DirectoryOwnership: owner contact review cadence code owners file
    三级嵌套:
      - env bootstrap: read .env + secrets -> validate -> inject settings
      - channel registration: TelegramBot.routes -> app.include_router -> log route names
    JSON Schema (MUST):
      {
        "$id": "kobe/layout/top_entry.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["app_py", "infra", "core", "telegrambot"],
        "properties": {
          "app_py": {"type": "string", "const": "{REPO_ROOT}/app.py"},
          "infra": {
            "type": "array",
            "items": {"type": "string", "pattern": "^\{REPO_ROOT\}/infra/"},
            "minItems": 1
          },
          "core": {
            "type": "array",
            "items": {"type": "string", "pattern": "^\{REPO_ROOT\}/core/"},
            "minItems": 3
          },
          "telegrambot": {
            "type": "array",
            "items": {"type": "string", "pattern": "^\{REPO_ROOT\}/TelegramBot/"},
            "minItems": 4
          }
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - entry_missing_file（locale=zh-CN, audience=devops）
        用途: 通知缺失入口文件。
        触发条件: call_verify_layout 检测到 app.py 等不存在。
        变量说明: {path}。
        示例文案: "缺少入口文件 Kobe/app.py"
        结构化定义:
          prompt_id=entry_missing_file locale=zh-CN text="缺少入口文件 {path}" audience=devops
      - entry_layout_violation（locale=en-US, audience=maintainer）
        用途: 报告目录职责与文档不一致。
        触发条件: layout check mismatch。
        变量说明: {component}。
        示例文案: "Layout mismatch at TelegramBot/adapters"
        结构化定义:
          prompt_id=entry_layout_violation locale=en-US text="Layout mismatch at {component}" audience=maintainer
    Prompt 变量表:
      - 名称:path | 类型:string | 必填:是 | 示例:"Kobe/app.py" | 说明: 缺失文件。
      - 名称:component | 类型:string | 必填:是 | 示例:"TelegramBot/adapters" | 说明: 出问题的组件。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/top_entry.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^entry_"},
          "locale": {"type": "string"},
          "text": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_top_entry(): ...  入口合约
        """
        MUST ensure env bootstrap occurs before importing TelegramBot modules。
        MUST inject {DOC_ID} and {DOC_COMMIT} into logging context。
        SHOULD call register_routes for each channel directory listed。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_verify_layout(manifest): ...  校验目录
        """Reads ProjectLayout manifest ensures required files present。"""
      - def call_register_channel(app, module): ...  注册渠道
        """Imports module.routes and attaches to FastAPI app。"""
    Config Contract (MUST):
      - Contracts/toolcalls.py MUST expose call_verify_layout。
      - Config/prompts.*.yaml MUST include entry_* prompts。
      - Contracts/output.schema.json MUST include top_entry manifest definitions。
    Safety & Refusal Policy (MUST):
      - Missing app.py -> refuse deploy。
      - TelegramBot directory absent -> refuse and prompt entry_missing_file。
    i18n & Brand Voice (MUST):
      - zh-CN: 指令式提示。
      - en-US: concise incident tone。
    Output Contract (MUST):
      {
        "top_entry_manifest": {
          "type": "object",
          "required": ["app_py", "directories"],
          "properties": {
            "app_py": {"type": "string"},
            "directories": {"type": "array", "items": {"type": "string"}}
          }
        }
      }
    Logging & Observability (MUST):
      - Metrics: layout_check_latency, layout_violation_total。
      - Logs: include component, action, request_id。
    Versioning & Traceability (MUST):
      - Layout manifest version v1.1.0。
      - commits touching layout MUST mention doc_id。
    Golden Sample(s) (MUST >=3):
      - Sample A: manifest lists app.py infra/fastapi_app.py core/schema.py TelegramBot/routes.py -> status ok
      - Sample B: manifest includes services/web placeholder -> status ok
      - Sample C: manifest missing TelegramBot -> triggers entry_missing_file prompt
    Counter Sample(s) (MUST >=2):
      - Counter A: infra list empty -> schema fail
      - Counter B: path outside {REPO_ROOT} -> reject
    决策表 / 状态机 / 顺序化约束:
      | Stage | Condition | Action |
      | bootstrap | manifest valid | proceed |
      | bootstrap | manifest missing file | halt + prompt |
      | rollout | add new channel | update manifest + prompts |
    如何使用:
      - CI 运行 call_verify_layout -> compare with repo。
      - 架构评审 referencing manifest。
    agent如何读取:
      - Agents referenced only via core; manifest prevents direct import。
    边界与回退:
      - app.py rename -> update manifest + codegen paths。
      - Temporary experiments -> place under services/experimental and record future_hooks。
    SLO / 阈值 / 触发条件:
      - Layout check time SHOULD < 2s。
      - Violations MUST block merge。
      - Manifest update lag MUST < 1 day。
    """
# 标题: 文件架构
def section_file_layout(): ...  文件架构章节
    """
    设计意图:
      - MUST 给出最新目录树，供脚本和 codegen 使用。
      - SHOULD 标注 owner 与未来扩展位。
    设计原因:
      - 多渠道协作需要统一文件放置。
      - 防止旧目录残留。
    接口锚点:
      - WorkPlan/02TelegramBotGCmessagePlan.md
      - scripts/layout/check_layout.py (待实现)
      - git root {REPO_ROOT}
    需求字段:
      - tree ascii 表示 app.py infra core TelegramBot OpenaiAgents KnowledgeBase SharedUtility WorkPlan Tests
      - ownership map: app.py -> platform owner, infra -> infra owner, core -> ai platform, TelegramBot -> channel owner
      - future_hooks: services/<channel>
    二级嵌套:
      - tree.level1 -> directories
      - tree.level2 -> files
    三级嵌套:
      - TelegramBot.adapters -> telegram.py response.py
      - TelegramBot.handlers -> message.py
    JSON Schema (MUST):
      {
        "$id": "kobe/layout/tree.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["tree", "ownership", "future_hooks"],
        "properties": {
          "tree": {"type": "string"},
          "ownership": {
            "type": "object",
            "required": ["KnowledgeBase", "SharedUtility", "WorkPlan", "OpenaiAgents", "TelegramBot", "Tests", "logs"],
            "properties": {
              "KnowledgeBase": {"type": "string"},
              "SharedUtility": {"type": "string"},
              "WorkPlan": {"type": "string"},
              "OpenaiAgents": {"type": "string"},
              "TelegramBot": {"type": "string"},
              "Tests": {"type": "string"},
              "logs": {"type": "string"}
            },
            "additionalProperties": true
          },
          "future_hooks": {
            "type": "array",
            "items": {"type": "string"}
          }
        },
        "additionalProperties": false
      }
    Prompt Catalog (MUST):
      - layout_missing_dir（locale=zh-CN, audience=dev）
        用途: 提醒开发目录缺失。
        触发条件: call_compare_tree 检测 missing。
        变量说明: {dir}。
        示例文案: "目录缺失 core/"
        结构化定义:
          prompt_id=layout_missing_dir locale=zh-CN text="目录缺失 {dir}" audience=dev
      - layout_owner_mismatch（locale=en-US, audience=ops）
        用途: 报告 ownership 配置不一致。
        触发条件: layout guard 发现 owner 不匹配。
        变量说明: {component}。
        示例文案: "Ownership mismatch TelegramBot"
        结构化定义:
          prompt_id=layout_owner_mismatch locale=en-US text="Ownership mismatch {component}" audience=ops
    Prompt 变量表:
      - 名称:dir | 类型:string | 必填:是 | 默认:"" | 示例:"core/" | 说明: 缺失目录。
      - 名称:component | 类型:string | 必填:是 | 默认:"" | 示例:"TelegramBot" | 说明: ownership 不匹配的组件。
    Prompt JSON Schema (MUST):
      {
        "$id": "kobe/prompts/layout_tree.schema.json",
        "type": "object",
        "required": ["prompt_id", "locale", "text"],
        "properties": {
          "prompt_id": {"type": "string", "pattern": "^layout_"},
          "locale": {"type": "string"},
          "text": {"type": "string"}
        }
      }
    Behavior Contract (MUST):
      - def behavior_layout_guard(): ...  目录守卫
        """
        MUST diff actual fs tree vs documented tree。
        MUST alert via layout_missing_dir when mismatch。
        SHOULD auto update ownership docs when files move。
        """
    ToolCall / FunctionCall Contract (MUST):
      - def call_scan_tree(root): ...  扫描
        """Returns ascii tree string。"""
      - def call_compare_tree(expected, actual): ...  对比
        """Returns diff; non empty -> raise LayoutMismatch。"""
    Config Contract (MUST):
      - Config/prompts.*.yaml MUST include layout_* prompts。
      - Contracts/toolcalls.py MUST declare call_scan_tree/call_compare_tree。
    Safety & Refusal Policy (MUST):
      - Missing critical directory -> refuse deploy。
      - Ownership mismatch -> block merge。
    i18n & Brand Voice (MUST):
      - zh-CN 语气直接。
      - en-US 简洁。
    Output Contract (MUST):
      {
        "layout_report": {
          "type": "object",
          "required": ["tree", "ownership", "status"],
          "properties": {
            "tree": {"type": "string"},
            "ownership": {"type": "object"},
            "status": {"type": "string", "enum": ["clean", "violation"]}
          }
        }
      }
    Logging & Observability (MUST):
      - Metrics: layout_scan_latency_ms, layout_violation_total。
      - Logs: include dir path, owner, request_id。
    Versioning & Traceability (MUST):
      - tree version t1.1 与 doc schema_version 对齐。
      - future_hooks 更新需记录 doc_id。
    Golden Sample(s) (MUST >=3):
      - Sample A: tree 包含所有必需目录 -> status clean
      - Sample B: ownership 指定 platform/channel -> status clean
      - Sample C: future_hooks 包含 services/web -> status clean
    Counter Sample(s) (MUST >=2):
      - Counter A: tree 缺 TelegramBot -> violation
      - Counter B: ownership.core="" -> violation
    决策表 / 状态机 / 顺序化约束:
      | Check | Condition | Action |
      | tree completeness | missing directory | fail CI |
      | ownership | mismatch | request owner update |
      | future hooks | new channel planned | append entry |
    如何使用:
      - scripts/layout/check_layout.py 调用 behavior_layout_guard。
    agent如何读取:
      - Agents 关注 OpenaiAgents 所属 owner。
    边界与回退:
      - tree 与 git 不符 -> 更新文档或阻止合并。
      - 临时目录 -> 记录在 future_hooks。
    SLO / 阈值 / 触发条件:
      - Layout check failure rate SHOULD < 1% weekly。
      - tree 更新后 24h 内同步脚本。
      - ownership 变更未同步 -> trigger audit。
    tree:
      {REPO_ROOT}/
      ├── app.py
      ├── core/
      │   ├── schema.py
      │   ├── adapters.py
      │   └── context.py
      ├── Config/
      ├── Contracts/
      ├── KnowledgeBase/
      ├── SharedUtility/
      ├── WorkPlan/
      ├── OpenaiAgents/
      ├── TelegramBot/
      ├── Tests/
      └── logs/
    """
# 标题: Prompt 总览清单
设计意图: "集中罗列全套提示类别，便于人工审阅与机检映射。"
设计原因: "保证 system/triage/summarize/compose/clarify/toolcall/refusal/welcome/help/rate_limit/degrade 全量覆盖。"
接口锚点:
class PromptRegistry: ...  "Contracts/behavior_contract.py"
需求字段 = {
"categories": ["system","triage","summarize","compose","clarify","toolcall","refusal","welcome","help","rate_limit","degrade"],
"mapping": {
  "system": ["agent_triage_system"],
  "triage": ["agent_triage_system"],
  "summarize": ["telegram_history_summarize"],
  "compose": ["agent_consult_compose","agency_compose_header","agency_compose_body"],
  "clarify": ["telegram_user_clarify"],
  "toolcall": ["telegram_toolcall_error"],
  "refusal": ["agent_refusal_policy","core_schema_violation"],
  "welcome": ["telegram_welcome"],
  "help": ["telegram_prompt_missing"],
  "rate_limit": ["budget_alert"],
  "degrade": ["agent_bridge_offline","telegram_streaming_degrade"]
}
}

分类定义 (MUST):
  - telegram_history_summarize（locale=zh-CN, audience=llm）
    用途: 当对话历史超过阈值，提炼要点供后续回答。
    触发条件: 全局 summary_threshold_tokens 触发。
    变量说明: {history_chunks}, {limit_tokens}。
    示例文案: "请把以下历史精炼为要点，长度不超过 {limit_tokens} tokens：{history_chunks}"
    结构化定义:
      prompt_id=telegram_history_summarize locale=zh-CN audience=llm
      text="请把以下历史精炼为要点，长度不超过 {limit_tokens} tokens：{history_chunks}"
    Prompt 变量表:
      - 名称:history_chunks | 类型:list[string] | 必填:是 | 默认:[] | 示例:["昨日问候","日报需求"] | 说明: 需要总结的历史片段。
      - 名称:limit_tokens | 类型:integer | 必填:是 | 默认:200 | 示例:200 | 说明: 摘要长度上限。

  - telegram_user_clarify（locale=zh-CN, audience=user）
    用途: 当用户表达不清时请求澄清。
    触发条件: triage/confidence 低于阈值或 selectors 无匹配。
    变量说明: {examples}，{question}。
    示例文案: "我需要更多信息，例如：{examples}。请确认：{question}"
    结构化定义:
      prompt_id=telegram_user_clarify locale=zh-CN audience=user
      text="我需要更多信息，例如：{examples}。请确认：{question}"
    Prompt 变量表:
      - 名称:examples | 类型:list[string] | 必填:否 | 默认:[] | 示例:["报表日期","部门名称"] | 说明: 引导示例。
      - 名称:question | 类型:string | 必填:是 | 默认:"" | 示例:"你要日报还是周报？" | 说明: 澄清问题。

  - telegram_toolcall_error（locale=en-US, audience=ops）
    用途: 工具调用失败（参数缺失/超时）。
    触发条件: toolcall 返回错误码。
    变量说明: {tool}, {error}, {request_id}。
    示例文案: "Toolcall {tool} failed: {error}, request={request_id}"
    结构化定义:
      prompt_id=telegram_toolcall_error locale=en-US audience=ops
      text="Toolcall {tool} failed: {error}, request={request_id}"
    Prompt 变量表:
      - 名称:tool | 类型:string | 必填:是 | 默认:"" | 示例:"mem_read" | 说明: 工具名。
      - 名称:error | 类型:string | 必填:是 | 默认:"" | 示例:"timeout" | 说明: 错误详情。
  - 名称:request_id | 类型:string | 必填:是 | 默认:"" | 示例:"abcd" | 说明: 请求 ID。

  - agent_triage_system（locale=zh-CN, audience=llm）
    用途: 引导 LLM 判断用户意图（system/triage 角色），并给出候选 domain_profile。
    触发条件: 每次进入 triage 阶段。
    变量说明: {user_message}, {intent_candidates}, {domain_profiles}。
    示例文案: "你是对话路由器。请根据 {user_message} 在 {intent_candidates} 中判定意图，并从 {domain_profiles} 选择最匹配的领域。"
    结构化定义:
      prompt_id=agent_triage_system locale=zh-CN audience=llm
      text="你是对话路由器。请根据 {user_message} 在 {intent_candidates} 中判定意图，并从 {domain_profiles} 选择最匹配的领域。"
    Prompt 变量表:
      - 名称:user_message | 类型:string | 必填:是 | 默认:"" | 示例:"请给我今天的销售情况" | 说明: 用户原始输入。
      - 名称:intent_candidates | 类型:list[string] | 必填:是 | 默认:["consult","plan","operation"] | 示例:["consult","plan"] | 说明: 候选意图集合。
      - 名称:domain_profiles | 类型:list[string] | 必填:是 | 默认:[] | 示例:["sales","finance"] | 说明: 可选领域标签/摘要。

  - agent_consult_compose（locale=zh-CN, audience=llm）
    用途: 在咨询意图下生成可直接发送给用户的回答（compose 类别）。
    触发条件: triage 判定 intent=consult。
    变量说明: {context_snippets}, {tone}, {token_budget}。
    示例文案: "请以 {tone} 语气，用不超过 {token_budget} tokens，基于以下上下文回答：{context_snippets}"
    结构化定义:
      prompt_id=agent_consult_compose locale=zh-CN audience=llm
      text="请以 {tone} 语气，用不超过 {token_budget} tokens，基于以下上下文回答：{context_snippets}"
    Prompt 变量表:
      - 名称:context_snippets | 类型:list[string] | 必填:是 | 默认:[] | 示例:["同比+12%","环比-3%"] | 说明: 索引摘取的上下文片段。
      - 名称:tone | 类型:string | 必填:否 | 默认:"业务口吻" | 示例:"正式" | 说明: 输出语气。
      - 名称:token_budget | 类型:integer | 必填:是 | 默认:300 | 示例:300 | 说明: 该轮最大 tokens。

  - agent_refusal_policy（locale=zh-CN, audience=llm）
    用途: 当触发安全/合规/合同校验失败时，生成标准拒绝回复（refusal 类别）。
    触发条件: safety/contract 策略命中或输出校验失败。
    变量说明: {rule}, {contact}。
    示例文案: "因触发 {rule}，当前请求无法处理。如需帮助，请联系 {contact}。"
    结构化定义:
      prompt_id=agent_refusal_policy locale=zh-CN audience=llm
      text="因触发 {rule}，当前请求无法处理。如需帮助，请联系 {contact}。"
    Prompt 变量表:
      - 名称:rule | 类型:string | 必填:是 | 默认:"policy_violation" | 示例:"policy_violation" | 说明: 触发的拒绝策略。
      - 名称:contact | 类型:string | 必填:否 | 默认:"support@example.com" | 示例:"ops@example.com" | 说明: 联系方式。

  - budget_alert（locale=en-US, audience=ops）
    用途: 提醒运维/开发当前请求消耗超出阈值（rate_limit 类别）。
    触发条件: tokens 使用超过 per_call/per_flow 或达到 summary_threshold。
    变量说明: {stage}, {tokens}, {threshold}。
    示例文案: "Token budget exceeded at {stage}: tokens={tokens} > {threshold}"
    结构化定义:
      prompt_id=budget_alert locale=en-US audience=ops
      text="Token budget exceeded at {stage}: tokens={tokens} > {threshold}"
    Prompt 变量表:
      - 名称:stage | 类型:string | 必填:是 | 默认:"compose" | 示例:"compose" | 说明: 触发阶段。
      - 名称:tokens | 类型:integer | 必填:是 | 默认:0 | 示例:3500 | 说明: 本次消耗。
      - 名称:threshold | 类型:integer | 必填:是 | 默认:3000 | 示例:3000 | 说明: 阈值。

  - telegram_welcome（locale=zh-CN, audience=user）
    用途: 首次互动的欢迎语与使用提示。
    触发条件: /start 或首次会话。
    变量说明: {bot_name}。
    示例文案: "欢迎使用 {bot_name}，直接发送问题或输入 /help 获取帮助。"
    结构化定义:
      prompt_id=telegram_welcome locale=zh-CN audience=user
      text="欢迎使用 {bot_name}，直接发送问题或输入 /help 获取帮助。"
    Prompt 变量表:
      - 名称:bot_name | 类型:string | 必填:是 | 默认:"KobeBot" | 示例:"KobeBot" | 说明: 机器人名称。

  - telegram_streaming_degrade（locale=zh-CN, audience=user）
    用途: 流式降级提示（如多次编辑失败）。
    触发条件: streaming 编辑重试后仍失败。
    变量说明: {request_id}。
    示例文案: "当前网络不稳定（请求 {request_id}），已切换为非流式回复。"
    结构化定义:
      prompt_id=telegram_streaming_degrade locale=zh-CN audience=user
      text="当前网络不稳定（请求 {request_id}），已切换为非流式回复。"
    Prompt 变量表:
      - 名称:request_id | 类型:string | 必填:是 | 默认:"" | 示例:"abcd" | 说明: 请求 ID。
  - agency_compose_header（locale=zh-CN, audience=llm）
    用途: 生成回答顶部框架，展示机构与领域名称，可作为消息第一行标题（compose 类别）。
    触发条件: compose_response 初始化 header 时触发。
    变量说明: {agency_display_name}, {domain_name}。
    示例文案: "### {agency_display_name} | {domain_name}"
    结构化定义:
      prompt_id=agency_compose_header locale=zh-CN audience=llm
      text="### {agency_display_name} | {domain_name}"
    Prompt 变量表:
      - 名称:agency_display_name | 类型:string | 必填:是 | 默认:"" | 示例:"零售事业部" | 说明: 机构展示名。
      - 名称:domain_name | 类型:string | 必填:是 | 默认:"" | 示例:"销售洞察" | 说明: 当前领域名称。

  - agency_compose_body（locale=zh-CN, audience=llm）
    用途: 渲染主体段落或要点列表，按照模板与 slot 值拼装出用户可读的正文（compose 类别）。
    触发条件: compose_response 渲染 body 阶段触发。
    变量说明: {body_template}, {slot_values}。
    示例文案: "{body_template}"
    结构化定义:
      prompt_id=agency_compose_body locale=zh-CN audience=llm
      text="{body_template}"
    Prompt 变量表:
      - 名称:body_template | 类型:string | 必填:是 | 默认:"" | 示例:"- 指标：{metric}\n- 趋势：{trend}" | 说明: 模板文本，含占位符。
      - 名称:slot_values | 类型:list[string] | 必填:否 | 默认:[] | 示例:["指标：12%","趋势：上行"] | 说明: 用于填充模板的值/片段。

如何使用: "审阅者核对 mapping 是否与各章节 Prompt Catalog 一致；缺项须在对应章节补齐。"
SLO / 阈值 / 触发条件: "categories 覆盖率 MUST 100%；发现缺项即阻断发布。"

 ``` 
