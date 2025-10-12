---
description: 测试技术决策工作流 - 定义测试实现的技术细节
version: 2.0
language: zh-CN
upstream: TestPlanGeneration_V2
downstream: TestExecuteAndDebug_V2
scripts:
  ps: CodexFeatured/Scripts/get-test-context.ps1 -Json
---

# TestTechDecisions - 测试技术决策工作流

## 工作流概述

**目标**：基于测试计划，定义测试实现的具体技术细节。

**核心问题**：
- 用什么测试框架和工具？
- 如何实现随机化？（数据、顺序、延迟、失败注入）
- 如何实现并发测试？
- 如何模拟外部依赖？（大模型API、网络超时）
- 如何控制随机种子？（确保可复现）
- 如何收集性能指标？

**核心原则**：
- 遵循测试宪法（SimulationTestingConstitution）
- 技术选择要明确版本号
- 随机化策略要可执行、可复现
- 所有技术决策都要有代码示例

**输入**：
- 测试场景文档 `Kobe/SimulationTest/{MODULE_NAME}_testscenarios.md`
- 测试计划文档 `Kobe/SimulationTest/{MODULE_NAME}_testplan.md`

**输出**：
- 技术决策文档 `Kobe/SimulationTest/{MODULE_NAME}_testtech.md`

---

## 参数定义

```yaml
OUTPUT_DIR: "D:/AI_Projects/Kobe/SimulationTest"
MODULE_NAME: "{{RUNTIME_RESOLVE}}"
SCENARIO_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testscenarios.md"
TESTPLAN_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testplan.md"
TESTTECH_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testtech.md"
```

---

## 执行流程

### 步骤1：加载测试场景和测试计划

**动作**：
1. **自动定位文档**：
   - 扫描 `${OUTPUT_DIR}` 下所有 *_testscenarios.md 和 *_testplan.md 文件
   - 按修改时间倒序，选择最新的
   → 如果未找到：ERROR "未找到测试场景或测试计划文档"

2. **读取测试场景文档**：
   - 提取所有随机化策略类型：
     * 数据量随机
     * 顺序随机
     * 延迟随机
     * 失败注入
     * 内容随机
     * ...
   - 提取并发需求：
     * 10并发、100并发
   - 提取性能指标：
     * 响应时间、内存占用、CPU使用率

3. **读取测试计划文档**：
   - 提取目录结构
   - 提取数据生成器需求
   - 提取依赖服务清单

4. **读取测试宪法**：
   - 读取 `CodexFeatured/Common/SimulationTestingConstitution.yaml`
   - 提取强制性约束（如必须使用pytest）

5. **更新进度**：测试文档加载完成

**输出**：
- 随机化策略清单
- 并发需求清单
- 性能指标清单
- 依赖服务清单

---

### 步骤2：确定测试框架和核心依赖

**动作**：
1. **确定测试框架**（遵循测试宪法）：

   ```yaml
   core_framework:
     pytest: 7.4.3
     reason: 测试宪法强制要求，业界标准
   ```

2. **确定pytest插件**：

   | 插件 | 版本 | 用途 | 必需性 |
   |------|------|------|--------|
   | pytest-asyncio | 0.21.1 | 异步测试支持 | 必需（项目使用async） |
   | pytest-timeout | 2.2.0 | 超时控制 | 必需（防止测试卡死） |
   | pytest-json-report | 1.5.0 | JSON报告 | 必需（结构化报告） |
   | pytest-html | 4.1.1 | HTML报告 | 必需（可视化报告） |
   | pytest-xdist | 3.5.0 | 并行执行 | 推荐（提高效率） |
   | pytest-repeat | 0.9.3 | 重复执行 | 可选（稳定性测试） |
   | pytest-dependency | 0.5.1 | 依赖管理 | 推荐（场景依赖） |

