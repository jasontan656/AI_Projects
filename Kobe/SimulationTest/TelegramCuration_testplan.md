# 测试计划：TelegramCuration

标识信息：MODULE_NAME=TelegramCuration；COUNT_3D=005；INTENT_TITLE_2_4=TelegramChatKnowledgeCuration；生成时间=2025-10-11 12:25:00

**参考文档**：
- 测试场景文档：D:/AI_Projects/Kobe/SimulationTest/TelegramCuration_testscenarios.md

**输出路径**：D:/AI_Projects/Kobe/SimulationTest/TelegramCuration_testplan.md

---

## 1. 测试组织结构

### 1.1 目录结构

为保持与既有 SimulationTest 规范一致（参考 RichLogger_testplan、TaskQueue_testplan），本计划采用如下目录：

```
Kobe/SimulationTest/TelegramCuration_testplan/
├── test_cases/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_01_功能覆盖.py
│   ├── test_02_数据多样性.py
│   ├── test_03_并发性能.py
│   ├── test_04_配置分支.py
│   ├── test_05_异常恢复.py
│   ├── test_06_依赖服务.py
│   └── test_07_真实场景.py
├── test_data/
│   ├── __init__.py
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── base_generator.py
│   │   ├── message_generator.py
│   │   ├── html_generator.py
│   │   └── random_utils.py
│   └── fixtures/
│       ├── sample_small.html
│       ├── sample_empty.html
│       ├── sample_special.html
│       └── sample_malformed.html
├── utils/
│   ├── __init__.py
│   ├── api_client.py
│   ├── db_client.py
│   ├── service_checker.py
│   └── result_validator.py
├── logs/
│   ├── .gitkeep
│   └── README.md
├── results/
│   ├── .gitkeep
│   └── README.md
├── requirements.txt
├── pytest.ini
├── run_tests.py
└── README.md
```

说明：
- 保持“测试代码与数据分离”的原则；固定样本位于 `test_data/fixtures`，动态样本经生成器产生。
- 统一通过 `run_tests.py` 执行环境检查、数据准备与 pytest 调度。
- 所有输出（日志/报告/生成样本）落在本目录树内，避免污染生产数据。

### 1.2 测试文件映射

依据场景分布（合计 71；P0=9，P1=25，P2=33，P3=4）：

| 维度 | 文件 | 场景数 | 预估时间 |
|------|------|------:|---------|
| 功能覆盖 | test_01_功能覆盖.py | 16 | ~60–90 分钟 |
| 数据多样性 | test_02_数据多样性.py | 10 | ~40 分钟 |
| 并发与性能 | test_03_并发性能.py | 8 | ~120 分钟 |
| 配置分支 | test_04_配置分支.py | 12 | ~90 分钟 |
| 异常恢复 | test_05_异常恢复.py | 10 | ~60 分钟 |
| 依赖服务 | test_06_依赖服务.py | 8 | ~90 分钟 |
| 真实场景 | test_07_真实场景.py | 7 | ~60 分钟 |

命名规范：
- 用例函数名与场景编号对齐，如 `test_scenario_1_1__正常导入小文件()`，便于 `pytest -k 1_1` 精确筛选。
- 使用 markers 标注优先级与维度，形如 `@pytest.mark.p0`、`@pytest.mark.func_cov`。

### 1.3 关键组件说明

#### conftest.py
- 作用：集中声明 fixtures、markers、hooks 与测试级别配置。
- fixtures（示例）：
  - `api_client`：封装 FastAPI 基础请求（基于 httpx）。
  - `celery_env`：提供与回收 Celery 相关环境（RABBITMQ_URL、REDIS_URL 等）。
  - `db_client`：提供 MongoDB 客户端（若场景落地持久化后启用）。
  - `redis_client`：结果后端或缓存客户端（可选）。
  - `test_config`：加载专用测试配置（见 §3.4）。
  - `test_data_dir`：指向 `test_data` 根目录。
  - `random_seed`：统一设置随机种子，保证可复现。
  - `workspace`：基于 `tmp_path` 提供隔离工作区。
- hooks：
  - `pytest_configure`/`pytest_unconfigure`：启动/收尾时进行环境检查与清理。
  - `pytest_runtest_setup`/`pytest_runtest_teardown`：按场景建立/回收资源、记录日志。

#### run_tests.py
- 作用：一键执行（检查 → 准备数据 → 运行 pytest → 汇总报告）。
- 主要参数：
  - `--priority {p0,p1,p2,p3,all}`
  - `--dimension {func,data,perf,conf,exc,dep,real}`
  - `--check-only`（仅检查环境与样本）
  - `--seed 42`（随机种子）
  - `--workers 4`（pytest-xdist 并发）

