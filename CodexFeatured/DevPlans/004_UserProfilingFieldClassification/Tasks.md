meta:
  count_3d: "004"
  intent_title_2_4: "UserProfilingFieldClassification"
  target_dir: "D:/AI_Projects/CodexFeatured/DevPlans/004_UserProfilingFieldClassification"
  target_demand_path: "D:/AI_Projects/CodexFeatured/DevPlans/004_UserProfilingFieldClassification/DemandDescription.md"
  generated_at: "2025-10-11T00:00:00Z"
  author: "DevPipelineGeneration"

tech_decisions:
  复用模块清单:
    - module: "Kobe/SharedUtility/RichLogger"
      provides:
        - "__init__.py: init_logging()"
        - "__init__.py: install_traceback()"
        - "__init__.py: get_console()"
      usage: "统一初始化日志与异常堆栈渲染，用于扫描与判定流程。"
      调用方式示例: "from Kobe.SharedUtility.RichLogger import init_logging, install_traceback; init_logging(); install_traceback()"
    - module: "Kobe/SharedUtility/TaskQueue"
      provides:
        - "app.py: app (Celery 应用实例)"
        - "tasks.py: demo_long_io, demo_sharded_job (参考示例)"
        - "schemas.py: TaskStart/TaskStatus/TaskResult (Pydantic v3)"
      usage: "复用 Celery 应用与任务路由模式，新增本需求的判定任务。"
      调用方式示例: "from Kobe.SharedUtility.TaskQueue.app import app as celery_app; r=celery_app.AsyncResult(task_id); r.ready()"
    - module: "Kobe/SharedUtility/TaskQueue/repository/mongo.py"
      provides:
        - "coll_raw_payload()"
        - "coll_task_result()"
        - "ensure_indexes()"
      usage: "落库存放原始提交载荷与判定结果，构建必要索引。"
      调用方式示例: "from Kobe.SharedUtility.TaskQueue.repository.mongo import coll_raw_payload, coll_task_result; coll_raw_payload().insert_one({...})"
    - module: "Kobe/routers/task.py"
      provides:
        - "POST /task/start"
        - "GET  /task/status/{task_id}"
        - "GET  /task/result/{task_id}"
      usage: "复用现有任务提交/查询接口，扩展支持本需求 task 类型。"

  新增依赖清单:
    - name: "sqlglot"
      version: ">=23"
      reason: "跨方言 SQL 解析（DDL/INSERT），可靠提取表/列与样本值。官方文档与社区活跃度验证。"
    - name: "orjson"
      version: ">=3.9"
      reason: "高性能 JSON 编解码，用于大体量字段样本的序列化与落库。"

  架构决策:
    - "同步解析 + 异步判定：本地一次性解析 SQL 转储产出字段与样本（同步 I/O），分类判定与落库通过 Celery 异步执行，符合 BackendConstitution 的后台任务约束。"
    - "I/O 模型：遵循 BackendConstitution，HTTP 层 FastAPI；后台 Celery + RabbitMQ；可选 Redis 作为 result backend。"
    - "数据存储：MongoDB 用于存放原始提交与判定结果集合（RawPayload/TaskResult），结果文档与可审计 JSON 保留样本哈希与摘要（不落原始 PII）。"
    - "注释与风格：代码内遵循 CodeCommentStandard.yaml 的顺序化可读注释规范；接口模型使用 Pydantic v2（与现有代码一致，若宪章升级至 v3 再评估迁移）。"

scope:
  功能:
    - "解析 D:/AI_Projects/Visa/visa_db.sql，枚举库-表-字段并抽取 30-50 个代表性样本"
    - "对字段进行 True|Boundary|False 判定，输出理由、置信度与样本摘要"
    - "生成统一结构的 Markdown 说明文档与可审计 JSON（可选）"
    - "提供异步提交/查询能力：复用 /task/start|/task/status|/task/result 接口"
  结构:
    - "新增工具代码位于: Kobe/TempUtility/VisaDBOperation/*.py（目录已存在，禁止新建编号目录）"
    - "复用队列与仓储: Kobe/SharedUtility/TaskQueue/*"
  接口:
    - submit: "POST /task/start (task='user_profile_classify', payload={sql_path, options...})"
    - query:  "GET /task/status/{task_id}, GET /task/result/{task_id}"
  DoD:
    - "在目标目录生成 Markdown 文档，包含字段清单、分类结果、理由、样本摘要"
    - "在 Mongo 中可查询到 RawPayload 与 TaskResult 两类文档，索引生效"
    - "异步任务可通过现有路由提交与查询，错误可观测（日志/指标）"
    - "无原始 PII 落库；仅存样本散列与去标识摘要"

