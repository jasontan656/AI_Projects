# 测试技术决策：TelegramCuration

标识信息：MODULE_NAME=TelegramCuration；COUNT_3D=005；INTENT_TITLE_2_4=TelegramChatKnowledgeCuration；生成时间=2025-10-11 21:45:00

参考文档：
- 测试场景文档：D:/AI_Projects/Kobe/SimulationTest/TelegramCuration_testscenarios.md
- 测试计划文档：D:/AI_Projects/Kobe/SimulationTest/TelegramCuration_testplan.md

输出路径：D:/AI_Projects/Kobe/SimulationTest/TelegramCuration_testtech.md

---

## 0. 输入解析摘要（来自步骤1）

- 随机化策略（节选）：
  - 消息内容随机生成（长度 10–120 字），sender 从 3 人中随机；`text` 随机嵌入 emoji/URL/换行；消息时间戳在近 90 天内随机；部分场景不启用随机化（“无”）。
  - 需要支持：数据量随机、顺序随机、延迟随机、失败注入、内容随机。
- 并发需求：10 并发导入请求；100 并发启动任务；并发轮询与压测，记录 P95；目标“100 并发下错误率 < 1%”。
- 性能指标：全量10万消息 ≤ 30 分钟；增量5千消息 ≤ 5 分钟；检索 P95 ≤ 800ms；记录响应时间、CPU/内存峰值与曲线；性能用例“平均 < 1 分钟；P95 < 2 分钟”。
- 依赖服务清单：FastAPI（/health）、RabbitMQ（必需）、Redis（可选结果后端）、MongoDB/ChromaDB（预留，后续能力）。
- 目录结构（计划约定）：`test_cases/`、`test_data/{generators,fixtures}/`、`utils/`、`logs/`、`results/`、`pytest.ini`、`requirements.txt`、`run_tests.py`。

宪法约束（CodexFeatured/Common/SimulationTestingConstitution.yaml）：
- 必须采用 pytest + pytest-asyncio；统一超时用 pytest-timeout；报告用 pytest-json-report + pytest-html；资源监控用 psutil；性能基准可用 pytest-benchmark；所有测试从官方入口发起，执行路径可追踪且结果可复现。

---

## 1. 测试框架和依赖

### 1.1 核心框架

```yaml
core_framework:
  pytest: 7.4.3
  reason: 测试宪法强制要求，业界标准
```

### 1.2 pytest 插件

| 插件 | 版本 | 用途 | 必需性 |
|------|------|------|--------|
| pytest-asyncio | 0.21.1 | 异步测试支持 | 必需（项目使用 async） |
| pytest-timeout | 2.2.0 | 超时控制 | 必需（防止测试卡死） |
| pytest-json-report | 1.5.0 | JSON 报告 | 必需（结构化报告） |
| pytest-html | 4.1.1 | HTML 报告 | 必需（可视化报告） |
| pytest-xdist | 3.5.0 | 并行执行 | 推荐（提高效率） |
| pytest-repeat | 0.9.3 | 重复执行 | 可选（稳定性测试） |
| pytest-dependency | 0.5.1 | 用例依赖管理 | 推荐（场景依赖） |
| pytest-benchmark | 4.0.0 | 性能基准统计 | 推荐（性能评估） |

### 1.3 所有依赖清单（requirements.txt 完整内容）

```txt
# 核心测试框架
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-timeout==2.2.0
pytest-json-report==1.5.0
pytest-html==4.1.1
pytest-xdist==3.5.0
pytest-repeat==0.9.3
pytest-dependency==0.5.1
pytest-benchmark==4.0.0

# HTTP 客户端
requests==2.31.0
httpx==0.25.2

# 数据库/中间件客户端
pymongo==4.6.1
redis==5.0.1
pika==1.3.2

# 随机化与数据生成
faker==20.1.0

# 资源监控
psutil==5.9.6

# 日志
structlog==23.2.0

# 配置/类型（可选）
pydantic==2.5.3
pydantic-settings==2.1.0
```

---

## 2. 随机化技术实现

以下代码位于建议路径：`test_data/generators/random_utils.py` 与 `test_data/generators/message_generator.py`，均支持统一随机种子，确保可复现。

### 2.1 数据量随机化