#### utils/*
- `api_client.py`：统一 REST 调用（基于 httpx，支持重试与超时配置）。
- `db_client.py`：Mongo/Redis 客户端封装与隔离数据库管理。
- `service_checker.py`：依赖服务探测与等待（见 §3.1 与 §3.2）。
- `result_validator.py`：统一断言 API/DB/文件输出/性能指标。

---

## 2. 测试数据准备

### 2.1 数据分类

- 小数据：10–20 条，快速校验解析与接口（缓存固定样本）。
- 中数据：100–500 条，性能基线与正确性（按需生成）。
- 大数据：≥ 10,000 条，性能与稳定性（运行时生成，不缓存）。
- 特殊数据：空文件/畸形/控制符/特殊字符（固定样本＋生成组合）。

### 2.2 数据生成器架构

示意代码骨架：

```python
# base_generator.py
class BaseGenerator:
    def __init__(self, seed=None):
        import random
        from faker import Faker
        self.seed = seed or random.randint(1, 1_000_000)
        random.seed(self.seed)
        self.faker = Faker('zh_CN')
        self.faker.seed_instance(self.seed)

    def set_seed(self, seed: int):
        self.seed = seed
        import random
        random.seed(seed)

# message_generator.py
class MessageGenerator(BaseGenerator):
    def generate_message(self, **kw):
        # sender/text/created_at/reply_to/media 等字段随机
        ...
    def generate_messages(self, count=None, **kw):
        ...
    def generate_special_message(self, kind='emoji'):
        ...

# html_generator.py
class TelegramHTMLGenerator(BaseGenerator):
    def generate_html(self, messages):
        # 渲染为 Telegram 导出样式（.message/.from_name/.text/.date）
        ...
    def generate_file(self, count=None, output_path=None):
        ...

# random_utils.py
def random_count(lo, hi): ...
def random_shuffle(items): ...
def random_delay(min_sec=0, max_sec=5): ...
def inject_failure(prob=0.1): ...
```

### 2.3 固定样本清单

| 样本 | 描述 | 生成方式 | 目标大小 |
|------|------|---------|--------:|
| sample_small.html | 18 条标准消息 | 一次生成 + 缓存 | ~10KB |
| sample_empty.html | 0 条消息（占位结构） | 手工创建 | ~1KB |
| sample_special.html | 特殊字符/emoji/URL/代码块 | 一次生成 + 缓存 | ~5KB |
| sample_malformed.html | 缺失关键节点/坏标签 | 手工创建 | ~5KB |

### 2.4 数据准备流程

```
run_tests.py 启动
  └─ 检查 test_data/fixtures 是否具备固定样本
        ├─ 不存在 → 运行 generators/prepare_fixtures.py 生成并缓存
        └─ 已存在 → 直接使用
  └─ 大数据场景：运行时按需生成（tests 结束后清理）
```

---

## 3. 测试环境搭建

### 3.1 依赖服务

| 服务 | 默认地址 | 检查方式 | 启动建议 |
|------|---------|---------|---------|
| RabbitMQ | amqp://guest:guest@localhost:5672/ | AMQP 连接（pika） | docker run rabbitmq:3-management |
| Redis（可选结果后端） | redis://localhost:6379/0 | `redis-cli ping` 或 redis-py | docker run redis |
| MongoDB（预留） | mongodb://localhost:27017 | pymongo ping | docker run mongo:7 |
| ChromaDB（预留） | http://localhost:8001 | GET /api/v2/heartbeat | chromadb/chroma |
| Celery Worker | N/A | `ps`/心跳日志 | `celery -A Kobe.SharedUtility.TaskQueue.app:app worker -l info` |
| FastAPI | http://localhost:8000 | GET /health | `uvicorn Kobe.main:app` |

注：当前代码已落地 FastAPI、TaskQueue 与 TelegramCuration API/任务占位；Mongo/Chroma/LLM 为后续能力，仍需在计划中预留验证位。

### 3.2 环境检查脚本（utils/service_checker.py）

职责与接口：

```python
class ServiceChecker:
    def check_rabbitmq(self) -> bool: ...  # pika.BlockingConnection
    def check_redis(self) -> bool: ...     # redis.from_url().ping()
    def check_mongodb(self) -> bool: ...   # MongoClient.admin.command('ping')
    def check_chromadb(self) -> bool: ...  # GET /api/v2/heartbeat
    def check_celery_worker(self) -> bool: ...  # 简化：探测队列消费/或进程名
    def check_fastapi(self) -> bool: ...   # GET /health == 200
    def wait_for_service(self, name, timeout=30): ...
    def check_all(self) -> dict: ...
```

