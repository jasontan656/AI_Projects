Step 1:
  title: 文档状态检查与编号确定
  sub_steps:
    - "运行代码库映射脚本: python CodexFeatured/Scripts/CodebaseStructure.py"
    - "读取结构文档: CodexFeatured/Common/CodebaseStructure.yaml"
    - "扫描 D:/AI_Projects/CodexFeatured/DevPlans 按 ^\\d{3}.+ 求最大编号=004"
    - "设置编号: COUNT_3D=005, INTENT_TITLE_2_4=InitialSetup, SUBDIR_NAME=005_InitialSetup"
    - "拼接需求文档路径: D:/AI_Projects/CodexFeatured/DevPlans/005_InitialSetup/DemandDescription.md"
    - "若需求文档不存在, 则从 D:/AI_Projects/CodexFeatured/DevPlans/004_InitialSetup/DemandDescription.md 复制并校验文件大小>0"

Step 2:
  title: 规范加载与调研
  sub_steps:
    - "读取 CodexFeatured/Common/BackendConstitution.yaml 并记录关键约束: Python3.10, FastAPI, Celery+RabbitMQ, Redis 缓存, MongoDB 权威存储, 统一日志"
    - "读取 CodexFeatured/Common/CodeCommentStandard.yaml 抽取注释与 Docstring 要点"
    - "读取 CodexFeatured/Common/BestPractise.yaml 浏览其中官方链接清单"
    - "调研 Celery+RabbitMQ 发布确认/持久化/DLX 与 Worker 预取/重试 最佳实践"

Step 3:
  title: 依赖与环境准备
  sub_steps:
    - "创建虚拟环境: python -m venv Kobe/.venv; 激活并升级 pip"
    - "更新依赖文件 Kobe/requirements.txt, 写入: fastapi, uvicorn[standard], celery, redis, pymongo, pydantic, python-dotenv, prometheus-fastapi-instrumentator, opentelemetry-api, opentelemetry-sdk"
    - "安装依赖: pip install -r Kobe/requirements.txt"
    - "检查环境文件: Kobe/.env  包含 RABBITMQ_URL, REDIS_URL, MONGODB_URI 等, 与 BackendConstitution.env_defaults 对齐"
    - "提供 docker-compose.yml 启动 redis/mongodb/rabbitmq, 使用网络 ai_services_net 并暴露管理端口"

Step 4:
  title: 目录骨架与应用入口
  sub_steps:
    - "检查 FastAPI 入口 Kobe/main.py: 加载 .env, 初始化日志 init_logging(level='INFO'), 暴露 /health"
    - "写入配置模块 使用 Pydantic Settings 读取环境变量"
    - "引用日志模块 Kobe/SharedUtility/RichLogger 并在 main.py 调用 install_traceback()"
    - "创建顶层 README.md 记录运行/调试命令与目录结构"

Step 5:
  title: Celery 应用与消息配置
  sub_steps:
    - "创建 Kobe/SharedUtility/TaskQueue/__init__.py 与 app.py: 配置 Celery broker=RabbitMQ, task_acks_late=true, task_default_queue, task_routes, worker_prefetch_multiplier, task_time_limit"
    - "启用 RabbitMQ Publisher Confirms、消息 persistent、队列 durable、优先级与路由键"
    - "实现基础任务 Kobe/SharedUtility/TaskQueue/tasks.py: demo_long_io(), demo_sharded_job() 带自动重试(指数退避)"
    - "可选配置 Redis 为结果后端, 默认关闭以避免同步等待"

Step 6:
  title: API 契约与数据模型
  sub_steps:
    - "创建模型 Kobe/SharedUtility/TaskQueue/schemas.py: TaskStart, TaskStatus, TaskResult (Pydantic v3)"
    - "实现 POST /task/start: 验证入参, 生成 task_id, 发送 Celery 任务并返回 {task_id}"
    - "实现 GET /task/status/{task_id}: 查询 AsyncResult 标准化为 PENDING|STARTED|RETRY|SUCCESS|FAILURE"
    - "实现可选 GET /task/result/{task_id}: 启用 Redis 结果后端时返回结果, 默认不阻塞"

