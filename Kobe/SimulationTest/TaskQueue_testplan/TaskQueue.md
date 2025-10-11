# TestSituationCoverageDiscovery: TaskQueue 模块可执行测试计划输入

说明：本文件为 TestPipelineGeneration 的前置输入，全部条目为“必须”执行的指令，不包含“建议/可选”措辞。测试默认在本机仿真环境执行，路径固定为 `D:/AI_Projects/Kobe/SimulationTest`。

## 1. 前置校验（强制）
- 必须校验“用户输入”不为空且等于 `TaskQueue`，否则立即失败并中止后续步骤。
- 必须校验以下关键文件存在：
  - `Kobe/routers/task.py`
  - `Kobe/SharedUtility/TaskQueue/app.py`
  - `Kobe/SharedUtility/TaskQueue/config.py`
  - `Kobe/SharedUtility/TaskQueue/tasks.py`
  - `Kobe/SharedUtility/TaskQueue/schemas.py`

## 2. 依赖与环境（强制）
- 语言与运行时：Python 3.10（与 BackendConstitution.runtime 一致），虚拟环境固定为 `Kobe/.venv`，环境变量加载自 `Kobe/.env`。
- 必须启动 FastAPI 应用与 Celery Worker：
  - HTTP 服务：`python -m Kobe.main` 或 `uvicorn Kobe.main:app --host 127.0.0.1 --port 8000`
  - Celery Worker：`celery -A Kobe.SharedUtility.TaskQueue:app worker -l info --concurrency 2 -Q q.tasks.default,q.tasks.sharded`
  - 若配置变更（见第 4 节），必须重启 Worker 与 HTTP 服务。
- 外部服务（本地容器或宿主进程均可）：
  - RabbitMQ（含 Management UI/API，端口 5672/15672）
  - Redis（端口 6379）
  - MongoDB（端口 27017）

## 3. HTTP 端点清单（强制）
- POST `/task/start`：入参模型 `TaskStart`（见 schemas.py），返回 `{"task_id": str}`。
- GET `/task/status/{task_id}`：返回 `TaskStatus`。
- GET `/task/result/{task_id}`：返回 `TaskResult`（当结果尚不可用时，状态码必须为 202）。

## 4. 可配置项与覆盖矩阵（强制两两覆盖）
来源：`Kobe/SharedUtility/TaskQueue/config.py` 的 `Settings`。

- `RABBITMQ_URL`（默认 `amqp://guest:guest@localhost:5672/`）
  - 场景A：RabbitMQ 可用
  - 场景B：RabbitMQ 不可用（关闭端口或错误地址）
- `REDIS_URL`（默认 `redis://localhost:6379/0`）
  - 场景A：Redis 可用
  - 场景B：Redis 不可用
- `ENABLE_RESULT_BACKEND`（默认 False）
  - 场景A：False（结果查询仅返回状态，不含 result，期望 202）
  - 场景B：True（结果查询可返回 result，期望 200）
- `CELERY_DEFAULT_QUEUE`（默认 `q.tasks.default`）
  - 场景A：默认名
  - 场景B：自定义名（需用管理 API 验证队列存在）
- `CELERY_SHARDED_QUEUE`（默认 `q.tasks.sharded`）
  - 场景A：默认名
  - 场景B：自定义名（路由必须生效）
- `CELERY_DLX` / `CELERY_DLQ`（默认 `dlx.tasks` / `q.tasks.dlq`）
  - 场景A：默认
  - 场景B：自定义（必须验证 DLQ 队列已声明）
- `CELERY_PREFETCH`（默认 1）
  - 场景A：1
  - 场景B：>1（例如 4）
- `CELERY_TASK_TIME_LIMIT` / `CELERY_TASK_SOFT_TIME_LIMIT`（默认 300 / 270）
  - 场景A：默认
  - 场景B：软超时极低（如 1~2s）以验证超时处理

执行规则：
- 上述每个二分配置均必须在“服务可用/不可用”及“结果后端开关”两维度组合下覆盖最少 1 个功能用例；
- 产生的组合必须至少覆盖：功能、压力、错误恢复、数据库校验四类测试（见第 7 节）。