### 3.3 环境隔离

- 数据库隔离：使用专用数据库（如 `test_telegram_curation`）与 Redis DB=1，测试后回收。
- 文件隔离：各测试基于 `tmp_path` 派生工作区，测试后清理。
- 任务隔离：`ALLOWED_TASKS` 指定白名单，仅放通与场景相关的任务名（如 `telegram.ingest_channel`）。

示例 fixture：

```python
@pytest.fixture(scope='session')
def test_config() -> dict:
    return {
        'FASTAPI_URL': 'http://localhost:8000',
        'RABBITMQ_URL': 'amqp://guest:guest@localhost:5672/',
        'REDIS_URL': 'redis://localhost:6379/1',
        'MONGODB_URL': 'mongodb://localhost:27017/test_telegram_curation',
        'CHROMADB_URL': 'http://localhost:8001',
        'RANDOM_SEED': 42,
        'TIMEOUT': 300,
        'MAX_WORKERS': 8,
    }
```

### 3.4 配置管理

- 测试专用 `pytest.ini`：

```ini
[pytest]
addopts = -ra --tb=short --maxfail=1
markers =
    p0: 核心场景
    p1: 重要场景
    p2: 辅助场景
    p3: 边缘场景
    func_cov: 功能覆盖
    data_var: 数据多样性
    perf: 并发与性能
    conf: 配置分支
    exc: 异常恢复
    dep: 依赖服务
    real: 真实场景
```

- `requirements.txt`（建议）：

```
pytest
pytest-xdist
pytest-timeout
pytest-dependency
pytest-html
faker
httpx
requests
redis
pymongo
pika
psutil
pyyaml
```

### 3.5 启动与清理流程

在 `conftest.py`：

```
pytest_configure:
  1) 读取 test_config → 设置随机种子
  2) ServiceChecker 检查关键服务（RabbitMQ/FASTAPI；Redis 视是否启用结果后端）
  3) 若缺失 → 给予可操作提示并中止（P0/P1 需齐全）

pytest_unconfigure:
  1) 清理临时工作区/临时样本
  2) 回收测试数据库（如启用）
  3) 汇总生成报告（合并 JUnit/JSON/HTML）
```

---

## 4. 测试执行计划

### 4.1 依赖关系图（节选）

```
Scenario-1.1（正常导入小文件）
  ├─→ Scenario-1.2（正常导入小文件-HTML）
  ├─→ Scenario-3.1（10 并发导入请求） ─→ Scenario-3.2（100 并发启动 demo 任务）
  └─→ Scenario-7.1（个人聊天导入→切片）
           ↑
           └─ Scenario-2.1（特殊字符与转义）
```

依赖列表示例：
- Scenario-1.2 → 1.1
- Scenario-3.1 → 1.1
- Scenario-3.2 → 3.1
- Scenario-7.1 → [1.1, 2.1]

### 4.2 执行阶段与拓扑排序

- 阶段1（无依赖，优先 P0）：1.1、1.4、1.5、1.7、1.10、5.7 等。
- 阶段2（依赖阶段1）：1.2、3.1、1.11、1.15、1.16 等。
- 阶段3（依赖阶段2）：3.2、7.1、7.2、7.3 等。
- 阶段4（可选 P2/P3 收尾）：剩余并发/配置/异常类场景。

### 4.3 pytest 执行策略

- 优先级 markers：`p0/p1/p2/p3`。
- 依赖：`pytest-dependency` 在关键用例上标注 `@pytest.mark.dependency(depends=["test_scenario_1_1"])`。
- 超时：`pytest-timeout`，P0 用例默认 300s；性能用例更长。
- 并行：`pytest -n 4` 用于 P1/P2 无依赖集合；P0 串行执行以降低噪声。
- 示例命令：

```bash
# 仅 P0 场景
pytest -m p0 --tb=short

# P0 + P1
pytest -m "p0 or p1" --tb=short

# 并行执行 P1（排除带 depends 的）
pytest -n 4 -m p1 -k "not depends"

# 按文件执行
pytest test_cases/test_01_功能覆盖.py
```

### 4.4 失败处理策略

| 优先级 | 失败动作 | 影响 |
|--------|---------|-----|
| P0 | 立即停止运行 | 全局 |
| P1 | 记录失败并继续执行无依赖用例 | 依赖链 |
| P2 | 记录失败，不阻塞其他 | 局部 |
| P3 | 记录失败，不阻塞其他 | 局部 |

---

