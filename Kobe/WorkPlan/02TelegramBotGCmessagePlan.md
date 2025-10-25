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