## 5. 服务状态查询（强制）
- RabbitMQ Management API：
  - 健康检查：`GET http://127.0.0.1:15672/api/overview`（Basic Auth 使用 `guest/guest` 或 `.env` 中凭据）。
  - 队列校验：`GET /api/queues/%2f/<queue>`（`<queue>` 为默认或自定义队列名）。
- Redis：
  - Python 方式：`redis.Redis.from_url(REDIS_URL).ping()` 必须返回 True。
  - CLI 方式（如可用）：`redis-cli -h 127.0.0.1 -p 6379 ping` 必须返回 `PONG`。
- MongoDB（pymongo）：
  - `MongoClient(MONGODB_URI).admin.command("ping")` 的 `ok` 必须为 1。

## 6. 工具栈（强制且唯一）
- 测试框架：`pytest`
- HTTP 客户端：`requests`
- 超时控制：`pytest-timeout`
- 并发执行：`pytest-xdist`
- 报告生成：`pytest-html`
- 结构化日志：`structlog`（用于测试日志统一输出，可在 `conftest.py` 初始化）

安装命令（在 `Kobe/.venv` 中执行）：
```
pip install -U pytest requests pytest-timeout pytest-xdist pytest-html structlog
```

## 7. 测试场景与用例（强制）

### 7.1 功能测试
1) 启动任务—长 IO（无结果后端）
   - 前置：`ENABLE_RESULT_BACKEND=False`，RabbitMQ 可用。
   - 步骤：POST `/task/start`，body `{"task":"demo_long_io","duration_sec":2,"fail_rate":0}`。
   - 断言：返回 200 且包含 `task_id`；随后轮询 `/task/status/{id}` 至 `SUCCESS`；请求 `/task/result/{id}` 返回 202。

2) 启动任务—长 IO（启用结果后端）
   - 前置：`ENABLE_RESULT_BACKEND=True`，Redis 可用。
   - 步骤：同上。
   - 断言：`/task/result/{id}` 在完成后返回 200 且 `result.kind == "demo_long_io"`，`slept == duration_sec`。

3) 启动任务—分片任务路由
   - 前置：RabbitMQ 可用。
   - 步骤：POST `/task/start`，body `{"task":"demo_sharded_job","shard_key":"user-42"}`。
   - 断言：成功返回 `task_id`；完成后 `result.kind == "demo_sharded_job"` 且 `partition` 在 `[0,7]`。
   - 额外：调用管理 API 校验 `q.tasks.sharded` 上的入队计数大于 0。

4) 自定义队列名（default/sharded）
   - 前置：设置 `CELERY_DEFAULT_QUEUE` 与/或 `CELERY_SHARDED_QUEUE` 为自定义；重启 Worker。
   - 步骤：分别触发两类任务。
   - 断言：管理 API 返回对应自定义队列存在，且消息入队、被消费。

### 7.2 压力测试（最小并发保障）
5) 基础并发
   - 前置：`--concurrency 2`，`CELERY_PREFETCH=1`。
   - 步骤：并发提交 20 个 `demo_long_io(duration_sec=2)`；使用 `pytest-xdist -n auto` 驱动 HTTP 提交。
   - 断言：全部任务在合理时间内完成；无 HTTP 超时；Worker 无未处理异常。

6) 提高预取与并发
   - 前置：`--concurrency 4`，`CELERY_PREFETCH=4`。
   - 步骤：并发提交 100 个任务。
   - 断言：吞吐提升；管理 API/metrics 显示消费者活跃且队列无长时间堆积。

### 7.3 错误与恢复
7) Broker 不可用
   - 前置：关闭 RabbitMQ 或将 `RABBITMQ_URL` 设置为不可达；重启 HTTP 服务。
   - 步骤：POST `/task/start`。
   - 断言：返回 5xx 或明确错误；不得长时间卡死；日志包含连接失败与重试信息。