Step 1:
  title: 环境与路径校验（只读输入、受控输出）
  sub_steps:
    - "校验输入 SQL 转储存在: D:/AI_Projects/Visa/visa_db.sql"
    - "校验 venv: BackendConstitution.runtime.venv=Kobe/.venv 已创建并可激活"
    - "校验 .env 包含 MONGODB_URI、MONGODB_DATABASE、RABBITMQ_URL、REDIS_URL（按 constitution 默认值可用）"
    - "校验 RabbitMQ/Redis/Mongo 本地容器可连通（仅当执行异步与落库时需要）"
  acceptance:
    - "存在可读取的 SQL 文件；不可写入输入路径"
    - "pip 冻结输出包含 fastapi、celery、pydantic>=2、pymongo、redis 等基础依赖"
    - ".env 变量解析成功，Celery 能获取 broker 与（可选）result backend"

Step 2:
  title: SQL 解析与字段枚举（同步工具）
  sub_steps:
    - "在 Kobe/TempUtility/VisaDBOperation 新增 sql_scan.py，实现 parse_schema(sql_path) 返回 [ {table, column, type} ]"
    - "在 sql_scan.py 实现 extract_samples(sql_path, limit_per_column=50) 从 INSERT/VALUES 抽取样本"
    - "使用模块: sqlglot 解析 DDL/DML；Kobe/SharedUtility/RichLogger 初始化日志"
    - "输出中间产物 fields_samples.json（仅本地/可选），不包含原始 PII，仅存样本 hash 与摘要"
  acceptance:
    - "随机抽取每字段 30–50 个样本（可配置为 >=20），结构包含 table、column、type、samples_used、sample_hash"
    - "异常 SQL 能被跳过并记录日志；总流程不中断"

Step 3:
  title: 业务判定器实现（True|Boundary|False）
  sub_steps:
    - "新增 classifier.py，提供 classify_field(field_key, samples, column_type)->{label, confidence, reasoning}"
    - "内置规则：名称/类型/样本模式综合判定（如 phone/email/id/address），边界情形给 Boundary"
    - "输出不含原始 PII，仅含样本摘要（长度、字符集、掩码片段）与 sha256 样本哈希"
  acceptance:
    - "对典型字段（手机号/邮箱/身份证/姓名/地址）给出稳定判定；为混合/弱信号给 Boundary"
    - "判定包含可解释理由与置信度，便于审计复核"

Step 4:
  title: 文档生成器与目录结构（Markdown/JSON）
  sub_steps:
    - "新增 doc_writer.py，生成 DatabaseDietPlan.md（统一模板）"
    - "章节包含：项目概述、字段清单、分类结果表、理由与样本摘要、附录（约束/边界/数据源）"
    - "可选生成 JSON（每字段一条记录）用于审计复核"
  acceptance:
    - "Markdown 可直接阅读；结构与需求文档相符；表格字段不少于：表、字段、类型、判定、置信度、理由摘要"
    - "若开启 JSON 产出，严格不含原始 PII"

Step 5:
  title: 异步任务实现与落库（Celery + Mongo）
  sub_steps:
    - "在 Kobe/TempUtility/VisaDBOperation 新增 tasks.py，定义 celery 任务 user_profile_classify(payload)"
    - "任务流程：解析->抽样->判定->生成 Markdown/JSON；调用 repository.mongo.coll_raw_payload/coll_task_result 落库"
    - "在 Kobe/SharedUtility/TaskQueue/app.py 扩展 autodiscover 至 [\"Kobe.SharedUtility.TaskQueue\", \"Kobe.TempUtility.VisaDBOperation\"]"
    - "调用 repository.mongo.ensure_indexes() 初始化索引"
    - "统一日志：Kobe/SharedUtility/RichLogger.init_logging()"
  acceptance:
    - "提交一次任务，可在 Mongo DB 查询到 RawPayload 与 TaskResult 文档；字段含 trace_id、created_at、sample_hash"
    - "任务失败自动重试（参考 demo_long_io 的策略）且错误原因写入 TaskErrorLog"