Step 7:
  title: 去重、分片与租约模型
  sub_steps:
    - "创建 Mongo 初始化 Kobe/SharedUtility/TaskQueue/repository/mongo.py, 读取 MONGODB_URI 并提供集合句柄"
    - "创建集合与索引: TaskDedup(task_fingerprint 唯一), TaskCheckpoint(shard_key, sub_key 复合索引), PendingTasks(task_key 唯一, lease_until TTL), TaskErrorLog, RawPayload"
    - "实现分片键策略: hash(key) % N 并持久化分片元数据"
    - "实现租约/Frontier: findOneAndUpdate 设置 lease_until 与 taken_by, 过期自动回收"

Step 8:
  title: 可靠性与失败处理
  sub_steps:
    - "配置 DLX/DLQ: 定义死信交换与队列策略, 失败/超时/拒绝路由至 DLQ"
    - "消费者手动 ack 与重试上限; 统一异常捕获, 结构化日志记录 task_id/root_cause/retry_count"
    - "编写 RabbitMQ 健康自检脚本: 队列 durable/消息 persistent/Publisher Confirms 生效"

Step 9:
  title: 缓存一致性与结果后端策略
  sub_steps:
    - "Redis 用于短期缓存/会话/速率, 统一 Key 前缀与 TTL"
    - "严格场景采用 Write-Invalidate 策略, 禁止不一致的写回"
    - "启用结果后端时配置过期策略, 控制资源占用"

Step 10:
  title: 观测性与统一日志
  sub_steps:
    - "集成 prometheus-fastapi-instrumentator 暴露 /metrics"
    - "按 BackendConstitution 集成 OpenTelemetry(可选), 贯穿 API→队列→Worker TraceId"
    - "统一使用 logging.getLogger(__name__), 禁止 print(); 使用 RichLogger 样式与 traceback"

Step 11:
  title: 启动与本地运行
  sub_steps:
    - "启动基础设施: docker-compose up -d (redis/mongo/rabbitmq)"
    - "启动 API: python -m Kobe.main 或 uvicorn Kobe.main:app --reload"
    - "启动 Worker: celery -A Kobe.SharedUtility.TaskQueue:app worker -l info --concurrency 10 --prefetch-multiplier 1"

Step 12:
  title: 端到端链路验证
  sub_steps:
    - "调用 POST /task/start 返回 task_id, 轮询 GET /task/status/{id} 状态变更直至 SUCCESS/FAILURE"
    - "断开/重启 RabbitMQ 验证消息不丢失且可恢复消费"
    - "模拟异常触发自动重试与 DLQ 路由, 核对 Mongo 记录与日志"

Step 13:
  title: 验收标准（DoD）
  sub_steps:
    - "API 契约满足: /task/start、/task/status/{id}、/task/result/{id}(可选) 正常工作"
    - "RabbitMQ: durable 队列、persistent 消息、Publisher Confirms 与手动 ack 生效"
    - "Mongo: 去重/分片/租约集合与索引齐备, 行为正确"
    - "Redis: 仅用于短期缓存; 一致性策略为 Write-Invalidate"
    - "观测性: /metrics 暴露基础指标; 日志统一且无敏感信息; Trace 可选可用"
    - "代码注释/Docstring 符合 CodexFeatured/Common/CodeCommentStandard.yaml"

Step 14:
  title: 交付物清单与落盘输出
  sub_steps:
    - "交付源代码: Kobe/main.py, Kobe/SharedUtility/TaskQueue/*, Kobe/SharedUtility/TaskQueue/repository/*, Kobe/SharedUtility/TaskQueue/schemas.py, Kobe/SharedUtility/TaskQueue/config.py"
    - "交付环境与依赖 docker-compose.yml"
    - "交付文档: readme.md 与运行/调试说明; OpenAPI 自动文档可用"
 