```python
# test_data/generators/random_utils.py
from __future__ import annotations

import os
import random
from typing import List

# 全局随机种子（从环境变量读取，确保可复现）
RANDOM_SEED: int = int(os.getenv("TEST_RANDOM_SEED", random.randint(1, 1_000_000)))
random.seed(RANDOM_SEED)

def random_count(min_val: int, max_val: int) -> int:
    """
    生成指定范围内的随机数量

    Args:
        min_val: 最小值
        max_val: 最大值

    Returns:
        随机数量

    Example:
        >>> cnt = random_count(10, 20)
        >>> assert 10 <= cnt <= 20
    """
    return random.randint(min_val, max_val)

def random_count_with_distribution(
    small_prob: float = 0.3,
    medium_prob: float = 0.5,
    large_prob: float = 0.2,
) -> str:
    """
    按概率分布返回数据规模

    Args:
        small_prob: 小数据量概率（10-20条）
        medium_prob: 中数据量概率（100-500条）
        large_prob: 大数据量概率（10000+条）

    Returns:
        'small' | 'medium' | 'large'
    """
    rand = random.random()
    if rand < small_prob:
        return "small"
    if rand < small_prob + medium_prob:
        return "medium"
    return "large"

def random_shuffle(items: List[object]) -> List[object]:
    """
    随机打乱列表顺序（不修改原列表）

    Args:
        items: 原始列表

    Returns:
        打乱后的新列表
    """
    shuffled = list(items)
    random.shuffle(shuffled)
    return shuffled

def random_delay(min_sec: float = 0.0, max_sec: float = 5.0) -> None:
    """
    随机延迟（模拟网络延迟）

    Args:
        min_sec: 最小延迟（秒）
        max_sec: 最大延迟（秒）
    """
    import time

    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
```

### 2.2 失败注入

```python
# test_data/generators/random_utils.py（续）
import requests
from typing import Any, Callable

class FailureInjector:
    """失败注入器，用于模拟各种失败场景"""

    @staticmethod
    def should_inject_failure(probability: float = 0.1) -> bool:
        """
        根据概率决定是否注入失败

        Args:
            probability: 失败概率（0.0-1.0）

        Returns:
            True 表示应该注入失败
        """
        return random.random() < probability

    @staticmethod
    def inject_api_failure(probability: float = 0.1) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        API 失败注入装饰器

        Args:
            probability: 失败概率
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if FailureInjector.should_inject_failure(probability):
                    failure_type = random.choice(["timeout", "connection_error", "server_error"]) 
                    if failure_type == "timeout":
                        raise requests.Timeout("Simulated timeout")
                    if failure_type == "connection_error":
                        raise requests.ConnectionError("Simulated connection error")
                    raise requests.HTTPError("500 Server Error")
                return func(*args, **kwargs)
            return wrapper
        return decorator
```

### 2.3 内容随机化

```python
# test_data/generators/message_generator.py
from __future__ import annotations

import random
from typing import Optional
from faker import Faker

class MessageGenerator:
    """消息内容生成器"""

    def __init__(self, seed: Optional[int] = None) -> None:
        self.faker = Faker("zh_CN")
        if seed is not None:
            self.faker.seed_instance(seed)

    def generate_text(self, min_length: int = 10, max_length: int = 500) -> str:
        """
        生成随机文本

        Args:
            min_length: 最小长度
            max_length: 最大长度
        """
        target_length = random.randint(min_length, max_length)
        return self.faker.text(max_nb_chars=target_length)

    def generate_emoji(self) -> str:
        """随机生成表情符号"""
        emojis = [
            "😀","😁","😂","🤣","😃","😄","😅","😆","😉","😊","😋","😎","😍","😘","🥰","😗","😙","😚","🙂","🤗",
            "🤩","🤔","🤨","😐","😑","😶","🙄","😏","😣","😥",
        ]
        return random.choice(emojis)

    def generate_code_block(self) -> str:
        """随机生成代码块（markdown 格式）"""
        languages = ["python", "javascript", "sql", "bash"]
        lang = random.choice(languages)
        code_samples = {
            "python": 'def hello():\n    print("Hello, World!")',
            "javascript": 'function hello() {\n  console.log("Hello, World!");\n}',
            "sql": "SELECT * FROM users WHERE id = 1;",
            "bash": 'echo "Hello, World!"',
        }
        return f"```{lang}\n{code_samples[lang]}\n```"

    def generate_html_tag(self) -> str:
        """随机生成 HTML 标签片段"""
        tags = ["<b>Bold</b>", "<i>Italic</i>", '<a href="#">Link</a>', "<code>code</code>", "<pre>preformatted</pre>"]
        return random.choice(tags)
```

### 2.4 随机种子管理（pytest 自动注入）

