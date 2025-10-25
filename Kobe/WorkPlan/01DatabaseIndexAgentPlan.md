```yaml
doc:
  id: DatabaseIndexAgentPlan
  title: Telegram BI/Index 方案与 Agent 开发工作笔记
  language: zh-CN
  created: 2025-10-25
  updated: 2025-10-25
  owner: owner
  editors:
    - AI Assistant
  status: draft
  repository_root: D:\\AI_Projects
  focus_note_path: D:\\AI_Projects\\TelegramChatHistory\\Workspace\\.WorkPlan\\DatabaseIndexAgentPlan.md
  knowledge_base_root: AckowleageBase
  all_paths_relative_to: BASE_DIR=Kobe
  purpose: >
    作为面向 AI 与开发者的“几乎可执行”设计文档：
    本文优先定义 index.yaml 的结构与字段（单一事实来源，SSOT）；
    注意：各“独立机构/业务体系（agency）”各自维护一份独立的 index.yaml，
    每份 index.yaml 是该机构/业务线的唯一真源；项目可并行存在多份 index.yaml；
    Agent 仅作为索引的消费者；TelegramBot 改造按此索引完成对接。
writing_rules:
  content_ratio: "20% 代码式标记 + 80% 中文叙述"
  structure_order:
    - 标题: 每节以 "# 标题: ..." 开头, 简述目标与范围
    - 设计意图: 先说明“设计成怎么实现”与“为何如此设计”
    - 设计原因: 引用代码/文档/数据结构作为证据
    - 接口锚点: 仅写 import/from/def/class 声明行(无实现)
    - 需求字段: 列清晰的字段与约束, 使用英文键名与 ASCII 标点
    - 二级嵌套: 展开对象/数组字段, 说明层级关系与依赖
    - 三级嵌套: 必要时补充, 记录边界与回退
    - 如何使用: 叙述调用顺序与输入输出契约, 不写实现
    - agent如何读取: 叙述检索与最小读取流程, 不写实现
  body_style:
    description: >
      正文采用 Python 上色以提升可读性；允许 import/from/def/class 作为“声明式锚点”，
      允许 if/else/try/except/return 表达流程与回退；禁止函数体、真实赋值、函数调用与循环；
      仅标题使用 #，其它小节为纯文本行或引号内容；按滚雪球顺序展开。
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
    multiline_allowed: true
    nesting_allowed: true
    parse_markers:
      - 标题
      - 设计意图
      - 设计原因
      - 接口锚点
      - 需求字段
      - 二级嵌套
      - 三级嵌套
      - 如何使用
      - agent如何读取
      - 边界与回退
      - 模板与占位
  code_guidelines:
    language: python
    libraries:
      - openai-agents
      - pydantic>=2
    patterns:
      - 正文不出现任何实现细节；仅保留接口锚点与中文说明
      - 参数使用 snake_case；时间统一 ISO-8601（含时区偏移）
  acceptance_criteria:
    - 正文整体包裹在一个 python 代码块中，仅用于高亮与结构表达
    - 每节按“设计意图→设计原因→接口锚点→需求字段→使用→读取→回退”顺序叙述
    - 文本基于现有代码/文档的实际字符串(函数名/文件路径/键名)，可直接映射为实现与测试契约，表达无歧义
changelog:
  - date: 2025-10-25
    author: AI Assistant
    change: 规范对齐；修复 YAML/正文分离；引入 index.yaml 设计为主、Agent 为消费者
```

