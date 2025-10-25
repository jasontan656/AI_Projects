Tech_Decisions:
  intent: "UserProfilingFieldClassification"
  count_3d: "004"
  target_dir: "D:/AI_Projects/CodexFeatured/DevPlans/004_UserProfilingFieldClassification"
  standards:
    - "遵循 CodexFeatured/Common/BackendConstitution.yaml（Python 3.10，异步 I/O 优先，统一日志 RichLogger）"
    - "遵循 CodexFeatured/Common/CodeCommentStandard.yaml（模块 docstring + 叙事式行内注释）"
    - "参考 CodexFeatured/Common/BestPractise.yaml 官方链接进行依赖选型与验证"
  reuse_modules:
    - module: "Kobe/SharedUtility/RichLogger"
      apis: ["init_logging", "install_traceback", "get_console"]
      usage_example: |
        from Kobe.SharedUtility.RichLogger import init_logging, install_traceback
        install_traceback()
        init_logging(level="INFO")
    - module: "Kobe/SharedUtility/TaskQueue"
      decision: "本需求为一次性离线工具，默认不引入队列。若后续需要批量/长流程，可复用 registry.send_task 提交分类作业。"
      usage_example: |
        from Kobe.SharedUtility.TaskQueue.registry import send_task
        send_task("visa.field_classify", payload={"field_key": "UserHomeAddress"})
  new_dependencies:
    - name: "openai"
      version: ">=1.50.0"
      reason: "官方 Python SDK，支持 gpt-4o-mini 等模型，用于小样本字段画像真/假/人工复核(verify)三值分类。"
      official_refs:
        - "https://platform.openai.com/docs/api-reference"
        - "https://github.com/openai/openai-python"
    - name: "sqlparse"
      version: ">=0.5.0"
      reason: "解析 SQL DDL（CREATE TABLE）以提取表/字段结构，纯 Python、零依赖。"
      official_refs:
        - "https://sqlparse.readthedocs.io/"
    - name: "pydantic"
      version: ">=3.0.0"
      reason: "输入/输出与中间 JSON 的数据模型校验，满足 BackendConstitution 对 v3 的约束。"
  architecture:
    - "同步脚本为主 + 受控并发（后续可无缝切换为异步 aio+队列）。"
    - "输入固定为 D:/AI_Projects/Visa/visa_db.sql（只读），输出固定路径 JSON/Markdown。"
    - "幂等性：以 field_key+sample_hash 去重，避免重复 LLM 调用。"
    - "安全：日志屏蔽原始 PII，Markdown 仅展示脱敏样本。"

Step 1:
  title: 文档状态检查与目标定位
  sub_steps:
    - "运行: python CodexFeatured/Scripts/CodebaseStructure.py（写回 CodexFeatured/Common/CodebaseStructure.yaml）"
    - "读取: CodexFeatured/Common/CodebaseStructure.yaml，确认 Kobe/ 目录结构生成成功"
    - "在 D:/AI_Projects/CodexFeatured/DevPlans 下查找包含 DemandDescription.md 的子目录，按修改时间倒序选择最新"
    - "从目标 DemandDescription.md 首行解析 INTENT_TITLE_2_4=UserProfilingFieldClassification, COUNT_3D=004"
    - "设置 target_dir=D:/AI_Projects/CodexFeatured/DevPlans/004_UserProfilingFieldClassification"
    - "设置 target_tasks_path=D:/AI_Projects/CodexFeatured/DevPlans/004_UserProfilingFieldClassification/Tasks.md"
    - "读取 Kobe/index.yaml 及其 sub_indexes（SharedUtility/*, TempUtility/*）构建可复用模块清单"
  acceptance:
    - "已生成/更新 CodebaseStructure.yaml 且包含根条目 Kobe/"
    - "成功锁定 004_UserProfilingFieldClassification 作为目标目录"
    - "解析得到 COUNT_3D=004 与 INTENT_TITLE_2_4=UserProfilingFieldClassification 并记录到 Tech_Decisions"

Step 2:
  title: 规范加载与技术选型确认
  sub_steps:
    - "通读 CodexFeatured/Common/BackendConstitution.yaml：运行时 Python3.10、Pydantic v3、异步优先、统一日志 RichLogger"
    - "通读 CodexFeatured/Common/CodeCommentStandard.yaml：为后续脚本补充模块 docstring 与关键行注释"
    - "通读 CodexFeatured/Common/BestPractise.yaml 中官方链接，确认 openai 与 sqlparse 选型"
    - "将本文件 Tech_Decisions 章节与上述规范对齐（必要时修订本文件）"
  acceptance:
    - "Tech_Decisions 与三份规范一致（版本/依赖/注释要求明确）"
    - "如有修订，已在本文件更新并保存"