```python
# conftest.py（节选：随机种子）
import os
import random
import pytest
from faker import Faker

@pytest.fixture(scope="session")
def random_seed() -> int:
    """
    全局随机种子 fixture
    从环境变量读取种子，如果未设置则随机生成；确保测试可复现。
    """
    seed = int(os.getenv("TEST_RANDOM_SEED", random.randint(1, 1_000_000)))

    # 设置随机源
    random.seed(seed)
    faker_instance = Faker("zh_CN")
    faker_instance.seed_instance(seed)

    print(f"\n=== Random Seed: {seed} ===")
    print(f"To reproduce: TEST_RANDOM_SEED={seed} pytest")
    return seed

@pytest.fixture(autouse=True)
def _apply_seed(random_seed: int) -> None:
    # 仅用于声明顺序依赖，实际设置在 random_seed 内完成
    return None
```

重要提示：
- 所有测试运行时会自动生成并打印随机种子；
- 要复现某次测试，设置环境变量：`TEST_RANDOM_SEED=<seed值>`（示例：`TEST_RANDOM_SEED=123456 pytest`）。

---

## 3. 并发测试技术

### 3.1 并发测试器

```python
# test_cases/test_03_并发性能.py（并发测试器）
from __future__ import annotations

import queue
import threading
import time
from statistics import mean
from typing import Any, Callable, Dict, List, Tuple

class ConcurrentTester:
    """并发测试器（适用于 I/O 密集型）"""

    def __init__(self, num_workers: int) -> None:
        self.num_workers = num_workers
        self.results: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    def run_concurrent(
        self,
        func: Callable[..., Any],
        args_list: List[Tuple[Any, ...]] | None = None,
        kwargs_list: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        并发执行函数

        Args:
            func: 要执行的函数
            args_list: 每个 worker 的位置参数列表
            kwargs_list: 每个 worker 的关键字参数列表

        Returns:
            结果列表（每项包含：success/result/error/duration/worker_id）
        """
        if args_list is None:
            args_list = [tuple()] * self.num_workers
        if kwargs_list is None:
            kwargs_list = [{}] * self.num_workers

        def worker(worker_id: int, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> None:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                self.results.put({
                    "success": True,
                    "result": result,
                    "duration": duration,
                    "worker_id": worker_id,
                })
            except Exception as e:  # noqa: BLE001
                duration = time.perf_counter() - start
                self.results.put({
                    "success": False,
                    "error": str(e),
                    "duration": duration,
                    "worker_id": worker_id,
                })

        threads: List[threading.Thread] = []
        for i in range(self.num_workers):
            args = args_list[i] if i < len(args_list) else tuple()
            kwargs = kwargs_list[i] if i < len(kwargs_list) else {}
            t = threading.Thread(target=worker, args=(i, args, kwargs), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        results: List[Dict[str, Any]] = []
        while not self.results.empty():
            results.append(self.results.get())
        return results

    @staticmethod
    def _percentile(values: List[float], q: float) -> float:
        if not values:
            return 0.0
        values = sorted(values)
        idx = max(0, min(len(values) - 1, int(round((len(values) - 1) * q))))
        return values[idx]

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, float | int]:
        """
        分析并发测试结果，返回统计信息
        """
        total = len(results)
        success_count = sum(1 for r in results if r.get("success"))
        failure_count = total - success_count
        success_rate = (success_count / total) if total else 0.0
        durations = [r["duration"] for r in results]
        return {
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_rate,
            "avg_duration": mean(durations) if durations else 0.0,
            "p50_duration": self._percentile(durations, 0.50),
            "p95_duration": self._percentile(durations, 0.95),
            "p99_duration": self._percentile(durations, 0.99),
        }
```

### 3.2 使用示例

```python
import pytest
from pathlib import Path

@pytest.mark.p1
@pytest.mark.timeout(600)
def test_scenario_3_1_10_concurrent_users(api_client, tmp_path: Path):
    """Scenario-3.1：10 并发用户"""
    from test_cases.test_03_并发性能 import ConcurrentTester

    tester = ConcurrentTester(num_workers=10)

    # 准备每个 worker 的不同输入（示例：10 个文件路径）
    args_list = []
    for i in range(10):
        test_file = tmp_path / f"concurrent_{i}.html"
        # 这里调用你的样本生成器，生成每个文件 100 条消息
        # generate_telegram_html(count=100, output=test_file)
        test_file.write_text("<html><body>mock</body></html>", encoding="utf-8")
        args_list.append((str(test_file),))

    # 被测函数：例如 api_client.ingest_telegram_html(file_path)
    def _call_ingest(file_path: str):
        return api_client.ingest_start(source_dir=file_path, workspace_dir=str(tmp_path))

    results = tester.run_concurrent(func=_call_ingest, args_list=args_list)
    stats = tester.analyze_results(results)

    assert stats["success_rate"] >= 0.95, f"成功率{stats['success_rate']:.2%}低于95%"
    assert stats["avg_duration"] < 60, f"平均响应时间{stats['avg_duration']:.1f}s超过1分钟"
    assert stats["p95_duration"] < 120, f"P95响应时间{stats['p95_duration']:.1f}s超过2分钟"
```