## 5. 结果收集与报告

### 5.1 日志结构

```
logs/
├── test_run_{ts}.log     # 总日志（INFO+）
├── debug.log             # 调试（DEBUG）
├── error.log             # 错误（ERROR）
└── by_scenario/
    ├── scenario_1_1.log
    ├── scenario_1_2.log
    └── ...
```

日志模板：

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] [Scenario-X.Y] <message>
```

### 5.2 报告格式

- JSON 报告：`results/report.json`（总览 + 分优先级/分维度 + 失败详情）。
- HTML 报告：`results/report.html`（pytest-html，自包含）。
- JUnit 报告（可选 CI）：`results/junit.xml`。

JSON 示例：

```json
{
  "summary": {"total": 71, "passed": 0, "failed": 0, "duration": "-"},
  "by_priority": {"P0": {"total": 9}, "P1": {"total": 25}, "P2": {"total": 33}, "P3": {"total": 4}},
  "by_dimension": {"功能覆盖": 16, "数据多样性": 10, "并发与性能": 8, "配置分支": 12, "异常恢复": 10, "依赖服务": 8, "真实场景": 7},
  "failed_scenarios": []
}
```

### 5.3 性能指标

每个场景收集如下指标（psutil + 定制计时）：

```python
metrics = {
  "scenario_id": "Scenario-1.1",
  "start_time": "2025-10-11T10:00:00",
  "end_time": "2025-10-11T10:00:16",
  "duration_s": 16.0,
  "api_response_time_s": 14.0,
  "memory": {"peak_mb": 120, "avg_mb": 80},
  "cpu": {"peak_pct": 45.0, "avg_pct": 25.0}
}
```

### 5.4 结果验证器

`utils/result_validator.py` 统一断言：

```python
class ResultValidator:
    def validate_api_response(self, resp, expected): ...
    def validate_database_state(self, db, expected_records): ...
    def validate_file_output(self, path, expected_format): ...
    def validate_performance(self, metrics, thresholds): ...
```

---

## 6. 使用指南

### 6.1 初次运行

```bash
# 进入计划目录
cd Kobe/SimulationTest/TelegramCuration_testplan

# 安装依赖
pip install -r requirements.txt

# 检查环境
python run_tests.py --check-only

# 运行 P0 场景
python run_tests.py --priority p0

# 查看报告
python -m webbrowser results/report.html
```

### 6.2 常用命令

```bash
# 运行 P0+P1
python run_tests.py --priority p0,p1

# 指定维度（并发与性能）
pytest -m perf -n 4 test_cases/test_03_并发性能.py

# 只运行失败用例
pytest --lf