3. **确定HTTP客户端**：

   ```yaml
   http_client:
     requests: 2.31.0
     reason: 简单易用，同步调用
     alternatives:
       httpx: 0.25.2  # 如果需要异步HTTP调用
   ```

4. **确定数据库客户端**（基于项目使用的服务）：

   | 依赖 | 版本 | 用途 |
   |------|------|------|
   | pymongo | 4.6.1 | MongoDB客户端 |
   | redis | 5.0.1 | Redis客户端 |
   | pika | 1.3.2 | RabbitMQ客户端（检查状态） |

5. **确定随机化库**：

   | 依赖 | 版本 | 用途 |
   |------|------|------|
   | faker | 20.1.0 | 生成假数据（姓名、文本等） |
   | random | 内置 | 基础随机化 |

6. **确定性能监控库**：

   | 依赖 | 版本 | 用途 |
   |------|------|------|
   | psutil | 5.9.6 | CPU、内存监控 |
   | pytest-benchmark | 4.0.0 | 性能基准测试 |

7. **确定日志库**：

   ```yaml
   logging:
     structlog: 23.2.0
     reason: 结构化日志，与项目一致
   ```

8. **生成requirements.txt**：

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

   # HTTP客户端
   requests==2.31.0
   httpx==0.25.2

   # 数据库客户端
   pymongo==4.6.1
   redis==5.0.1
   pika==1.3.2

   # 随机化和数据生成
   faker==20.1.0

   # 性能监控
   psutil==5.9.6

   # 日志
   structlog==23.2.0

   # 类型检查（可选）
   pydantic==2.5.3
   pydantic-settings==2.1.0
   ```

9. **更新进度**：测试框架和依赖确定完成

**输出**：
- 核心框架清单
- pytest插件清单
- 所有依赖清单（包含版本号和用途）
- requirements.txt内容

---

### 步骤3：定义随机化技术实现

**动作**：
1. **数据量随机化实现**：

   ```python
   # test_data/generators/random_utils.py
   
   import random
   import os
   
   # 全局随机种子（从环境变量读取，确保可复现）
   RANDOM_SEED = int(os.getenv("TEST_RANDOM_SEED", random.randint(1, 1000000)))
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
           >>> count = random_count(10, 20)
           >>> assert 10 <= count <= 20
       """
       return random.randint(min_val, max_val)
   
   def random_count_with_distribution(
       small_prob: float = 0.3,
       medium_prob: float = 0.5,
       large_prob: float = 0.2
   ) -> str:
       """
       按概率分布返回数据规模
       
       Args:
           small_prob: 小数据量概率（10-20条）
           medium_prob: 中数据量概率（100-500条）
           large_prob: 大数据量概率（10000+条）
       
       Returns:
           'small', 'medium', 'large'
       
       Example:
           >>> size = random_count_with_distribution()
           >>> assert size in ['small', 'medium', 'large']
       """
       rand = random.random()
       if rand < small_prob:
           return 'small'
       elif rand < small_prob + medium_prob:
           return 'medium'
       else:
           return 'large'
   ```

2. **顺序随机化实现**：

   ```python
   def random_shuffle(items: list) -> list:
       """
       随机打乱列表顺序（不修改原列表）
       
       Args:
           items: 原始列表
       
       Returns:
           打乱后的新列表
       
       Example:
           >>> original = [1, 2, 3, 4, 5]
           >>> shuffled = random_shuffle(original)
           >>> assert len(shuffled) == len(original)
           >>> assert set(shuffled) == set(original)
       """
       shuffled = items.copy()
       random.shuffle(shuffled)
       return shuffled
   ```

3. **延迟随机化实现**：

   ```python
   import time
   
   def random_delay(min_sec: float = 0, max_sec: float = 5):
       """
       随机延迟（模拟网络延迟）
       
       Args:
           min_sec: 最小延迟（秒）
           max_sec: 最大延迟（秒）
       
       Example:
           >>> random_delay(0.1, 0.5)  # 延迟0.1-0.5秒
       """
       delay = random.uniform(min_sec, max_sec)
       time.sleep(delay)
   ```

4. **失败注入实现**：

   ```python
   class FailureInjector:
       """失败注入器，用于模拟各种失败场景"""
       
       @staticmethod
       def should_inject_failure(probability: float = 0.1) -> bool:
           """
           根据概率决定是否注入失败
           
           Args:
               probability: 失败概率（0.0-1.0）
           
           Returns:
               True表示应该注入失败
           
           Example:
               >>> if FailureInjector.should_inject_failure(0.1):
               >>>     raise TimeoutError("Simulated timeout")
           """
           return random.random() < probability
       
       @staticmethod
       def inject_api_failure(probability: float = 0.1):
           """
           API失败注入装饰器
           
           Args:
               probability: 失败概率
           
           Example:
               >>> @FailureInjector.inject_api_failure(0.1)
               >>> def call_api():
               >>>     return requests.post(...)
           """
           def decorator(func):
               def wrapper(*args, **kwargs):
                   if FailureInjector.should_inject_failure(probability):
                       failure_type = random.choice([
                           'timeout',
                           'connection_error',
                           'server_error'
                       ])
                       if failure_type == 'timeout':
                           raise requests.Timeout("Simulated timeout")
                       elif failure_type == 'connection_error':
                           raise requests.ConnectionError("Simulated connection error")
                       else:
                           raise requests.HTTPError("500 Server Error")
                   return func(*args, **kwargs)
               return wrapper
           return decorator
   ```

5. **内容随机化实现**：

   ```python
   from faker import Faker
   
   class MessageGenerator:
       """消息内容生成器"""
       
       def __init__(self, seed: int = None):
           self.faker = Faker('zh_CN')
           if seed:
               self.faker.seed_instance(seed)
       
       def generate_text(
           self,
           min_length: int = 10,
           max_length: int = 500
       ) -> str:
           """
           生成随机文本
           
           Args:
               min_length: 最小长度
               max_length: 最大长度
           
           Returns:
               随机文本
           """
           target_length = random.randint(min_length, max_length)
           text = self.faker.text(max_nb_chars=target_length)
           return text
       
       def generate_emoji(self) -> str:
           """随机生成表情符号"""
           emojis = ['😀', '😁', '😂', '🤣', '😃', '😄', '😅', '😆', '😉', '😊',
                     '😋', '😎', '😍', '😘', '🥰', '😗', '😙', '😚', '🙂', '🤗',
                     '🤩', '🤔', '🤨', '😐', '😑', '😶', '🙄', '😏', '😣', '😥']
           return random.choice(emojis)
       
       def generate_code_block(self) -> str:
           """随机生成代码块"""
           languages = ['python', 'javascript', 'sql', 'bash']
           lang = random.choice(languages)
           
           code_samples = {
               'python': 'def hello():\n    print("Hello, World!")',
               'javascript': 'function hello() {\n  console.log("Hello, World!");\n}',
               'sql': 'SELECT * FROM users WHERE id = 1;',
               'bash': 'echo "Hello, World!"'
           }
           
           return f"```{lang}\n{code_samples[lang]}\n```"
       
       def generate_html_tag(self) -> str:
           """随机生成HTML标签"""
           tags = ['<b>Bold</b>', '<i>Italic</i>', '<a href="#">Link</a>',
                   '<code>code</code>', '<pre>preformatted</pre>']
           return random.choice(tags)
   ```

6. **随机种子管理**：

   ```python
   # conftest.py
   
   import pytest
   import random
   import os
   from faker import Faker
   
   @pytest.fixture(scope="session")
   def random_seed():
       """
       全局随机种子fixture
       
       从环境变量读取种子，如果未设置则随机生成
       确保测试可复现
       """
       seed = int(os.getenv("TEST_RANDOM_SEED", random.randint(1, 1000000)))
       
       # 设置所有随机源的种子
       random.seed(seed)
       
       # 设置faker的种子
       faker_instance = Faker('zh_CN')
       faker_instance.seed_instance(seed)
       
       # 打印种子，便于复现
       print(f"\n=== Random Seed: {seed} ===")
       print(f"To reproduce this test run, use: TEST_RANDOM_SEED={seed}")
       
       return seed
   
   @pytest.fixture(autouse=True)
   def use_random_seed(random_seed):
       """自动应用随机种子到所有测试"""
       pass
   ```

7. **更新进度**：随机化技术实现定义完成

**输出**：
- 所有随机化函数的完整代码
- 随机种子管理方案

---

### 步骤4：定义并发测试技术实现

**动作**：
1. **基于threading的并发实现**（适用于I/O密集型）：

   ```python
   # test_cases/test_03_并发性能.py
   
   import threading
   import queue
   import time
   from typing import List, Dict, Callable
   
   class ConcurrentTester:
       """并发测试器"""
       
       def __init__(self, num_workers: int):
           self.num_workers = num_workers
           self.results = queue.Queue()
       
       def run_concurrent(
           self,
           func: Callable,
           args_list: List[tuple] = None,
           kwargs_list: List[dict] = None
       ) -> List[Dict]:
           """
           并发执行函数
           
           Args:
               func: 要执行的函数
               args_list: 每个worker的位置参数列表
               kwargs_list: 每个worker的关键字参数列表
           
           Returns:
               结果列表，每个结果包含：
               - success: bool
               - result: Any（如果成功）
               - error: str（如果失败）
               - duration: float（执行时间）
               - worker_id: int
           
           Example:
               >>> tester = ConcurrentTester(num_workers=10)
               >>> results = tester.run_concurrent(call_api, args_list=[...])
           """
           if args_list is None:
               args_list = [()] * self.num_workers
           if kwargs_list is None:
               kwargs_list = [{}] * self.num_workers
           
           def worker(worker_id: int, args: tuple, kwargs: dict):
               start_time = time.time()
               try:
                   result = func(*args, **kwargs)
                   duration = time.time() - start_time
                   self.results.put({
                       "success": True,
                       "result": result,
                       "duration": duration,
                       "worker_id": worker_id
                   })
               except Exception as e:
                   duration = time.time() - start_time
                   self.results.put({
                       "success": False,
                       "error": str(e),
                       "duration": duration,
                       "worker_id": worker_id
                   })
           
           # 启动所有线程
           threads = []
           for i in range(self.num_workers):
               args = args_list[i] if i < len(args_list) else ()
               kwargs = kwargs_list[i] if i < len(kwargs_list) else {}
               t = threading.Thread(
                   target=worker,
                   args=(i, args, kwargs),
                   daemon=True
               )
               threads.append(t)
               t.start()
           
           # 等待所有线程完成
           for t in threads:
               t.join()
           
           # 收集结果
           results = []
           while not self.results.empty():
               results.append(self.results.get())
           
           return results
       
       def analyze_results(self, results: List[Dict]) -> Dict:
           """
           分析并发测试结果
           
           Returns:
               统计信息：
               - total: 总请求数
               - success_count: 成功数
               - failure_count: 失败数
               - success_rate: 成功率
               - avg_duration: 平均响应时间
               - p50_duration: P50响应时间
               - p95_duration: P95响应时间
               - p99_duration: P99响应时间
           """
           total = len(results)
           success_count = sum(1 for r in results if r['success'])
           failure_count = total - success_count
           success_rate = success_count / total if total > 0 else 0
           
           durations = sorted([r['duration'] for r in results])
           avg_duration = sum(durations) / len(durations) if durations else 0
           
           p50_index = int(len(durations) * 0.50)
           p95_index = int(len(durations) * 0.95)
           p99_index = int(len(durations) * 0.99)
           
           return {
               "total": total,
               "success_count": success_count,
               "failure_count": failure_count,
               "success_rate": success_rate,
               "avg_duration": avg_duration,
               "p50_duration": durations[p50_index] if durations else 0,
               "p95_duration": durations[p95_index] if durations else 0,
               "p99_duration": durations[p99_index] if durations else 0,
           }
   ```

2. **使用示例**：

   ```python
   @pytest.mark.p1
   @pytest.mark.timeout(600)
   def test_scenario_3_1_10_concurrent_users(api_client, test_data_dir):
       """
       Scenario-3.1：10并发用户
       """
       tester = ConcurrentTester(num_workers=10)
       
       # 为每个worker准备不同的测试数据
       args_list = []
       for i in range(10):
           test_file = test_data_dir / f"concurrent_{i}.html"
           # 生成测试文件（每个文件100条消息）
           generate_telegram_html(count=100, output=test_file)
           args_list.append((str(test_file),))
       
       # 并发执行
       results = tester.run_concurrent(
           func=api_client.ingest_telegram_html,
           args_list=args_list
       )
       
       # 分析结果
       stats = tester.analyze_results(results)
       
       # 验收标准
       assert stats['success_rate'] >= 0.95, f"成功率{stats['success_rate']:.2%}低于95%"
       assert stats['avg_duration'] < 60, f"平均响应时间{stats['avg_duration']:.1f}秒超过1分钟"
       assert stats['p95_duration'] < 120, f"P95响应时间{stats['p95_duration']:.1f}秒超过2分钟"
   ```

3. **更新进度**：并发测试技术实现定义完成

**输出**：
- 并发测试器完整代码
- 结果分析函数
- 使用示例

---

### 步骤5：定义模拟（Mock）技术实现

**动作**：
1. **模拟大模型API**：

   ```python
   # utils/mock_llm.py
   
   import time
   import random
   from typing import Dict, Any
   
   class MockLLMAPI:
       """模拟大模型API，用于测试"""
       
       def __init__(
           self,
           response_delay: float = 0.1,
           failure_rate: float = 0.0
       ):
           self.response_delay = response_delay
           self.failure_rate = failure_rate
       
       def chat_completion(
           self,
           messages: list,
           model: str = "gpt-4",
           **kwargs
       ) -> Dict[str, Any]:
           """
           模拟chat completion API
           
           Args:
               messages: 消息列表
               model: 模型名称
           
           Returns:
               模拟的API响应
           """
           # 模拟延迟
           time.sleep(self.response_delay)
           
           # 模拟失败
           if random.random() < self.failure_rate:
               raise Exception("Simulated LLM API failure")
           
           # 模拟响应
           return {
               "id": f"mock-{random.randint(1000, 9999)}",
               "object": "chat.completion",
               "model": model,
               "choices": [{
                   "index": 0,
                   "message": {
                       "role": "assistant",
                       "content": "This is a mock response for testing."
                   },
                   "finish_reason": "stop"
               }],
               "usage": {
                   "prompt_tokens": 10,
                   "completion_tokens": 20,
                   "total_tokens": 30
               }
           }
   ```

2. **在conftest.py中提供mock fixture**：

   ```python
   # conftest.py
   
   @pytest.fixture
   def mock_llm_api(test_config):
       """
       模拟大模型API的fixture
       
       如果配置中MOCK_LLM=True，则返回MockLLMAPI
       否则返回真实的LLM客户端
       """
       if test_config.MOCK_LLM:
           return MockLLMAPI(
               response_delay=test_config.LLM_RESPONSE_DELAY,
               failure_rate=0.0  # 测试时默认不注入失败
           )
       else:
           # 返回真实的LLM客户端
           from openai import OpenAI
           return OpenAI(api_key=test_config.OPENAI_API_KEY)
   ```

3. **模拟网络超时**：

   ```python
   # utils/mock_network.py
   
   import requests
   from unittest.mock import patch
   
   class NetworkMock:
       """网络模拟器"""
       
       @staticmethod
       def inject_timeout(url_pattern: str = None):
           """
           注入网络超时
           
           Args:
               url_pattern: URL模式（如果为None，则对所有请求生效）
           
           Example:
               >>> with NetworkMock.inject_timeout():
               >>>     requests.get("http://example.com")  # 会超时
           """
           def mock_request(*args, **kwargs):
               if url_pattern is None or url_pattern in args[0]:
                   raise requests.Timeout("Simulated timeout")
               return original_request(*args, **kwargs)
           
           original_request = requests.request
           return patch('requests.request', side_effect=mock_request)
   ```

4. **更新进度**：模拟技术实现定义完成

**输出**：
- 大模型API模拟器代码
- 网络超时模拟器代码
- 使用示例

---

### 步骤6：定义性能监控技术实现

**动作**：
1. **性能指标收集器**：

   ```python
   # utils/performance_monitor.py
   
   import psutil
   import time
   from typing import Dict
   from contextlib import contextmanager
   
   class PerformanceMonitor:
       """性能监控器"""
       
       def __init__(self):
           self.process = psutil.Process()
           self.metrics = {}
       
       @contextmanager
       def monitor(self, scenario_id: str):
           """
           性能监控上下文管理器
           
           Args:
               scenario_id: 场景ID
           
           Example:
               >>> monitor = PerformanceMonitor()
               >>> with monitor.monitor("Scenario-1.1"):
               >>>     # 执行测试
               >>>     pass
               >>> metrics = monitor.get_metrics("Scenario-1.1")
           """
           # 记录初始状态
           start_time = time.time()
           start_cpu = self.process.cpu_percent()
           start_memory = self.process.memory_info().rss
           
           peak_memory = start_memory
           peak_cpu = start_cpu
           
           # 启动监控线程
           import threading
           stop_monitoring = threading.Event()
           
           def monitor_loop():
               nonlocal peak_memory, peak_cpu
               while not stop_monitoring.is_set():
                   current_memory = self.process.memory_info().rss
                   current_cpu = self.process.cpu_percent()
                   peak_memory = max(peak_memory, current_memory)
                   peak_cpu = max(peak_cpu, current_cpu)
                   time.sleep(0.1)  # 每100ms采样一次
           
           monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
           monitor_thread.start()
           
           try:
               yield
           finally:
               # 停止监控
               stop_monitoring.set()
               monitor_thread.join(timeout=1)
               
               # 记录最终状态
               end_time = time.time()
               end_memory = self.process.memory_info().rss
               
               # 保存指标
               self.metrics[scenario_id] = {
                   "duration": end_time - start_time,
                   "memory": {
                       "start": start_memory / 1024 / 1024,  # MB
                       "end": end_memory / 1024 / 1024,  # MB
                       "peak": peak_memory / 1024 / 1024,  # MB
                       "delta": (end_memory - start_memory) / 1024 / 1024  # MB
                   },
                   "cpu": {
                       "start": start_cpu,
                       "peak": peak_cpu
                   }
               }
       
       def get_metrics(self, scenario_id: str) -> Dict:
           """获取指定场景的性能指标"""
           return self.metrics.get(scenario_id, {})
       
       def get_all_metrics(self) -> Dict:
           """获取所有场景的性能指标"""
           return self.metrics
   ```

2. **在conftest.py中集成**：

   ```python
   # conftest.py
   
   from utils.performance_monitor import PerformanceMonitor
   
   @pytest.fixture(scope="session")
   def performance_monitor():
       """全局性能监控器"""
       return PerformanceMonitor()
   
   @pytest.hookimpl(tryfirst=True)
   def pytest_runtest_call(item):
       """每个测试执行时自动监控性能"""
       if hasattr(item, 'performance_monitor'):
           scenario_id = item.name
           with item.performance_monitor.monitor(scenario_id):
               yield
       else:
           yield
   ```

3. **使用示例**：

   ```python
   def test_scenario_1_2_large_file(api_client, performance_monitor):
       """Scenario-1.2：大文件导入"""
       with performance_monitor.monitor("Scenario-1.2"):
           result = api_client.ingest_telegram_html("large_file.html")
       
       # 获取性能指标
       metrics = performance_monitor.get_metrics("Scenario-1.2")
       
       # 验收标准
       assert metrics['duration'] < 300, f"响应时间{metrics['duration']:.1f}秒超过5分钟"
       assert metrics['memory']['peak'] < 500, f"内存峰值{metrics['memory']['peak']:.1f}MB超过500MB"
   ```

4. **更新进度**：性能监控技术实现定义完成

**输出**：
- 性能监控器完整代码
- 使用示例

---

### 步骤7：生成技术决策文档

**动作**：
1. **生成完整的技术决策文档**：

   ```markdown
   # 测试技术决策：{MODULE_NAME}

   标识信息：MODULE_NAME={MODULE_NAME}；COUNT_3D={COUNT_3D}；INTENT_TITLE_2_4={INTENT_TITLE_2_4}；生成时间={YYYY-MM-DD HH:mm:ss}

   **参考文档**：
   - 测试场景文档：{SCENARIO_FILE}
   - 测试计划文档：{TESTPLAN_FILE}

   **输出路径**：{TESTTECH_FILE}

   ---

   ## 1. 测试框架和依赖

   ### 1.1 核心框架

   {从步骤2，包含版本号和选择理由}

   ### 1.2 pytest插件

   {从步骤2，表格形式，包含必需性说明}

   ### 1.3 所有依赖清单

   {从步骤2，requirements.txt完整内容}

   ---

   ## 2. 随机化技术实现

   ### 2.1 数据量随机化

   {完整代码，从步骤3}

   ### 2.2 顺序随机化

   {完整代码，从步骤3}

   ### 2.3 延迟随机化

   {完整代码，从步骤3}

   ### 2.4 失败注入

   {完整代码，从步骤3}

   ### 2.5 内容随机化

   {完整代码，从步骤3}

   ### 2.6 随机种子管理

   {完整代码，从步骤3}

   **重要提示**：
   - 所有测试运行时会自动生成并打印随机种子
   - 要复现某次测试，设置环境变量：`TEST_RANDOM_SEED=<seed值>`
   - 示例：`TEST_RANDOM_SEED=123456 pytest test_cases/`

   ---

   ## 3. 并发测试技术

   ### 3.1 并发测试器实现

   {完整代码，从步骤4}

   ### 3.2 使用示例

   {代码示例，从步骤4}

   ---

   ## 4. 模拟（Mock）技术

   ### 4.1 大模型API模拟

   {完整代码，从步骤5}

   ### 4.2 网络超时模拟

   {完整代码，从步骤5}

   ### 4.3 配置

   在测试配置中设置：
   ```python
   MOCK_LLM = True  # 启用模拟
   LLM_RESPONSE_DELAY = 0.1  # 模拟延迟（秒）
   ```

   ---

   ## 5. 性能监控技术

   ### 5.1 性能监控器实现

   {完整代码，从步骤6}

   ### 5.2 使用示例

   {代码示例，从步骤6}

   ### 5.3 收集的指标

   - duration: 执行时间（秒）
   - memory.start: 初始内存（MB）
   - memory.end: 结束内存（MB）
   - memory.peak: 峰值内存（MB）
   - memory.delta: 内存增量（MB）
   - cpu.start: 初始CPU使用率（%）
   - cpu.peak: 峰值CPU使用率（%）

   ---

   ## 6. 配置管理

   ### 6.1 测试配置文件

   ```python
   # test_config.py
   
   from pydantic_settings import BaseSettings
   
   class TestConfig(BaseSettings):
       # 服务地址
       REDIS_URL: str = "redis://localhost:6379/1"
       MONGODB_URL: str = "mongodb://localhost:27017/test_{MODULE_NAME}"
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
       OPENAI_API_KEY: str = "sk-test"  # 仅在MOCK_LLM=False时使用
       
       # 日志配置
       LOG_LEVEL: str = "INFO"
       LOG_FILE: str = "logs/test_run.log"
       
       class Config:
           env_prefix = "TEST_"
           env_file = ".env.test"
   ```

   ### 6.2 环境变量

   创建 `.env.test` 文件：
   ```env
   TEST_MOCK_LLM=True
   TEST_RANDOM_SEED=42
   TEST_TIMEOUT=300
   TEST_LOG_LEVEL=DEBUG
   ```

   ---

   ## 7. pytest配置

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
       --json-report
       --json-report-file=results/report.json
       --html=results/report.html
       --self-contained-html
       --timeout=300
       --verbose
       --capture=no
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
   
   # 超时
   timeout_method = thread
   ```

   ---

   ## 8. 使用指南

   ### 8.1 运行测试

   ```bash
   # 安装依赖
   pip install -r requirements.txt
   
   # 运行所有P0场景
   pytest -m p0
   
   # 运行所有P0和P1场景
   pytest -m "p0 or p1"
   
   # 并行运行（4个worker）
   pytest -n 4
   
   # 指定随机种子（复现测试）
   TEST_RANDOM_SEED=123456 pytest
   
   # 生成详细报告
   pytest --html=results/report.html
   ```

   ### 8.2 调试测试

   ```bash
   # 运行单个测试
   pytest test_cases/test_01_功能覆盖.py::test_scenario_1_1
   
   # 显示详细输出
   pytest -vv -s
   
   # 在第一个失败处停止
   pytest -x
   
   # 只运行失败的测试
   pytest --lf
   ```

   ---

   **工作流版本**：2.0 | **生成时间**：{YYYY-MM-DD HH:mm:ss}
   ```

2. **写入文件**：
   ```
   写入文件：${TESTTECH_FILE}
   编码：UTF-8（无BOM）
   ```

3. **更新进度**：技术决策文档生成完成

**输出文件**：`${TESTTECH_FILE}`

---

## 进度跟踪

**阶段状态**：
- [ ] 步骤1：测试文档加载完成
- [ ] 步骤2：测试框架和依赖确定完成
- [ ] 步骤3：随机化技术实现定义完成
- [ ] 步骤4：并发测试技术实现定义完成
- [ ] 步骤5：模拟技术实现定义完成
- [ ] 步骤6：性能监控技术实现定义完成
- [ ] 步骤7：技术决策文档生成完成

---

## 验收标准

**输出文件要求**：
- [ ] 输出路径符合 `${TESTTECH_FILE}`
- [ ] 文件编码为 UTF-8（无BOM）
- [ ] 文件大小 > 20KB（确保详细）

**技术决策要求**：
- [ ] 所有依赖包含版本号
- [ ] 所有技术决策都有完整代码示例
- [ ] 随机化策略可执行、可复现
- [ ] 包含requirements.txt完整内容
- [ ] 包含pytest.ini完整配置
- [ ] 包含使用指南

**代码质量要求**：
- [ ] 所有代码示例可直接运行
- [ ] 所有函数包含类型注解和文档字符串
- [ ] 所有类和函数包含使用示例

---

## 错误处理

**ERROR 级别**（终止执行）：
- 未找到测试场景或测试计划文档

**WARN 级别**（记录警告但继续）：
- 测试宪法不存在（使用默认配置）

---

## 规范引用

**测试规范**：
- `CodexFeatured/Common/SimulationTestingConstitution.yaml` - 测试专用宪法

**上游工作流**：
- `TestScenarioAnalysis_V2` - 测试场景分析
- `TestPlanGeneration_V2` - 测试计划生成

**下游工作流**：
- `TestExecuteAndDebug_V2` - 测试执行与调试

**工作流版本**：2.0 | **最后更新**：2025-10-11

---

*详细的测试技术决策，包含完整可执行代码*