---

## 4. 模拟（Mock）技术

### 4.1 大模型 API 模拟

```python
# utils/mock_llm.py
from __future__ import annotations

import random
import time
from typing import Any, Dict, List

class MockLLMAPI:
    """模拟大模型 API，用于测试"""

    def __init__(self, response_delay: float = 0.1, failure_rate: float = 0.0) -> None:
        self.response_delay = response_delay
        self.failure_rate = failure_rate

    def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4", **_: Any) -> Dict[str, Any]:
        """
        模拟 chat completion API
        """
        time.sleep(self.response_delay)
        if random.random() < self.failure_rate:
            raise RuntimeError("Simulated LLM API failure")
        return {
            "id": f"mock-{random.randint(1000, 9999)}",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "This is a mock response for testing."},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
```

在 `conftest.py` 中提供 fixture：

```python
# conftest.py（节选：mock_llm）
import os
import pytest

from utils.mock_llm import MockLLMAPI

@pytest.fixture(scope="session")
def mock_llm_api(test_config):
    """
    模拟大模型API的 fixture
    如果配置中 TEST_MOCK_LLM=True，则返回 MockLLMAPI；否则返回真实客户端（示例）。
    """
    if test_config.MOCK_LLM:
        return MockLLMAPI(response_delay=test_config.LLM_RESPONSE_DELAY, failure_rate=0.0)
    else:
        try:
            from openai import OpenAI  # type: ignore
        except Exception:  # noqa: BLE001
            raise RuntimeError("OpenAI SDK not installed; set TEST_MOCK_LLM=True for tests")
        return OpenAI(api_key=test_config.OPENAI_API_KEY)
```

### 4.2 网络超时模拟

```python
# utils/mock_network.py
from __future__ import annotations

from typing import Optional
from unittest.mock import patch
import requests

class NetworkMock:
    """网络模拟器"""

    @staticmethod
    def inject_timeout(url_pattern: Optional[str] = None):
        """
        注入网络超时

        Example:
            >>> with NetworkMock.inject_timeout():
            ...     requests.get("http://example.com")  # 会超时
        """
        original_request = requests.request

        def mock_request(method, url, *args, **kwargs):  # type: ignore[override]
            if url_pattern is None or (isinstance(url, str) and url_pattern in url):
                raise requests.Timeout("Simulated timeout")
            return original_request(method, url, *args, **kwargs)

        return patch("requests.request", side_effect=mock_request)
```

---

## 5. 性能监控技术

### 5.1 性能指标收集器

```python
# utils/performance_monitor.py
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Dict

import psutil

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self) -> None:
        self.process = psutil.Process()
        self.metrics: Dict[str, Dict] = {}

    @contextmanager
    def monitor(self, scenario_id: str):
        """
        性能监控上下文管理器
        """
        start_time = time.perf_counter()
        start_cpu = self.process.cpu_percent(interval=None)
        start_memory = self.process.memory_info().rss

        peak_memory = start_memory
        peak_cpu = start_cpu

        stop_event = threading.Event()

        def loop() -> None:
            nonlocal peak_memory, peak_cpu
            while not stop_event.is_set():
                current_memory = self.process.memory_info().rss
                current_cpu = self.process.cpu_percent(interval=None)
                peak_memory = max(peak_memory, current_memory)
                peak_cpu = max(peak_cpu, current_cpu)
                time.sleep(0.1)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        try:
            yield
        finally:
            stop_event.set()
            t.join(timeout=1)
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss
            self.metrics[scenario_id] = {
                "duration": end_time - start_time,
                "memory": {
                    "start": start_memory / 1024 / 1024,
                    "end": end_memory / 1024 / 1024,
                    "peak": peak_memory / 1024 / 1024,
                    "delta": (end_memory - start_memory) / 1024 / 1024,
                },
                "cpu": {
                    "start": start_cpu,
                    "peak": peak_cpu,
                },
            }

    def get_metrics(self, scenario_id: str) -> Dict:
        return self.metrics.get(scenario_id, {})

    def get_all_metrics(self) -> Dict[str, Dict]:
        return self.metrics
```