# 生成 HTML 报告
pytest --html=results/report.html --self-contained-html
```

### 6.3 调试与复现

- 使用 `--seed` 固定随机种子确保可复现。
- 提高日志级别（`LOG_LEVEL=DEBUG`）并重跑单场景：`pytest -k 1_1 -vv`。
- 对外部依赖（RabbitMQ/Redis）先执行 `ServiceChecker.wait_for_service`，减少因未就绪导致的假失败。

---

## 7. 预期产出

### 7.1 报告

- `results/report.json`、`results/report.html`、（可选）`results/junit.xml`。

### 7.2 日志

- `logs/test_run_{timestamp}.log`、`logs/debug.log`、`logs/error.log`、`logs/by_scenario/*.log`。

### 7.3 测试数据

- 固定样本：`test_data/fixtures/*.html`。
- 生成样本（临时）：`test_data/generated/*.html`（由各用例在 `tmp_path` 下生成并清理）。

---

工作流版本：2.0 | 生成时间：2025-10-11 12:25:00

---

## 附录 A：场景到测试用例映射（样例）

为便于追踪，以下列出部分关键场景与测试函数名对照：

| 场景编号 | 场景名称 | 归属文件 | 测试函数名 |
|---------|---------|---------|-----------|
| Scenario-1.1 | 正常导入小文件（JSON） | test_01_功能覆盖.py | `test_scenario_1_1__json_small_ingest` |
| Scenario-1.2 | 正常导入小文件（HTML） | test_01_功能覆盖.py | `test_scenario_1_2__html_small_ingest` |
| Scenario-1.4 | 格式错误 JSON | test_01_功能覆盖.py | `test_scenario_1_4__json_malformed_raises` |
| Scenario-1.5 | 缺失文件 | test_01_功能覆盖.py | `test_scenario_1_5__missing_file_raises` |
| Scenario-1.7 | 时间窗口过滤 | test_01_功能覆盖.py | `test_scenario_1_7__since_until_filter` |
| Scenario-1.10 | 启动导入 API | test_01_功能覆盖.py | `test_scenario_1_10__api_ingest_start_returns_task_id` |
| Scenario-1.15 | Celery 任务 ingest_channel | test_01_功能覆盖.py | `test_scenario_1_15__celery_ingest_channel_dispatch` |
| Scenario-2.1 | 特殊字符与转义 | test_02_数据多样性.py | `test_scenario_2_1__special_chars_preserved` |
| Scenario-2.5 | 大数据（10k） | test_02_数据多样性.py | `test_scenario_2_5__large_dataset_performance` |
| Scenario-3.1 | 10 并发导入请求 | test_03_并发性能.py | `test_scenario_3_1__ten_concurrent_ingest` |
| Scenario-3.2 | 100 并发启动任务 | test_03_并发性能.py | `test_scenario_3_2__hundred_concurrent_tasks` |
| Scenario-4.1 | RabbitMQ 正常 | test_04_配置分支.py | `test_scenario_4_1__rabbitmq_ok` |
| Scenario-4.4 | Redis 关闭 | test_04_配置分支.py | `test_scenario_4_4__redis_disabled_degrades_gracefully` |
| Scenario-5.2 | RabbitMQ 连接中断恢复 | test_05_异常恢复.py | `test_scenario_5_2__rabbitmq_restart_recovers` |
| Scenario-5.7 | 不合法任务名 | test_05_异常恢复.py | `test_scenario_5_7__invalid_task_slug_422` |
| Scenario-6.2 | 队列反压 | test_06_依赖服务.py | `test_scenario_6_2__queue_backpressure` |
| Scenario-7.2 | 工作群 10k 导入 | test_07_真实场景.py | `test_scenario_7_2__workgroup_10k_e2e` |

---

## 附录 B：示例骨架代码片段

以下片段便于快速落地；实现需根据项目实际调整。

```python
# utils/api_client.py
import httpx

class APIClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.client = httpx.Client(base_url=base_url, timeout=timeout)

    def health(self):
        r = self.client.get('/health')
        r.raise_for_status()
        return r.json()

    def ingest_start(self, source_dir: str, workspace_dir: str):
        r = self.client.post('/api/telegram-curation/ingest/start', json={
            'sourceDir': source_dir, 'workspaceDir': workspace_dir,
        })
        r.raise_for_status()
        return r.json()

    def task_status(self, task_id: str):
        return self.client.get(f'/api/telegram-curation/task/{task_id}').json()
```

```python
# utils/service_checker.py（节选）
import time, httpx
import pika, redis, pymongo

class ServiceChecker:
    def check_rabbitmq(self, url: str) -> bool:
        try:
            params = pika.URLParameters(url)
            conn = pika.BlockingConnection(params)
            conn.close()
            return True
        except Exception:
            return False

    def check_fastapi(self, base_url: str) -> bool:
        try:
            r = httpx.get(base_url.rstrip('/') + '/health', timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def wait_for_service(self, fn, *args, timeout=30):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if fn(*args):
                return True
            time.sleep(1)
        return False
```

```python
# test_cases/conftest.py（节选）
import os, pytest, random
from utils.api_client import APIClient
from utils.service_checker import ServiceChecker

@pytest.fixture(scope='session')
def test_config():
    return {
        'FASTAPI_URL': os.getenv('TEST_FASTAPI_URL', 'http://localhost:8000'),
        'RABBITMQ_URL': os.getenv('TEST_RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/'),
        'RANDOM_SEED': int(os.getenv('TEST_RANDOM_SEED', '42')),
    }

@pytest.fixture(scope='session', autouse=True)
def env_ready(test_config):
    sc = ServiceChecker()
    assert sc.wait_for_service(sc.check_fastapi, test_config['FASTAPI_URL'], timeout=30)
    # RabbitMQ 可按需检查
    yield

@pytest.fixture(scope='session')
def api_client(test_config):
    return APIClient(test_config['FASTAPI_URL'])

@pytest.fixture(autouse=True)
def random_seed(test_config):
    random.seed(test_config['RANDOM_SEED'])
```

---

## 附录 C：资源监控与基线

- CPU/内存：使用 `psutil.Process(os.getpid())` 采样 RSS/CPU 百分比；在性能类场景记录峰值与平均值。
- I/O：必要时统计读取/写入字节数（尤其在大文件 HTML 解析）。
- 阈值参考（本机基线，可随硬件调整）：
  - 10k JSON 解析：< 5 分钟；峰值内存 < 500MB。
  - 10 并发导入启动：P95 < 2 分钟；错误率 < 1%。