8) 结果后端关闭
   - 前置：`ENABLE_RESULT_BACKEND=False`。
   - 步骤：完成 `demo_long_io` 后请求 `/task/result/{id}`。
   - 断言：状态码为 202；响应仅含 `task_id` 与 `state`。

9) 软超时触发
   - 前置：设置 `CELERY_TASK_SOFT_TIME_LIMIT=1`；重启 Worker。
   - 步骤：提交 `demo_long_io(duration_sec=5)`。
   - 断言：任务被中断并进入 `RETRY` 或最终 `FAILURE`（取决于重试配置）；日志包含超时信息。

10) 随机失败重试
   - 前置：保留默认 `max_retries`。
   - 步骤：提交 `demo_long_io(fail_rate=0.6)` 多次。
   - 断言：可观察到 RETRY→SUCCESS 的闭环；超过重试上限时进入 `FAILURE`。

### 7.4 数据库读写验证（Mongo）
11) 索引初始化
   - 步骤：调用 `Kobe/SharedUtility/TaskQueue/repository/mongo.py: ensure_indexes()`（通过临时脚本或测试钩子）。
   - 断言：
     - `TaskDedup.task_fingerprint` 唯一索引存在；
     - `TaskCheckpoint(shard_key, sub_key)` 复合索引存在；
     - `PendingTasks.task_key` 唯一索引存在；
     - `PendingTasks.lease_until` TTL 索引存在（`expireAfterSeconds=0`）。

12) TTL 生效性（最小验证）
   - 步骤：向 `PendingTasks` 写入 `lease_until=now()` 的文档；等待 TTL 监视器周期后复查。
   - 断言：文档被自动清理（允许数分钟内完成）。

## 8. 测试套件结构（强制）
在 `D:/AI_Projects/Kobe/SimulationTest/TaskQueue_testplan/test_cases/` 下创建：
- `test_functional.py`（覆盖 7.1）
- `test_stress.py`（覆盖 7.2）
- `test_recovery.py`（覆盖 7.3）
- `test_mongo_indexes.py`（覆盖 7.4）
- `conftest.py`：
  - 统一加载 `.env`；
  - 初始化 `structlog`；
  - 提供 `client` fixture（封装 `requests.Session`，带默认超时）。

## 9. 执行与报告（强制）
- 命令：
```
pytest -q --maxfail=1 --disable-warnings \
  --timeout=30 -n auto \
  --html=results/TaskQueue_report.html --self-contained-html
```
- 产物：`results/TaskQueue_report.html` 与 JUnit（如需对接 CI，可追加 `--junitxml=results/junit.xml`）。

## 10. 验收标准（强制）
- 必须符合 `BackendConstitution.yaml` 与 `SimulationTestingConstitution.yaml` 的约束：
  - 后台任务统一由 Celery 承载；
  - 消息投递“至少一次”、开启 Publisher Confirms、消息持久化；
  - API 不得阻塞等待长流程；
  - 测试目录与产物路径固定。
- 所有可配置项均已在第 4 节给出覆盖组合并在第 7 节映射到用例；
- 工具栈严格为第 6 节所列；
- 关键负面场景（Broker/Redis 不可用、软超时、随机失败）均已验证；
- Mongo 索引及 TTL 能力已验证。

## 11. 附：服务探活脚本片段（强制存档）
```python
# rabbitmq_check.py
import requests, os
u = os.getenv('RABBITMQ_MAN_URL','http://127.0.0.1:15672/api/overview')
auth=(os.getenv('RABBITMQ_USER','guest'), os.getenv('RABBITMQ_PASS','guest'))
r = requests.get(u, auth=auth, timeout=5); r.raise_for_status()

# redis_check.py
import redis, os
assert redis.Redis.from_url(os.getenv('REDIS_URL','redis://localhost:6379/0')).ping()

# mongo_check.py
from pymongo import MongoClient; import os
ok = MongoClient(os.getenv('MONGODB_URI','mongodb://localhost:27017')).admin.command('ping')['ok']
assert ok == 1
```