在 `conftest.py` 中集成（可选自动包裹每个测试）：

```python
# conftest.py（节选：performance monitor 集成）
import pytest
from utils.performance_monitor import PerformanceMonitor

@pytest.fixture(scope="session")
def performance_monitor() -> PerformanceMonitor:
    return PerformanceMonitor()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # 若测试使用了 performance_monitor fixture，则自动记录性能
    if hasattr(item, "fixturenames") and "performance_monitor" in item.fixturenames:  # type: ignore[attr-defined]
        pm = item.funcargs["performance_monitor"]  # 已注入的 fixture 实例
        scenario_id = item.name
        with pm.monitor(scenario_id):
            yield
    else:
        yield
```

使用示例：

```python
def test_scenario_1_2_large_file(api_client, performance_monitor):
    """Scenario-1.2：大文件导入"""
    with performance_monitor.monitor("Scenario-1.2"):
        _ = api_client.ingest_start(source_dir="large_file.html", workspace_dir=".")

    metrics = performance_monitor.get_metrics("Scenario-1.2")
    assert metrics["duration"] < 300, f"响应时间{metrics['duration']:.1f}秒超过5分钟"
    assert metrics["memory"]["peak"] < 500, f"内存峰值{metrics['memory']['peak']:.1f}MB超过500MB"
```

收集的指标：
- duration（秒）；memory.start/end/peak/delta（MB）；cpu.start/peak（%）。

---

## 6. 配置管理

### 6.1 测试配置文件

```python
# test_config.py
from __future__ import annotations

from pydantic_settings import BaseSettings

class TestConfig(BaseSettings):
    # 服务地址
    REDIS_URL: str = "redis://localhost:6379/1"
    MONGODB_URL: str = "mongodb://localhost:27017/test_TelegramCuration"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    CHROMADB_URL: str = "http://localhost:8001"
    FASTAPI_URL: str = "http://localhost:8000"

    # 测试配置
    RANDOM_SEED: int = 42
    TIMEOUT: int = 300
    MAX_WORKERS: int = 100
    RETRY_TIMES: int = 3

    # 大模型配置
    MOCK_LLM: bool = True
    LLM_RESPONSE_DELAY: float = 0.1
    OPENAI_API_KEY: str = "sk-test"  # 仅在 MOCK_LLM=False 时使用

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/test_run.log"

    class Config:
        env_prefix = "TEST_"
        env_file = ".env.test"
```

### 6.2 环境变量（.env.test）

```env
TEST_MOCK_LLM=True
TEST_RANDOM_SEED=42
TEST_TIMEOUT=300
TEST_LOG_LEVEL=DEBUG
```

---

## 7. pytest 配置

### 7.1 pytest.ini

```ini
[pytest]
# 基础配置
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = test_cases

# 插件配置
addopts = 
    --json-report \
    --json-report-file=results/report.json \
    --html=results/report.html \
    --self-contained-html \
    --timeout=300 \
    --verbose \
    --capture=no \
    --strict-markers

# 日志配置
log_cli = true
log_cli_level = INFO
log_file = logs/pytest.log
log_file_level = DEBUG

# 标记
markers =
    p0: Priority 0 - Core scenarios
    p1: Priority 1 - Important scenarios
    p2: Priority 2 - Supplementary scenarios
    p3: Priority 3 - Edge cases
    slow: Slow tests (> 1 minute)
    concurrent: Concurrent tests
    perf: Performance tests

# 超时
timeout_method = thread
```

---

## 8. 使用指南

### 8.1 运行测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行所有 P0 场景
pytest -m p0

# 运行 P0 与 P1
pytest -m "p0 or p1"

# 并行运行（4 个 worker）
pytest -n 4

# 指定随机种子（复现测试）
TEST_RANDOM_SEED=123456 pytest

# 生成详细报告
pytest --html=results/report.html
```

### 8.2 调试测试

```bash
# 运行单个测试
pytest test_cases/test_01_功能覆盖.py::test_scenario_1_1__json_small_ingest

# 显示详细输出
pytest -vv -s

# 在第一个失败处停止
pytest -x

# 只运行失败的测试
pytest --lf
```

---

工作流版本：2.0 | 最后更新：2025-10-11

（以上技术决策遵循 SimulationTestingConstitution、结合 TelegramCuration 模块的测试场景与计划，提供了可执行、可复现的随机化/并发/模拟/性能监控实现与完整依赖清单。）