```python
# 标题: 文档背景与阅读说明
from agents import Agent, Runner  "依赖锚点: OpenAI Agents SDK; 默认 Responses API"
from agents.models.openai_responses import OpenAIResponsesModel  "依赖锚点: Responses API 模型封装"

需求字段 = {
"knowledge_base_root": "AckowleageBase",
"focus_note_path": "D:\\AI_Projects\\TelegramChatHistory\\Workspace\\.WorkPlan\\DatabaseIndexAgentPlan.md",
"sections": ["Index设计", "Agent设计", "集成设计/TelegramBot 改造"]
}
设计意图: "优先定义 index.yaml 结构与字段；Agent 只消费 index.yaml；TelegramBot 改造与 Agent 对齐。"

# 标题: 最小改造基座 / 接口适配（第一步必做）

需求字段 = {
"目标": "以最小侵入方式把 Telegram 消息管线接到我们的 Agents 接口, 保持原事件循环不变, 先跑通对话",
"原则": ["不改 ApplicationBuilder 启动范式", "不改 handlers 注册模式", "仅替换‘向模型发问’这一层的实现"],
"兼容契约": "新适配层需保持 BaseLLM.ask_stream_async/ask_stream 的生成器语义, 以便 bot.py 的 getChatGPT 原样复用",
"环境": {"USE_AGENTS": true, "MODEL": "agents", "BASE_DIR": "Kobe"}
}
设计意图: "先把‘出口’接稳(问答可通), 再逐步实现 index 与 Agent 工作流; 这是最易出错但最小的改动点。"

接口锚点:
def AgentsBridge.ask_stream_async(): ...  文本: 适配层; 输入 prompt/convo_id/model/语言等; 内部调用 AgentsGateway.dispatch_stream; 以增量文本块 yield 回 Telegram 层;
def AgentsBridge.ask_stream(): ...  文本: 同步包装, 基于 async→sync 生成器适配; 维持 BaseLLM 接口一致;
def AgentsGateway.dispatch_stream(): ...  文本: 将 Telegram 文本转为 {intent, tools}; 咨询→compose_reply 小预算; 方案→mem_read+planner 中预算; 按 TokenMeter 汇报用量;
def TelegramAdapter.to_markdown_chunk(): ...  文本: 将 Agents 增量输出映射为 Telegram 需要的 MarkdownV2 片段(避免破坏代码块/图片占位);
def Config.get_robot_agents(): ...  文本: 当 USE_AGENTS 或 MODEL=="agents" 时返回 AgentsBridge 实例; 否则保持原 get_robot 行为;

如何使用:
在 .env 设置 USE_AGENTS=true, MODEL=agents; TelegramBot/config.py 读取 .env 后, get_robot 返回 AgentsBridge; bot.py 的 getChatGPT 函数不变(继续消费 ask_stream_async 增量), 立即可对话;

agent如何读取:
AgentsBridge 内部使用内存快照与 tools; 咨询/介绍→compose_reply 生成短句; 方案/办理→mem_read 取段落后交 Planner; Guardrails.enforce_brevity 控制长度; TokenMeter 输出本轮用量。

# 标题: 工程现状 / 仓库结构与启动方式（给开发AI的上下文）

需求字段 = {
"BASE_DIR": "Kobe",  # 仓库根; 所有索引路径相对该根解析
"org_index_file": "AckowleageBase/AckowleageBase_index.yaml",  # 顶层索引相对路径
"agency_index_pattern": "AckowleageBase/<agency>/<agency>_index.yaml",  # 机构索引命名规范
"kb_root": "AckowleageBase",  # 知识库根; 运行期已内存化
"env_file": ".env",  # 放置于 BASE_DIR 下; 由 TelegramBot/config.py 显式加载
"agents_sdk_root": "OpenaiAgents",  # OpenAI Agents SDK 本地工程
"telegram_bot_root": "TelegramBot",  # 机器人工程
}
设计意图: "为执行开发任务的 AI 提供最小但关键的工程上下文, 防止跑偏。"

如何使用:
入口应用: "TelegramBot/bot.py"（python-telegram-bot v20+ 应用, 非 FastAPI）; 启动方式: ApplicationBuilder().build(); 依据 WEB_HOOK 选择 run_webhook 或 run_polling; 禁止改其启动范式（仅允许最小注入）。

agent如何读取:
所有文件与索引路径相对 BASE_DIR 解析; 禁止使用绝对路径; MemoryLoader 在进程启动时一次性加载为 MemorySnapshot; 运行期工具仅访问内存。

# 标题: 集成约束 / 最小注入与环境加载（给开发AI）

需求字段 = {
"env_loading": "TelegramBot/config.py 已改为优先 find_dotenv(usecwd=True), 找不到则回落 BASE_DIR/.env",
"bootstrap": "在应用启动前/入口处调用 Bootstrap.memory_preload 与 AgentsGateway.attach_snapshot（可挂到 post_init 钩子）",
"no_framework_change": "不改 ApplicationBuilder/run_webhook/run_polling 方式, 保持现状",
}
设计意图: "以最小侵入方案接入内存快照与 Agents 工具, 保障现有机器人可持续运行。"

如何使用:
加载 .env 后, 以 BASE_DIR 相对路径构建 MemorySnapshot; 将 snapshot 与 app_name=\"Kobe\" 注入 AgentsGateway; 其它逻辑不变。
实现提示:
  - TelegramBot/config.py 暴露 `_ensure_agents_bridge()`、`get_robot_agents()` 与 `get_active_robot()`，当 `USE_AGENTS=true` 或 `MODEL=agents` 时返回 `AgentsBridge`；否则回退历史 ChatGPT 路径。
  - `.env` 中保留 `TELEGRAM_BOT_TOKEN`、`OPENAI_API_KEY`、`USE_AGENTS`、`WEB_HOOK` 等键，config.py 会自动创建/读取 BASE_DIR 下的 `user_configs/*.json`（支持 CHAT_MODE=global/multiusers）。
  - bot.py 仅在 `ApplicationBuilder.post_init` 注入 `Bootstrap.memory_preload()` 与 `AgentsGateway.attach_snapshot()`，并复用现有 handlers/事件循环，确保 USE_AGENTS=false 时可无缝回退。

# 标题: 消息格式 / Telegram Markdown 转义约定（沿用既有实现）

设计意图: "复用 TelegramBot 现有 MarkdownV2 转义与分片逻辑, 不重复造轮子。"

需求字段 = {
"escape_impl": "md2tgmd.src.md2tgmd.escape",
"split_code_impl": "md2tgmd.src.md2tgmd.split_code",
"replace_all_impl": "md2tgmd.src.md2tgmd.replace_all",
}
如何使用:
TelegramAdapter.to_markdown_chunk 调用上述实现完成转义/分片; AgentsBridge 仅传递语义片段, 不直接操作 Markdown 细节。

# 标题: 品牌与欢迎语 / 多语言尾注（给开发AI）

需求字段 = {
"bot_brand": "Kobe",  # 自称与日志品牌
"welcome_zh": "您好，我是四方集团的小秘书 Kobe~ 我可以提供关于移民局所有业务的咨询和协调。",
"welcome_tail_languages": ["English", "中文", "Español", "العربية", "한국어"],  # 多语支持提示; 内容仍以英文为默认
}
设计意图: "统一对外话术与品牌自称, 并在首条消息以短句建立‘咨询域’边界。"

如何使用:
TriageAgent.classify_and_greet 在首次交互以小预算 LLM 返回简短欢迎/确认, 文案源自 welcome_zh 与语言设置; 该消息不长篇大论。

# 标题: 机构语义 / agency 命名（防混淆）

需求字段 = {
"agency_id": "kebab-case, 全局唯一且稳定; 当前=bi",
"agency": {"agency_id": "bi", "agency_name": "BureauOfImmigration"}
}
设计意图: "统一使用 agency 表达‘政府机构/业务体系’, 避免与‘公司内部部门’混淆。"

如何使用:
OrgIndexAgent/AgencyIndexAgent 与所有会话状态字段使用 agency_* 命名; 顶层 org 索引为 agencies 列表。


# 标题: Index设计 / 组织级顶层 index（机构路由，最简）

需求字段 = {
"org_index_file": "AckowleageBase/AckowleageBase_index.yaml",
"agencies": [
  {"agency_id": "<id>", "agency_name": "<name>", "agency_desc": "<description>", "agency_folder": "<relative_folder>", "index_rel": "index.yaml"}
],
"agency_synonyms?": {"<standard_name>": ["同义词1", "同义词2"]}
}
设计意图: "仅用于定位机构与其文件夹/机构索引(index.yaml)；不承载业务条目与值选择；上层字段可由脚本自机构索引反推生成（如 agency_name/agency_folder）。"
实现提示: 当前仓库已提供 AckowleageBase/AckowleageBase_index.yaml，内含 bi (BureauOfImmigration) 机构条目，并指向 AckowleageBase/BI/BI_index.yaml；OrgIndexAgent 直接加载该 YAML，即为目前生产真源。
      设计原因: "顶层只负责‘发现与路由’，复杂结构全部留在机构级 index.yaml，避免重复定义与维护成本。"

      如何使用:
      OrgIndexAgent.locate_agency 读取 org_index_file，依据 agency_name/agency_synonyms 与用户请求匹配机构；命中后以 agency_folder + index_rel 组装机构索引路径，交由 AgencyIndexAgent 继续处理。若用户提示词涉及多机构，允许返回多机构候选并由上层合并拼接或按需要进入语义读取最小段落。

      # 标题: Index设计 / 组织级可选预路由 routing_table（降本缩域）
      
      需求字段 = {
      "routing_table?": {
        "pricing": {"tokens": ["价格", "费用", "费率", "多少钱"], "agencies": ["bi"], "l3_candidates?": ["<level3_key>"]},
        "process": {"tokens": ["流程", "步骤", "怎么办理"], "agencies": ["bi"], "l3_candidates?": []},
        "faq": {"tokens": ["问", "FAQ"], "agencies": ["bi"]}
      }
      }
      设计意图: "在进入 LLM 前用确定性映射缩小候选集，降低平均 tokens；未命中时回退到纯 LLM。"
      语言适配: "routing_table.tokens 按 IntentAgent 检测到的语言选择对应词表；若该语言无词表则直接回退纯 LLM 判定。"
      
      如何使用:
      TriageAgent 先用 routing_table 从用户词面命中 {agencies, l3_candidates}（至多 K 个），再把候选作为限制项交给 LLM 判定与首轮问候；若无候选或歧义高 → 直接走 LLM 判定。该模块为可选与灰度，不改变保底链路。

agent如何读取:
若未命中机构 → 返回‘当前知识库尚未覆盖该机构’；若机构已注册但 index_rel 缺失 → 返回‘该机构索引暂不可用’并记录告警；其余流程与机构级索引一致。

# 标题: Index设计 / index.yaml 顶层结构

需求字段 = {
"index_file_pattern": "AckowleageBase/<agency>/<agency>_index.yaml",
"version": "v1",
"updated_at": "",
"kb_root": "AckowleageBase",
"path.syntax": "<domain>/<collection>/<level3>/<level4>/<attribute?>",
"domains": ["pricing", "process", "preconditions", "pre_required_documents", "applicability", "faq", "deliverables", "info_collection", "acknowledgement_flags", "service_related", "kpis", "risks", "semantic_profile"],
"lang.priority": ["default_language", "zh-CN", "en-US"],
"sections": ["agency", "domain_profiles", "compose_rules", "selectors", "synonyms", "entries", "slots", "build", "stats", "llm_policies"]
      }
设计意图: "知识库 YAML 不变；差异与深度在 index.yaml 表达；可跨知识库复用。"
设计原因: "1/2 级固定路径；3/4 级动态；5 级为属性层（但个别域在 4 即属性），必须以数据标注消解差异。"

二级嵌套:
agency_index_map? = {"bi": "AckowleageBase/BI/BI_index.yaml"}

# 标题: Index设计 / 内存快照与路径解析（运行期零磁盘IO）

设计意图: "运行期完全使用内存对象，避免本地文件 IO；路径语义保持不变，指向内存中的结构体。"

需求字段 = {
"MemoryLoader": {"load_all": true, "org_index": "AckowleageBase_index.yaml", "agency_indices": "<agency>_index.yaml", "kb_root": "AckowleageBase"},
"MemorySnapshot": {"snapshot_id": "<uuid>", "indexed_at": "<iso8601>", "agency_map": "{agency_id: AgencyView}", "bytes_approx": 0},
"InMemoryKB": {"entries": "list", "selectors": "dict", "slots": "dict", "synonyms": "dict", "domain_profiles": "dict", "compose_rules": "dict"},
"MemoryStore": {"get(path)": "value", "list(prefix)": "paths", "exists(path)": "bool"}
      }

def MemoryLoader.load_all(): ...  文本: 进程启动一次性解析顶层与各部门索引及业务 YAML, 构建 MemorySnapshot(只读)
def MemoryStore.get(): ...  文本: 从内存按 path.syntax 取值; 不做磁盘 IO
def MemoryStore.list(): ...  文本: 列举前缀路径; 用于生成占位与路径映射
def MemoryHealth.report(): ...  文本: 输出 snapshot_id/entries_count/bytes_approx/last_indexed_at

如何使用:
启动阶段构建 MemorySnapshot → 运行期所有工具仅访问 MemoryStore，不访问文件系统

agent如何读取:
OrgIndexAgent/AgencyIndexAgent/index_locate/index_get_paths_for_l3/mem_read 全部读内存; shape_override 与 selectors 在内存中生效

# 标题: Index设计 / domain_profiles 与 compose_rules（新增）

需求字段 = {
"agency": {"agency_id": "<id>", "agency_name": "<name>", "namespace?": "<ns>", "kb_id?": "<kb>"},
"domain_profiles": {
  "pricing": {"dynamic_levels": [3,4], "attr_level": 5, "compose_hint": "pricing_aggregate_fees"},
  "process": {"dynamic_levels": [3],   "attr_level": 4, "compose_hint": "process_outline"},
  "preconditions": {"dynamic_levels": [3], "attr_level": 4, "compose_hint": "rules_list"},
  "pre_required_documents": {"dynamic_levels": [3], "attr_level": 4, "compose_hint": "docs_list"},
  "applicability": {"dynamic_levels": [3], "attr_level": 4, "compose_hint": "scenarios_list"},
  "faq": {"dynamic_levels": [3], "attr_level": 4, "compose_hint": "qa_list"},
  "deliverables": {"dynamic_levels": [3], "attr_level": 4, "compose_hint": "deliverables_list"},
  "info_collection": {"dynamic_levels": [3], "attr_level": 4, "compose_hint": "info_list_items"}
},
"compose_rules": {
  "pricing": {"frame": "价格速览: {level3_name} 包含 {level4_item_list}.", "joiner": "，"},
  "process": {"frame": "办理步骤总览: {level3_name} 包含 {level4_item_list}.", "joiner": "，"},
  "preconditions": {"frame": "基本条件: {level3_name} 包含 {level4_item_list}.", "joiner": "，"},
  "pre_required_documents": {"frame": "前置材料: {level3_name} 包含 {level4_item_list}.", "joiner": "，"},
  "applicability": {"frame": "适用范围: {level3_name} 包含 {level4_item_list}.", "joiner": "，"},
  "faq": {"frame": "常见问答: {level3_name} 包含 {level4_item_list}.", "joiner": "，"},
  "info_collection": {"frame": "信息采集项: {level3_name} 包含 {level4_item_list}.", "joiner": "，"}
},
"render_policy": {
  "list_style": "bullet|inline",
  "max_items": 6,
  "ellipsis": "…",
  "joiner": "，",
  "sort": "original|alpha",
  "omit_empty": true,
  "dedupe": true,
  "casing": "preserve|title"
}
}
设计意图: "以域为单位声明动态层与属性层，前置拼接句式；Agent 零-LLM即可拼接首轮‘框架+占位’。"

# 标题: Index设计 / selectors 与 slots（已定）

需求字段 = {
"selectors": {
  "pricing": ["amount.display", "amount.value + currency", "notes"],
  "process": ["description", "title"],
  "pre_required_documents": ["documents", "trigger + documents"],
  "faq": ["answer"],
  "default": ["text"]
],
"slots": {
  "pricing": {"l3_slot": "level3_name", "l4_slot": "level4_fee_items", "selector_slot": "selector"},
  "process": {"l3_slot": "step_name", "l4_slot": "step_details"},
  "faq": {"l3_slot": "question_key", "l4_slot": "answer_key"},
  "info_collection": {"l3_slot": "group_name", "l4_slot": "item_list"}
}
}
边界与回退:
try 读取 "amount.display" except → return "amount.value + currency"; 若仍无 → return "notes"
if 缺失 "process/steps/<step>/description" → return "title"
语言: if 文档含 "default_language" → 返回对应语言; else → 返回原文

# 标题: Index设计 / pricing 聚合策略（确定性计算，非模板堆叠）
```yaml
需求字段 = {
"pricing.aggregate": {
  "inputs": {"fields": ["amount.value", "currency", "discounts?"], "group_by": ["level3_name"], "round": 2, "locale": "zh_CN|en_US"},
  "outputs": {"items": "[{l3,l4,value,display}]", "totals": "{by_l3, grand_total}", "notes?": "list"},
  "display": {"grand_total_slot": "{grand_total_display}", "by_l3_slot": "{by_l3_list}"}
}
}
设计意图: "金额/币种/合计用确定性工具计算, 不交给 LLM；模板只负责渲染。"
跨币种: "同一次聚合需同币种；若检测到多币种则分别汇总并各自渲染 totals（不做自动换汇）。"
如何使用:
compose_reply 在 domain=pricing 时调用聚合器生成 items/totals，再按 render_policy 与 frame 渲染首轮“价格速览”；后续如需细节，仅最小读取属性层进行替换，不做语义改写。
```

# 标题: Index设计 / entries 规范与覆盖（shape_override）

需求字段 = {
"entries": [
  {
    "doc_rel_path": "<relative/path.yaml>",
    "domain": "pricing|process|...",
    "collection": "items|steps|mandatory|conditional|required|not_eligible|qas|applicant|metadata",
    "level3_key": "<l3_key>",
    "level4_key": "<l4_key>",
    "l3_label": "<readable_name>",
    "l4_label": "<readable_name>",
    "value_selector": "selectors[domain] 或 entries 覆盖",
    "shape_override?": {"dynamic_levels": [3], "attr_level": 4},
    "compose_hint_override?": "info_list_items",
    "lang": "doc.default_language 或 lang.priority[1]",
    "tags": ["semantic_profile.intent", "semantic_profile.category", "semantic_profile.tags", "aliases?"],
    "mtime": "<source_file_mtime>",
    "indexed_at": "<index_time>"
  }
}
}
设计意图: "entries 到 level4 即止；属性层值由 Agent 按需读取；个别文档在 level4 即属性时，以条目级覆盖避免全局冲突。"
优先级: "属性层判定 entry.shape_override > domain_profiles.attr_level"

# 标题: Index设计 / synonyms 与 build/stats/llm_policies

需求字段 = {
"synonyms": {"standard_name": ["synonym1", "synonym2"]},
"build": {"indexed_at": "<iso8601>", "builder": "IndexBuilder", "run_id": "<uuid>", "schema_version": "1.0.0"},
"stats": {"doc_count": 0, "path_count": 0, "missing": 0, "overrides": 0, "conflicts": 0},
"llm_policies": {
  "triage": {"enabled": True, "max_tokens": 256},
  "intro_frame": {"enabled": True, "max_tokens": 256},
  "planner": {"enabled": True, "max_tokens": 4096},
  "brevity": {"max_sentences": 3, "max_bullets": 5, "forbid_essay": True},
  "business_lock": {"threshold": 5, "lockout_seconds": 3600, "lock_text": "尝试次数过多，请{countdown}再试。"}
}
}
设计意图: "把 LLM 可用性与预算放到数据层，仅在需要的节点开启；intro_frame 默认零-LLM。"

# 标题: Agent设计 / 使用 index.yaml 的接口锚点
from agents import function_tool  "依赖锚点: 工具清单与契约"
from agents import Agent, Runner  "依赖锚点: 会话循环与工具路由"
from OpenaiAgents.UnifiedCS.tools import ToolContext, toolset  "实现锚点: OpenaiAgents/UnifiedCS/tools.py，集中维护 locate_agency/compose_reply 等工具"

设计意图: "Agent 仅消费 index.yaml；首轮返回‘框架+占位+路径’，二阶段按需读取属性层；LLM 只在意图/方案类节点介入。机构/业务线通过 agency_id/kb_id 精确选择对应 index.yaml。" 所以 def IndexReader.load_index(): ... 然后 def IndexReader.locate_by_intent(): ...
实现提示: "ToolContext.attach_snapshot 在 OpenaiAgents/UnifiedCS/bootstrap.py 中由 memory_preload 调用，一次性注入 MemorySnapshot，toolset() 列表由 tools.py 暴露，供 AgentsGateway/Responses API 统一注册。"

def OrgIndexAgent.locate_agency(): ...  文本: 读取 org_index_file; 使用 agency_synonyms 与 domains 匹配机构; 输出 {agency_id, agency_name, agency_folder, index_rel}
def AgencyIndexAgent.load_agency_index(): ...  文本: 基于 {agency_folder, index_rel} 加载机构级 index.yaml; 暴露 agency/domain_profiles/compose_rules/selectors/slots/entries
def AgencyIndexAgent.route_agency_flow(): ...  文本: 依据 triage 决策选择“咨询/介绍”或“方案/办理”分支; 咨询走 compose_reply; 方案走检索+Planner

def IndexReader.load_index(): ...  文本: 读取并解析 index.yaml(可选 agency_id/kb_id), 暴露 agency/domain_profiles/compose_rules/selectors/slots/entries/synonyms
def IndexReader.locate_by_intent(): ...  文本: 基于意图与关键词过滤 entries(限定 agency_id/kb_id), 输出 domain 下某 level3 的全部 level4 路径
def IndexReader.get_paths_for_l3(): ...  文本: 输入 (domain, level3_key), 输出该主题下全部 level4 路径
def KVReader.read_values(): ...  文本: 按 paths + selector 最小读取属性值, 应用回退规则
def ResponsePlanner.compose_frame(): ...  文本: 依据 slots 与 compose_rules 生成“框架+占位”, 首轮不读取属性层

如何使用:
咨询/介绍: OrgIndexAgent.locate_agency → AgencyIndexAgent.load_agency_index → 意图→domain→entries 过滤→取 level3/4 键名→compose_frame→返回 框架+占位+路径 映射; 离线替换最小取值
方案/办理: OrgIndexAgent.locate_agency → AgencyIndexAgent.load_agency_index → 意图→domain→仅取必要段落→携带 user prompt 交 LLM 组织答案→（可选）离线替换

# 标题: Agent设计 / 工具清单与契约（以内存快照驱动）

工具清单 = ["locate_agency", "hydrate_agency", "index_locate", "index_get_paths_for_l3", "mem_read", "compose_reply", "plan_workflow"]
设计意图: "所有工具基于内存快照运行，避免磁盘 IO；LLM 仅在 compose_reply/plan_workflow 节点介入；工具实体集中维护在 OpenaiAgents/UnifiedCS/tools.py。"

def locate_agency(): ...  文本: 工具; 输入: agency_query|keywords; 输出: {agency_id, agency_name, agency_folder, index_rel}; 行为: 从 MemorySnapshot 的 org_index 视图匹配机构
def hydrate_agency(): ...  文本: 工具; 输入: agency_id 或 {agency_folder, index_rel}; 输出: 机构视图 (agency/domain_profiles/compose_rules/selectors/slots/entries/synonyms)
def index_locate(): ...  文本: 工具; 输入: intent|keywords|domain; 输出: {level3_candidates, compose_rules, selectors, slots}
def index_get_paths_for_l3(): ...  文本: 工具; 输入: {domain, level3_key}; 输出: 该 l3 下全部 level4 路径与占位集合（附路径标签）
def mem_read(): ...  文本: 工具; 输入: {paths, selector, lang?}; 输出: 路径对应的最小值集合，全部从 MemoryStore 读取
def compose_reply(): ...  文本: 工具(可配置 LLM=none，小预算); 输入: {frame: compose_rules[domain], slots, labels(l3/l4)}; 输出: “框架+占位+路径映射”字符串
def plan_workflow(): ...  文本: 工具(LLM 中预算); 输入: {segments, user_prompt, lang, llm_policies}; 输出: “方案类结构化答复”（步骤/注意事项等）


# 标题: 工具字段契约表（字段名对齐与返回结构）
```yaml
# 说明: 所有字段均使用 ASCII 标点与英文键名；未标注 "?" 的为必填；返回结构仅示意字段名与层级，不包含实现。

def locate_agency(): ...  字段契约
需求字段 = {
  "input": {
    "agency_query?": "string",
    "keywords?": "list[string]",
    "lang": "string"
  },
  "output": {
    "agency_id": "string",
    "agency_name": "string",
    "agency_folder": "string",
    "index_rel": "string"
  },
  "errors": [
    {"no_match": "未命中机构"}
  ]
}

def hydrate_agency(): ...  字段契约
需求字段 = {
  "input": {
    "agency_id?": "string",
    "agency_folder?": "string",
    "index_rel?": "string"
  },
  "output": {
    "agency": "dict",
    "domain_profiles": "dict",
    "compose_rules": "dict",
    "render_policy": "dict",
    "selectors": "dict",
    "slots": "dict",
    "entries": "list",
    "synonyms?": "dict"
  },
  "errors": [
    {"missing_index": "机构索引缺失/损坏"}
  ]
}

def index_locate(): ...  字段契约
需求字段 = {
  "input": {
    "intent": "consult|plan",
    "keywords": "list[string]",
    "domain?": "string"
  },
  "output": {
    "level3_candidates": "list[string]",
    "meta": {"slots": "dict", "compose_rules": "dict"}
  }
}

def index_navigator.find_paths(): ...  字段契约
需求字段 = {
  "input": {
    "domain": "string",
    "level3_key?": "string"
  },
  "output": {
    "key_structure": {
      "l3_list": "list[string]",
      "l4_map": "{l3_key: list[string]}"
    },
    "path_map": "{placeholder: path}",
    "labels?": "{key: readable_label}"
  }
}

def index_get_paths_for_l3(): ...  字段契约
需求字段 = {
  "input": {
    "domain": "string",
    "level3_key": "string"
  },
  "output": {
    "paths": "list[path]",
    "placeholders": "list[string]",
    "labels?": "{l4_key: readable_label}"
  }
}

def value_reader.read_values(): ...  字段契约
需求字段 = {
  "input": {
    "paths": "list[path]",
    "selector?": "string|list[string]",
    "strategy": "full",
    "lang?": "string"
  },
  "output": {
    "content_bundle": "list[{path: string, key: string, value: any, lang?: string}]"
  }
}

def compose_reply.llm_frame(): ...  字段契约
需求字段 = {
  "input": {
    "key_structure": "{l3_list, l4_map}",
    "frame": "string",
    "render_policy": "dict",
    "slots": "dict",
    "lang": "string"
  },
  "output": {
    "text_frame": "string",
    "placeholders": "{placeholder: path}",
    "used_paths": "list[path]",
    "domain": "string",
    "l3_keys": "list[string]"
  },
  "constraints": [
    "禁止输出属性值",
    "严格遵守 render_policy 与 brevity"
  ]
}

def planner.llm_plan(): ...  字段契约
需求字段 = {
  "input": {
    "content_bundle": "list[object]",
    "user_prompt": "string",
    "lang": "string",
    "llm_policies": "dict"
  },
  "output": {
    "final_text": "string",
    "used_paths": "list[path]"
  },
  "constraints": [
    "仅基于提供的完整键值集合组织答案",
    "保持简短, 以步骤/要点为主"
  ]
}

def pricing.aggregate(): ...  字段契约
需求字段 = {
  "input": {
    "fields": "[amount.value, currency, discounts?]",
    "group_by": "[level3_name]",
    "round": 2,
    "locale": "zh_CN|en_US"
  },
  "output": {
    "items": "[{l3, l4, value, display}]",
    "totals": "{by_l3: list[{l3,total}], grand_total: number}",
    "notes?": "list[string]"
  },
  "constraints": [
    "跨币种分别汇总, 不自动换汇"
  ]
}
```

# 标题: Agent设计 / 工作流（咨询/介绍 与 方案/办理）

咨询/介绍（LLM 低开销）:
1. IntentAgent.classify → 判定为咨询/介绍, 解析关键词与 agency 候选, 输出 {lang,intent,keywords,agency_candidates}; 未命中则用欢迎语模板引导提供业务语义。
2. OrgIndexAgent.locate_agency → 从内存 org_index 视图返回 {agency_id, agency_folder, index_rel} + 导航说明 nav_hints。
3. AgencyIndexAgent.hydrate_agency → 取得机构级内存视图。
4. index_locate / index_navigator.find_paths → 依据 intent/keywords 与 domain_profiles/synonyms 列出 l3 候选与该 l3 的 l4 子键结构（仅键名与标签）。
5. compose_reply.llm_frame（LLM 小预算）→ 输入 {键名结构+frame+render_policy+slots+lang} 生成“框架+占位+路径映射”，禁止属性值。
6. OfflineReplacer.replace_placeholders（离线）→ 按 selectors 读取所需属性值并替换占位 → 输出最终回复。

方案/办理（LLM 中预算）:
1. IntentAgent.classify → 判定为方案/办理, 解析关键词。
2. OrgIndexAgent.locate_agency → 定位机构(内存)。
3. AgencyIndexAgent.hydrate_agency → 取得机构级内存视图。
4. index_locate / index_navigator.find_paths → 选择 domain 与 l3（必要时多 l3），并确定需要的跨文件路径集合。
5. value_reader.read_values(strategy="full") → 读取上述路径的“完整所需键值集合”（可跨文件）。
6. planner.llm_plan（LLM 中预算）→ 以 {完整键值集合 + user prompt + lang} 生成方案答复（步骤/注意事项）。
7. （可选）OfflineReplacer.replace_placeholders → 若仍需嵌值或补足细节，再行替换。

# 标题: 读取策略 / 咨询与方案（白名单与限制）

设计意图: "咨询类由 LLM 基于‘键名结构’组织‘框架+占位+路径映射’，不读取属性值；方案类直接读取‘完整所需键值集合’后由 LLM 生成最终答复；金额/个人信息等只允许按选择器替换，不做语义推断。"

咨询类（框架白名单）: 允许除属性层(level5+)之外的一切键名参与框架组织；属性层值仅在 selectors 指定时由离线替换；LLM 不得直接输出属性值、不得语义改写属性。

方案类（内容白名单）: 允许读取涉及回答所需的“完整键值集合”（可跨文件）；LLM 在此基础上组织步骤/要点；严禁凭空扩展与外推。

金额/个人信息: 仅允许按 selectors 替换（如 amount.display 或 value+currency），不得由 LLM“推断/改写/扩展”。

# 标题: Agent设计 / 会话状态与缓存（三层）

会话状态 = {"agency_id", "kb_id?", "agency_folder", "index_rel", "domain", "level3_key", "paths", "slots", "selector", "lang", "llm_policy", "non_business_count", "locked_until"}
缓存策略 = {"org_index": "mtime 失效; 会话级只读", "agency_index": "mtime 失效; 会话级只读", "kv_value": "按 (path+selector+lang) 短 TTL"}
设计意图: "最小状态贯穿 Org→Dept→Reply 全链路；禁用全量值缓存，防止 token 与内存膨胀。"

# 标题: Agent设计 / LLM 策略与流式

遵守 index.yaml.llm_policies: IntentAgent/consult_frame 均启用 LLM(小预算); planner 启用 LLM(中预算)。运行期所有取数走内存，不访问磁盘。IntentAgent 自动检测用户语言；所有节点使用用户语言输出。
handoff 策略: 咨询/介绍 → stop_on_first_tool（compose_reply.llm_frame 产出即停）；方案/办理 → run_llm_again（必要时允许多轮组织）。
流式: 各 LLM 节点支持流式输出；如流式出错，立即抛异常（不降级、不兜底）。

# 标题: Agent设计 / 错误与回退

未命中机构: 返回“知识库未覆盖该机构”, 记录 org.stats.missing_index。
机构索引缺失/损坏: 返回“该机构索引暂不可用”, 记录 org.stats.stale_index。
选择器无值: 按回退链继续; 若仍无则降级为不含该占位的回复并记录 stats.missing。
权限/路径越界: KVReader 拒绝非 kb_root 路径并告警; 会话清理敏感状态。

# 标题: Agent设计 / 观测与日志（richlogger + token 计数）
from rich.logging import RichHandler  "依赖锚点: 控制台彩色日志"
import logging  "依赖锚点: 标准日志接口, 供封装"

设计意图: "为每一轮对话与工具调用提供清晰、降噪、可追溯的观测; 输出 DEBUG 级到 Console 与 File; 结合 OpenAI Agents SDK/Responses API 的 usage 做 Token 报告。"

需求字段 = {
"log.console": {"enabled": true, "level": "DEBUG", "rich": true},
"log.file": {"enabled": true, "level": "DEBUG", "dir": "logs/agents/%Y-%m-%d", "rotate_mb": 10, "backup": 14, "format": "jsonl"},
"log.fields": ["timestamp", "session_id", "trace_id", "agency_id", "kb_id", "agent", "tool", "step", "elapsed_ms", "status", "message", "memory.bytes_approx", "memory.entries_count"],
"token.fields": ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "reasoning_tokens?", "total_tokens"],
"redact": {"enabled": true, "patterns": ["phone", "email", "id_number"], "strategy": "mask_or_hash"},
"sampling_ratio": 1.0
}

def RichLogger.setup(): ...  文本: 初始化 Console/File Handler; Console 使用 RichHandler; File 使用 Rotating 或按日目录 JSONL
def RichLogger.event(): ...  文本: 关键节点统一打点; 接收 kwargs→结构化; 支持降噪合并
def TokenMeter.start_turn(): ...  文本: 回合开始; 初始化 turn_id/trace_id; 清零 usage 聚合
def TokenMeter.stop_turn(): ...  文本: 回合结束; 汇总 usage→TokenReport; Console 打印; File 追加
def ToolWrapper.with_logging(): ...  文本: 为 function_tool 增加 before/after 钩子; 记录耗时/异常/子用量
def BudgetGuard.check_and_warn(): ...  文本: 对比 llm_policies 预算; 近阈值 WARN; 超阈值 ERROR 并短路

二级嵌套:
关键节点: IntentAgent.classify_and_greet, OrgIndexAgent.locate_agency, AgencyIndexAgent.load_agency_index, index_locate, index_get_paths_for_l3, mem_read, compose_reply, plan_workflow, LockManager 状态变更
降噪策略: 合并重复调用; 内容截断(首尾 80); Console 仅摘要; File 保留 hash 与必要字段
安全: 脱敏启用; 拒绝非 kb_root 路径; 不记录密钥

如何使用:
AgentsGateway.dispatch → TokenMeter.start_turn → 业务链路(工具经 ToolWrapper.with_logging 包装; 全部读内存) → TokenMeter.stop_turn → RichLogger.event 写回合汇总

agent如何读取:
在 triage/intro_frame/planner 的 Runner.run/stream 返回对象中抽取 usage 累加; 若存在 handoff, 多步累积后统一汇总

# 标题: Agent设计 / 配置与开关（日志与预算）

需求字段 = {
"settings.logging.enabled": true,
"settings.logging.redact": true,
"settings.logging.rich_console": true,
"settings.logging.file_debug": true,
"settings.logging.log_dir": "logs/agents",
"settings.budget.triage_max_tokens": 256,
"settings.budget.intro_frame_max_tokens": 256,
"settings.budget.planner_max_tokens": 4096
}
设计意图: "以最小配置驱动观测与预算; 所有数值可由环境变量覆盖, 部署时无需改代码。"

# 标题: 集成设计 /.env 配置清单（手工维护, AI 禁止修改）

需求字段 = {
"USE_AGENTS": "true|false; 是否启用 AgentsBridge 适配层 (默认 true)",
"MODEL": "agents|<legacy>; 设为 agents 以走新链路",
"BASE_DIR": "Kobe; 仓库根; 所有路径相对该根解析",
"ORG_INDEX_FILE": "AckowleageBase/AckowleageBase_index.yaml",
"TELEGRAM_BOT_TOKEN": "<BotFather token>; webhook/polling 共用",
"WEB_HOOK": "https://<ngrok 或公网域名>; 留空则使用 polling",
"LOG_DIR": "logs/agents",
"LLM_TRIAGE_MODEL": "responses:mini",
"LLM_INTRO_MODEL": "responses:mini",
"LLM_PLANNER_MODEL": "responses:standard",
"LLM_TRIAGE_MAX_TOKENS": "256",
"LLM_INTRO_MAX_TOKENS": "256",
"LLM_PLANNER_MAX_TOKENS": "4096",
"BUSINESS_LOCK_THRESHOLD": "5",
"BUSINESS_LOCK_SECONDS": "3600",
"APP_NAME": "Kobe",
"MEMORY_WARN_MB": "1536",
"MEMORY_ERROR_MB": "2048",
"RICH_CONSOLE": "true",
"FILE_DEBUG": "true",
"REDACT": "true"
}
设计意图: "一次性复制到 .env 即可运行; 开关与预算独立于代码, 便于后续调优。"

# 标题: 配置设计 / 模型与 Prompt 外置 YAML（给开发AI）

需求字段 = {
"models.yaml": "Config/models.yaml",  # 相对 BASE_DIR=Kobe
"prompts.yaml": "Config/prompts.yaml"
}
设计意图: "将模型与节点 Prompt 从代码中拆出, 实现按节点/机构可插拔配置与成本/效果独立调优。"

models.yaml 结构:
defaults = {
  "triage": {"model": "responses:mini", "temperature": 0.2, "max_tokens": 256, "tool_use_behavior": "default"},
  "intro_frame": {"model": "responses:mini", "temperature": 0.2, "max_tokens": 256, "tool_use_behavior": "default"},
  "planner": {"model": "responses:standard", "temperature": 0.3, "max_tokens": 4096, "tool_use_behavior": "default"}
}
agency_overrides? = {
  "bi": {"planner": {"model": "gpt-5", "temperature": 0.3, "max_tokens": 4096}}
}
tool_overrides? = {
  "compose_reply": {"model": "none", "reason": "咨询类首轮不需 LLM, 仅框架+占位"},
  "mem_read": {"model": "none"},
  "triage": {"tool_use_behavior": "stop_on_first_tool"}
}
semantics = {
  "model": "字符串; 可为具体提供商型号(gpt-4o-mini, gpt-5 等)或逻辑组(responses:mini|responses:standard)",
  "none": "特殊值; 表示该工具/阶段不调用 LLM",
  "tool_use_behavior": "default|stop_on_first_tool; compose_reply 建议 stop_on_first_tool 以最小开销",
  "fallback": "tool_overrides > agency_overrides > defaults; 若仍无 → 按 index.yaml.llm_policies"
}
校验与回退 = {
  "validate_required": ["model"],
  "validate_ranges": {"temperature": [0.0, 2.0], "max_tokens": [1, 32768]},
  "normalize_alias": {"responses:mini": ["mini"], "responses:standard": ["standard"]}
}

prompts.yaml 结构:
triage = {
  "system": "你是企业客服意图分流与欢迎代理, 需检测用户语言(lang)与意图(intent ∈ {咨询, 方案}), 并返回极简确认。",
  "instruction": "判定业务相关性, 超过阈值触发锁定提示, 否则返回简短确认; 不生成冗长解释。"
}
intro_frame = {
  "system": "输出品牌欢迎与服务域边界; 语言=用户语言; 遵循简短风格; 禁止长段。",
  "instruction": "使用 {brand} 与 {tail_languages} 生成一行欢迎 + 一行多语言可用提示。"
}
consult_frame = {
  "system": "你是‘咨询框架器’，只基于提供的键名结构(l3/l4)+render_policy+compose_rules.frame 组织‘框架+占位+路径映射’；禁止输出属性值；严格简短。",
  "instruction": "根据 {key_structure} 与 {render_policy} 选择 {max_items} 个要点；按 {frame} 生成文本，使用 {slots} 占位；如超限，用 {ellipsis} 收尾；不得臆造键。"
}
planner = {
  "system": "根据内存读取到的完整所需键值集合(content_bundle)与用户提示词, 组织办理/方案类简明答复; 禁止编造; 严格简短。",
  "instruction": "优先输出步骤与注意事项, 控制在 {brevity} 内。"
}
placeholders = {
  "brand": "Kobe",
  "tail_languages": ["English", "中文", "Español", "العربية", "한국어"],
  "language": "auto",
  "brevity": "<=3 sentences or <=5 bullets"
}

def ModelResolver.select(): ...  文本: 选择模型的优先级=tool_overrides > agency_overrides > defaults; 若缺失则回退 llm_policies
def ModelResolver.validate(): ...  文本: 校验字段/范围; 解析 "none" 语义; 输出标准化配置
def PromptRegistry.get(): ...  文本: 读取 prompts.yaml 的节点文案, 返回 {system, instruction}
def PromptCompiler.render(): ...  文本: 用 placeholders 与会话 language/brand 渲染最终提示词

如何使用:
AgentsGateway.dispatch_stream 在每个节点调用 ModelResolver.select 与 PromptRegistry.get/PromptCompiler.render；在 .env 修改 LLM_* 即可覆盖默认值；开发阶段通过编辑 YAML 实施细粒度调优。

agent如何读取:
language 由 IntentAgent 检测并贯穿; planner 节点从 models.yaml 读出模型与温度, 并按 prompts.yaml 渲染系统/任务指令; compose_reply 节点默认 responses:mini 以控制成本。

# 标题: 集成设计 / 最小注入示例（锚点与行号, 不改框架）

需求字段 = {
"文件": {
  "TelegramBot/bot.py:893": "if __name__ == '__main__': 入口",
  "TelegramBot/bot.py:895": "ApplicationBuilder().build() 构建处",
  "TelegramBot/bot.py:959": "application.run_webhook(...)",
  "TelegramBot/bot.py:961": "application.run_polling(...)"
},
"注入": {
  "config.get_robot_agents": "当 USE_AGENTS=true 或 MODEL=agents 时返回 AgentsBridge 实例",
  "AgentsBridge.ask_stream_async": "保持增量生成器契约不变, 供 getChatGPT 直接消费",
  "Bootstrap.memory_preload": "进程启动时加载 MemorySnapshot（可挂 post_init 钩子）",
  "AgentsGateway.attach_snapshot": "将 snapshot 注入; 所有工具走内存"
}
}
设计意图: "仅替换‘向模型发问’层为 AgentsBridge; 其它启动与 handlers 不变; 方便快速回归。"

如何使用:
不改 ApplicationBuilder 与 handlers; 在 config.get_robot 旁实现 get_robot_agents；在 post_init 或入口前调用 Bootstrap.memory_preload 与 AgentsGateway.attach_snapshot；确保 .env USE_AGENTS=true。

# 标题: 集成设计 / 启动预热与健康检查（V1.0 不支持热更新）

设计意图: "进程启动一次性加载内存快照，运行期只读内存；V1.0 不支持热更新；V1.1 再评估热更新方案。"

def Bootstrap.memory_preload(): ...  文本: 启动时调用 MemoryLoader.load_all; 生成 MemorySnapshot 并注入 AgentsGateway
def AgentsGateway.attach_snapshot(): ...  文本: 将 MemorySnapshot 提供给所有工具; 拒绝文件 IO
def Healthz.memory(): ...  文本: /healthz/memory 输出 {snapshot_id, entries_count, bytes_approx, last_indexed_at}

如何使用:
进程启动 → Bootstrap.memory_preload → AgentsGateway.attach_snapshot → TelegramBot 正常接入

边界与路径:
BASE_DIR = "Kobe"（项目根）; 所有索引路径均为相对 BASE_DIR 的相对路径; 禁止使用绝对路径; 运行环境由 Kobe/TelegramBot/config.py 通过 find_dotenv(usecwd=True) 与模块 __file__ 推导 .env 与 BASE_DIR（无需依赖 FastAPI/uvicorn）

agent如何读取:
所有工具仅从内存读取; 如 MemoryHealth 报错或 snapshot 不可用, 返回临时不可用提示并记录告警

# 标题: Agent设计 / 意图与欢迎、业务域限制与锁定（LLM 常驻）

设计意图: "LLM 始终对话；当意图不清或非业务时，最小反馈并约束交互；连续 N 次非业务后锁定 1 小时并返回倒计时。触发一次业务即解冻。"

def IntentAgent.classify_and_greet(): ...  文本: 判定意图并返回简短欢迎/确认; 不清晰时提醒“仅用于业务咨询”并请求澄清
def SessionPolicy.enforce_business_scope(): ...  文本: 递增 non_business_count; 达阈值设置 locked_until; 写入会话状态
def LockManager.is_locked(): ...  文本: 判断当前是否处于锁定期
def LockManager.remaining_time(): ...  文本: 计算剩余锁定时间(秒)
def CountdownResponder.reply_remaining_lock(): ...  文本: 返回固定文案 "尝试次数过多，请{countdown}再试。"; 禁止进入后续链路

如何使用:
每条用户消息到达 → 若 LockManager.is_locked → CountdownResponder.reply_remaining_lock（{countdown} 为剩余时间简短描述，例如“59分20秒”）；否则 IntentAgent.classify_and_greet；若非业务 → SessionPolicy.enforce_business_scope 并返回简短提示；若为业务 → 进入 OrgIndexAgent/AgencyIndexAgent 流程。

# 标题: Agent设计 / 回复风格与长度约束（言简意赅）

设计意图: "所有回复默认简短、直接、指向性强；禁止长篇大论；咨询类仅描述‘怎么做’，方案类仅呈现必要步骤与注意事项。"

def Guardrails.enforce_brevity(): ...  文本: 约束回复长度(如 ≤3 句或 ≤5 条要点); 禁止无关寒暄
def ResponseStyle.apply(): ...  文本: 应用精简风格与术语规范; 优先输出步骤/要点; 避免段落型长文

# 标题: 集成设计 / TelegramBot 改造与 index.yaml 对接
from aient.core.request import get_payload  "锚点: Kobe/TelegramBot/ChatGPT-Telegram-Bot/aient/aient/core/request.py"
from aient.core.request import prepare_request_payload  "锚点: 同上"
from aient.core.response import fetch_response, fetch_response_stream  "锚点: Kobe/TelegramBot/ChatGPT-Telegram-Bot/aient/aient/core/response.py"

设计意图: "以最小侵入接管 GPT 分支；AgentsGateway 使用 index.yaml 与内存快照驱动工具链；保持上游接口与流式事件不变。" 所以 def AgentsGateway.dispatch(): ... 然后 def AgentsAdapter.convert_to_unified_response(): ...

def AgentsGateway.dispatch(): ...  文本: 注册 tools, 路由 locate_agency/mem_read/compose_reply, 消费内存快照; 依据 agency_id/kb_id 选择具体 agency 视图
def AgentsAdapter.convert_to_unified_response(): ...  文本: 将 Responses API 输出适配为现有统一事件结构

如何使用:
在 config.get_robot 旁新增 get_robot_agents 分支返回 AgentsBridge（当 USE_AGENTS=true 或 MODEL=agents）; models/chatgpt 等转义层保持不变; response 层复用既有统一事件结构与流式输出; 会话中携带 agency_id/kb_id 确保跨机构隔离

```
# 标题: 文件架构 / V1 路径与最小侵入范围（UnifiedCS）
```python
需求字段 = {
"BASE_DIR": "Kobe",
"禁止": ["绝对路径", ".env 非人工修改"],
"只读(运行期)": ["AckowleageBase/**", "Config/*.yaml"],
"可写(运行期)": ["logs/agents/%Y-%m-%d/*.jsonl"],
}

# 统一入口与编排（不使用 src；集中在 UnifiedCS/）
"Kobe/OpenaiAgents/UnifiedCS/bridge": "与 TelegramBot 的 ask_stream_async 契约适配（AgentsBridge）",
"Kobe/OpenaiAgents/UnifiedCS/gateway": "业务编排与路由：triage → 咨询 compose_reply / 方案 mem_read+planner",
"Kobe/OpenaiAgents/UnifiedCS/bootstrap": "启动预热与快照注入：memory_preload、attach_snapshot",

# 内存知识库与读取
"Kobe/OpenaiAgents/UnifiedCS/memory": "加载 org/agency index 与 KB → MemorySnapshot/Store/Health；只读，禁绝磁盘 IO",
"Kobe/OpenaiAgents/UnifiedCS/aggregators": "确定性聚合器（V1: pricing 聚合）",
"Kobe/OpenaiAgents/UnifiedCS/compose": "首轮‘框架+占位+路径’渲染，应用 render_policy 与 compose_rules",

# 模型与提示词配置
"Kobe/OpenaiAgents/UnifiedCS/config": "ModelResolver(select/validate)、PromptRegistry/PromptCompiler(placeholders 渲染)",

# 观测与用量
"Kobe/OpenaiAgents/UnifiedCS/logging": "richlogger(Console/File JSONL 降噪脱敏)、token_meter(聚合 Agents SDK usage)",

# 轻量测试（可选）
"Kobe/OpenaiAgents/UnifiedCS/tests": "聚合器/渲染策略/选择器的轻量单测（可延后）",

# 其余必需路径（保持原位）
"Kobe/AckowleageBase/AckowleageBase_index.yaml": "顶层 org index：agencies、agency_synonyms?、routing_table?",
"Kobe/AckowleageBase/<agency>/<agency>_index.yaml": "机构级 index：domain_profiles、compose_rules、render_policy、selectors、slots、entries、pricing.aggregate",
"Kobe/Config/models.yaml": "模型选择 defaults/agency_overrides/tool_overrides 与 tool_use_behavior（允许 model=none）",
"Kobe/Config/prompts.yaml": "triage/intro_frame/planner 的 system/instruction 与 placeholders",
"Kobe/logs/agents/%Y-%m-%d": "运行期日志 JSONL（token 用量与关键打点）",

# 最小侵入改动点（仅两处）
"Kobe/TelegramBot/config.py": "新增 get_robot_agents 分支（USE_AGENTS=true 或 MODEL=agents 时返回 AgentsBridge）; 保留 get_robot",
"Kobe/TelegramBot/bot.py": "在既定钩点调用 UnifiedCS/bootstrap 的 memory_preload 与 attach_snapshot；不改 handlers/启动范式",

设计意图: "把新增能力全部收纳到 UnifiedCS，避免与 OpenAI SDK 源码/例子目录混合，便于 debug 与演进；其余工程仅做两点最小注入。"
```

# 标题: 官方对齐与变更控制（Responses API + Agents SDK）
```python
# 真源与版本
需求字段 = {
"truth_sources": [
  "Agents SDK Streaming: Runner.run_streamed/事件",
  "Agents SDK Usage: result.context_wrapper.usage",
  "Agents SDK Running agents: run/run_streamed 停止条件",
  "Agents SDK Handoffs: stop_on_first_tool/handoff 行为"
],
"AGENTS_SDK_REF": "<tag-or-commit>; .env 锁定，升级需走测试闸门",
"policy": "仅以官方文档与仓库为唯一真源，第三方信息不入规范"
}

# 事件/字段契约（桥接层输出，避免字段漂移）
Streaming = {
  "input": ["text|input_items", "convo_id", "lang", "llm_policy_key"],
  "map_events": {
    "response.output_text.delta": "text_delta  # 直接拼入增量缓冲，供 Telegram 流式渲染",
    "run_item_stream_event": "tool_completed  # 仅日志打点，不上屏"
  },
  "finalize": ["result.final_output", "usage=requests|input_tokens|output_tokens|total_tokens"],
  "on_error": "流式解析/网络/未知事件 → 立即抛出异常；不降级、不兜底"
}

Tools = {
  "declaration": "function_tool + 类型注解（pydantic 校验）; 文档仅给出签名与字段语义，不含实现",
  "json_strict": "工具参数严格 JSON；返回体语义在小节‘工具清单’已描述"
}

# 测试闸门（三件套，UnifiedCS/tests/；V1 就位）
Tests = {
  "test_gateway.py": "覆盖 AgentsGateway.dispatch_stream 的 Responses API 流式契约 (raw_response_event→text_delta)",
  "test_memory_loader.py": "校验 MemoryLoader.load_all/MemorySnapshotView 能从 AckowleageBase_index.yaml 构建快照 (bi 实例)",
  "test_tools.py": "对 locate_agency/index_locate/mem_read/compose_reply 等 function_tool 做 Pydantic 契约验证",
  "test_bridge.py": "保证 AgentsBridge.ask_stream_async → TelegramMarkdown 适配符合 BaseLLM 生成器语义",
  "test_live_agents.py": "真实调用 OpenAI Responses API，校验 ToolContext/toolset 流程 (需 OPENAI_API_KEY)",
  "test_telegram_api.py": "验证 BOT_TOKEN/setWebhook/getMe 联通性 (需 Telegram 外网/WEB_HOOK)"
}
# 升级流程（可控跟新，非盲追新）
Upgrade = {
  "detect": "scripts/check_agents_sdk_ref.py 提示上游新 tag",
  "branch": "新分支拉取更新 → 跑三件套 → 全绿后更新 .env:AGENTS_SDK_REF 与文档锚点日期",
  "rollback": "若不兼容，保持旧 ref；待修复验证后再升级"
}

设计意图: "将‘跟官方对齐’转为可执行契约与测试，避免因知识截断或个人记忆导致的偏差；任何接口变化先由闸门卡住再进入集成。"
```