Step 3:
  title: 依赖清单更新（独立步骤）
  sub_steps:
    - "打开: Kobe/Requirements.txt"
    - "追加如下行（如已存在则跳过）：openai>=1.50.0, sqlparse>=0.5.0, pydantic>=3.0.0"
    - "执行: python -m venv Kobe/.venv; 激活后 pip install -r Kobe/Requirements.txt"
  acceptance:
    - "Kobe/Requirements.txt 成功包含三项新依赖"
    - "pip 安装成功，无冲突（pydantic 主版本为 3）"

Step 4:
  title: 复用统一日志模块并创建工作脚本骨架
  sub_steps:
    - "在 Kobe/TempUtility/VisaDBOperation/ 下新建脚本: field_ops.py"
    - "脚本顶部接入: from Kobe.SharedUtility.RichLogger import init_logging, install_traceback; install_traceback(); init_logging('INFO')"
    - "定义 Pydantic v3 数据模型: SchemaField, SampleItem, FieldDecision, FieldRecord（含字段与 verify/reason/confidence）"
  acceptance:
    - "field_ops.py 存在并可被 python 直接运行（不报错）"
    - "日志初始化后异常栈为统一渲染样式"

Step 5:
  title: SQL 结构解析器（提取库/表/字段）
  sub_steps:
    - "实现函数 parse_schema_from_sql(sql_path) -> list[SchemaField]，使用 sqlparse 解析 CREATE TABLE 语句"
    - "解析到的字段以 'database.table.column' 形式生成 field_path，规范化为 PascalCase 的 field_key"
    - "将结构初稿打印到控制台并统计字段总数"
  acceptance:
    - "从 D:/AI_Projects/Visa/visa_db.sql 成功提取出 >=1 个表与字段"
    - "field_key 与 field_path 均非空且数量一致"

Step 6:
  title: 样本采样与脱敏（生成中间 JSON）
  sub_steps:
    - "若可连接真实数据库，则针对每个字段采样至多 20 条代表性值；否则构造占位样本并注明 'pii_masked=true'"
    - "实现脱敏规则：邮箱/手机号/证件号做掩码；地址取前后片段 + 占位符"
    - "输出中间文件: D:/AI_Projects/Kobe/TempUtility/VisaDBOperation/field_samples.json（UTF-8, 无 BOM）"
  acceptance:
    - "field_samples.json 存在，符合需求文档示例结构，任意样本不暴露原始 PII"
    - "每字段 samples 条数 1..20 之间，含 sample_hash 与 created_at"

Step 7:
  title: 三值分类器（LLM 驱动）
  sub_steps:
    - "在 field_ops.py 中实现 classify_field(sample: SampleItem) -> FieldDecision，模型默认从环境变量 OPENAI_MODEL（默认 gpt-4o-mini）读取"
    - "并发控制：同一进程内限制同时请求数<=5，重复 (field_key+sample_hash) 命中本地缓存直接返回"
    - "对每个字段聚合 samples 的投票结果，生成最终 verify=true|false|verify 及 reason/avg_confidence"
  acceptance:
    - "对 10 个示例字段运行分类，产生稳定的三值结论"
    - "缓存生效：重复运行时 API 调用次数显著减少（日志可见）"

Step 8:
  title: 结果汇总与 Markdown 报告生成
  sub_steps:
    - "生成 D:/AI_Projects/Kobe/TempUtility/VisaDBOperation/VisaDatabseDietPlan.md"
    - "报告结构：概要统计（true/verify/false 计数与占比）+ 按表归档的字段明细（含 samples 脱敏片段与最终判定）"
    - "在报告页首注明输入/输出路径、运行时间、版本信息"
  acceptance:
    - "VisaDatabseDietPlan.md 存在且可读，包含统计小结与字段明细两部分"
    - "报告中不包含任何可反向识别的 PII"

Step 9:
  title: 性能与稳定性验证
  sub_steps:
    - "以 50 个字段为基准集进行一次完整跑通，记录总耗时与平均每字段耗时"
    - "校验并发上限与速率限制未触发服务端限流（无 429/5xx），失败自动重试<=3 次"
    - "验证幂等性：删除本地缓存后与保留缓存分别跑一次，比较调用次数差异>=50%"
  acceptance:
    - "50 字段完整运行<=10 分钟；零未处理异常；失败率<1% 且均已重试覆盖"
    - "缓存命中显著减少 API 次数（对比日志）"

Step 10:
  title: 交付与 DoD 确认
  sub_steps:
    - "确认输出文件：field_samples.json 与 VisaDatabseDietPlan.md 路径与编码符合要求"
    - "脚本内包含模块 docstring 与关键路径行注释，遵循 CodeCommentStandard"
    - "如未来扩展为批量任务：在 Kobe/SharedUtility/TaskQueue/registry.py 基础上编写 task 包装（可选）"
  acceptance:
    - "DoD 满足：功能（解析/采样/分类/汇总）、结构（数据模型/缓存/并发）、接口（可参数化模型名/采样数）、与交付物（JSON/Markdown）"
    - "本 Tasks.md 与 Tech_Decisions 一致；路径均为正斜杠风格"