Step 6:
  title: 扩展任务路由与数据契约（Pydantic v3）
  sub_steps:
    - "修改 Kobe/SharedUtility/TaskQueue/schemas.py：将 TaskStart.task 的正则扩展为 ^(demo_long_io|demo_sharded_job|user_profile_classify)$（保持 Pydantic v2 用法）"
    - "修改 Kobe/routers/task.py：在 /task/start 增加对 user_profile_classify 的分支与 payload 透传"
    - "示例调用：POST /task/start {\"task\":\"user_profile_classify\", \"payload\":{\"sql_path\": \"D:/AI_Projects/Visa/visa_db.sql\"}}"
  acceptance:
    - "通过现有路由提交新任务成功返回 task_id；状态/结果查询正常"

Step 7:
  title: 依赖与配置变更（最小化）
  sub_steps:
    - "在 Kobe/requirements.txt 追加: sqlglot, orjson（保持与现有版本兼容）"
    - "更新 README/环境说明：标注需本地 RabbitMQ/Redis/Mongo 容器（按 BackendConstitution.infrastructure_local）"
    - "在 .env 示例中补充/确认 MONGODB_URI、MONGODB_DATABASE、RABBITMQ_URL、REDIS_URL"
  acceptance:
    - "pip 安装成功且不破坏现有模块；uvicorn + Celery worker 可启动"

Step 8:
  title: 端到端验证（功能/性能/鲁棒性）
  sub_steps:
    - "新增脚本 Kobe/SimulationTest/visa_db_field_classification_smoke.py：构造一次 e2e 调用并输出结果摘要（不含 PII）"
    - "性能记录：在本机 1 个 worker，限制样本 30/列；记录解析/判定/落库用时与内存峰值"
    - "鲁棒性：对异常 SQL/空表/空列/极端长字段名进行回归"
  acceptance:
    - "脚本执行成功并生成 DatabaseDietPlan.md；性能报告包含各阶段耗时；异常路径不中断且有日志"

Step 9:
  title: 安全与合规校验（PII 最小化）
  sub_steps:
    - "检查任务结果中不包含原始 PII；仅保存样本长度分布/字符集/掩码与 hash"
    - "为结果集合设置 TTL 或归档策略（如仅保留摘要 30 天）"
    - "补充日志与指标（Prometheus/OpenTelemetry）埋点：任务耗时、失败率、样本计数"
  acceptance:
    - "静态抽查结果文档未见 PII；TTL/归档策略在集合上生效；指标可导出"

Step 10:
  title: 交付与归档（DoD 对齐）
  sub_steps:
    - "交付 Markdown 文档与（可选）JSON 审计文件至需求目录"
    - "在仓库提交包含：新增 *.py、requirements、.env 示例变更"
    - "在 DevPlans/004_*/Tasks.md 标注完成时间与版本号"
  acceptance:
    - "目标目录存在最终文档；Mongo 落库可复查；任务可重复运行且幂等"

self_check:
  覆盖度:
    - "功能点全部映射至步骤 2–6（解析/抽样/判定/文档/异步/落库）"
    - "交付物（Markdown/JSON）在步骤 4/10 明确产出；接口契约在步骤 6 对齐"
  技术对齐:
    - "新增依赖与 Python 3.10、Pydantic v3、Celery/RabbitMQ 兼容；参考官方文档"
    - "复用模块路径与接口与 Kobe/index.yaml 一致"
  修正策略:
    - "若发现与 BackendConstitution/BestPractise 冲突，优先以 constitution 为准并回写本文件"
  轮次:
    - "最多 3 轮：偏差→修正→复核（本文件覆盖更新）"
