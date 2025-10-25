---
description: 测试执行与调试工作流 - 实现测试组件并执行，智能调试
version: 2.0
language: zh-CN
upstream: TestTechDecisions_V2
downstream: (测试完成)
scripts:
  ps: CodexFeatured/Scripts/get-test-context.ps1 -Json
---

# TestExecuteAndDebug - 测试执行与调试工作流

## 工作流概述

**目标**：基于测试计划和技术决策，实现完整的测试组件，执行测试，并在失败时进行智能调试。

**两个核心阶段**：
1. **阶段1：测试实现**（创建测试组件，包含完整的目录、代码、配置）
2. **阶段2：执行与调试**（运行测试，失败时从源头分析问题）

**Debugging核心原则**（关键！）：
- **不是死磕单个bug**：不是反复尝试修改某行代码
- **从源头考虑问题**：从项目背景、架构、配置、基础设施整体分析
- **理解开发意图**：读取需求文档，理解为什么要开发这个功能
- **系统性诊断**：检查配置、环境、依赖服务、代码逻辑、基础设施
- **根本性解决方案**：解决根本原因，不是临时修补

**输入**：
- 测试场景文档 `Kobe/SimulationTest/{MODULE_NAME}_testscenarios.md`
- 测试计划文档 `Kobe/SimulationTest/{MODULE_NAME}_testplan.md`
- 技术决策文档 `Kobe/SimulationTest/{MODULE_NAME}_testtech.md`

**输出**：
- 完整的测试组件目录 `Kobe/SimulationTest/{MODULE_NAME}_testplan/`
- 测试报告 `results/report.html` 和 `results/report.json`
- 日志文件 `logs/*.log`

---

## 参数定义

```yaml
OUTPUT_DIR: "D:/AI_Projects/Kobe/SimulationTest"
MODULE_NAME: "{{RUNTIME_RESOLVE}}"
SCENARIO_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testscenarios.md"
TESTPLAN_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testplan.md"
TESTTECH_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testtech.md"
TESTPLAN_DIR: "${OUTPUT_DIR}/${MODULE_NAME}_testplan"
```

---

## 阶段1：测试实现

### 步骤1.1：加载所有测试文档

**动作**：
1. **自动定位文档**：
   - 扫描 `${OUTPUT_DIR}` 下所有测试文档
   - 验证三个文档都存在：
     * testscenarios.md
     * testplan.md
     * testtech.md
   → 如果任何一个不存在：ERROR "缺少必需的测试文档"

2. **读取测试场景文档**：
   - 提取所有场景的详细信息：
     * 场景ID、名称、描述
     * 输入、操作、预期输出
     * 验收标准
     * 随机化策略
     * 依赖关系

3. **读取测试计划文档**：
   - 提取目录结构
   - 提取测试文件映射（维度→文件名）
   - 提取conftest.py fixtures清单
   - 提取数据生成器设计

4. **读取技术决策文档**：
   - 提取requirements.txt
   - 提取所有技术实现代码：
     * 随机化函数
     * 并发测试器
     * 模拟器
     * 性能监控器
   - 提取pytest.ini配置

5. **加载项目约束**：
   - 读取 `CodexFeatured/Common/SimulationTestingConstitution.yaml`
   - 读取 `CodexFeatured/Common/BackendConstitution.yaml`（了解项目技术栈）

6. **加载开发文档**（关键！为Debugging准备）：
   - 读取 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/DemandDescription.md`
   - 读取 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/DevPlan.md`
   - 读取 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/Tech_Decisions.md`
   - 目的：理解开发意图，便于调试时从源头考虑问题

7. **更新进度**：所有文档加载完成

**输出**：
- 所有场景的完整信息
- 目录结构设计
- 技术实现代码
- 项目约束和开发文档

---

### 步骤1.2：创建测试组件目录结构

**动作**：
1. **创建完整的目录树**（基于测试计划）：

   ```
   创建目录：${TESTPLAN_DIR}/
   创建目录：${TESTPLAN_DIR}/test_cases/
   创建目录：${TESTPLAN_DIR}/test_data/
   创建目录：${TESTPLAN_DIR}/test_data/generators/
   创建目录：${TESTPLAN_DIR}/test_data/fixtures/
   创建目录：${TESTPLAN_DIR}/results/
   创建目录：${TESTPLAN_DIR}/logs/
   创建目录：${TESTPLAN_DIR}/logs/by_scenario/
   创建目录：${TESTPLAN_DIR}/utils/
   ```

2. **创建空的__init__.py文件**：
   ```
   创建文件：${TESTPLAN_DIR}/test_cases/__init__.py
   创建文件：${TESTPLAN_DIR}/test_data/__init__.py
   创建文件：${TESTPLAN_DIR}/test_data/generators/__init__.py
   创建文件：${TESTPLAN_DIR}/utils/__init__.py
   ```

3. **创建.gitkeep和README.md**：
   ```
   创建文件：${TESTPLAN_DIR}/results/.gitkeep
   创建文件：${TESTPLAN_DIR}/logs/.gitkeep
   创建文件：${TESTPLAN_DIR}/results/README.md（说明测试结果存储）
   创建文件：${TESTPLAN_DIR}/logs/README.md（说明日志存储）
   ```

4. **更新进度**：目录结构创建完成

**输出**：完整的目录树

---

### 步骤1.3：生成配置文件

**动作**：
1. **生成requirements.txt**：
   ```
   从技术决策文档提取完整的requirements.txt内容
   写入文件：${TESTPLAN_DIR}/requirements.txt
   ```

2. **生成pytest.ini**：
   ```
   从技术决策文档提取pytest.ini配置
   写入文件：${TESTPLAN_DIR}/pytest.ini
   ```

3. **生成test_config.py**：
   ```python
   # test_config.py
   
   from pydantic_settings import BaseSettings
   
   class TestConfig(BaseSettings):
       # 从技术决策文档提取完整的TestConfig类
       ...
   ```
   ```
   写入文件：${TESTPLAN_DIR}/test_config.py
   ```

4. **生成.env.test**：
   ```env
   # 从技术决策文档提取环境变量示例
   TEST_MOCK_LLM=True
   TEST_RANDOM_SEED=42
   ...
   ```
   ```
   写入文件：${TESTPLAN_DIR}/.env.test
   ```

5. **更新进度**：配置文件生成完成

**输出**：
- requirements.txt
- pytest.ini
- test_config.py
- .env.test

---

### 步骤1.4：生成工具模块

**动作**：
1. **生成test_data/generators/random_utils.py**：
   ```
   从技术决策文档第2节提取所有随机化函数
   写入文件：${TESTPLAN_DIR}/test_data/generators/random_utils.py
   ```

2. **生成test_data/generators/message_generator.py**：
   ```python
   # message_generator.py
   
   from faker import Faker
   import random
   from .random_utils import RANDOM_SEED
   
   class MessageGenerator:
       # 从技术决策文档提取MessageGenerator类
       ...
   ```
   ```
   写入文件：${TESTPLAN_DIR}/test_data/generators/message_generator.py
   ```

3. **生成test_data/generators/html_generator.py**：
   ```python
   # html_generator.py
   
   from .message_generator import MessageGenerator
   from typing import List, Dict
   
   class TelegramHTMLGenerator:
       """生成Telegram HTML格式的测试数据"""
       
       def __init__(self, seed: int = None):
           self.message_gen = MessageGenerator(seed)
       
       def generate_html(
           self,
           count: int = None,
           include_special: bool = False
       ) -> str:
           """
           生成HTML文件内容
           
           Args:
               count: 消息数量（None表示随机）
               include_special: 是否包含特殊字符
           """
           if count is None:
               from .random_utils import random_count
               count = random_count(10, 20)
           
           messages = []
           for i in range(count):
               if include_special and i % 5 == 0:
                   # 每5条消息插入一条特殊字符消息
                   msg = self.message_gen.generate_text(10, 50)
                   msg += " " + self.message_gen.generate_emoji()
               else:
                   msg = self.message_gen.generate_text(10, 500)
               
               messages.append({
                   "id": i + 1,
                   "sender": self.message_gen.faker.name(),
                   "text": msg,
                   "timestamp": self.message_gen.faker.date_time_this_month().isoformat()
               })
           
           # 渲染为Telegram HTML格式
           html = self._render_telegram_html(messages)
           return html
       
       def _render_telegram_html(self, messages: List[Dict]) -> str:
           """将消息列表渲染为Telegram HTML格式"""
           html_parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>']
           html_parts.append('<div class="history">')
           
           for msg in messages:
               html_parts.append(f'<div class="message" data-id="{msg["id"]}">')
               html_parts.append(f'<div class="from_name">{msg["sender"]}</div>')
               html_parts.append(f'<div class="text">{msg["text"]}</div>')
               html_parts.append(f'<div class="date">{msg["timestamp"]}</div>')
               html_parts.append('</div>')
           
           html_parts.append('</div></body></html>')
           return '\n'.join(html_parts)
   ```
   ```
   写入文件：${TESTPLAN_DIR}/test_data/generators/html_generator.py
   ```

4. **生成utils/api_client.py**：
   ```python
   # utils/api_client.py
   
   import requests
   import time
   from typing import Dict, Any
   from test_config import TestConfig
   
   class APIClient:
       """API客户端，用于测试"""
       
       def __init__(self, config: TestConfig):
           self.config = config
           self.base_url = config.FASTAPI_URL
           self.timeout = config.TIMEOUT
       
       def ingest_telegram_html(
           self,
           file_path: str,
           source_dir: str = None,
           workspace_dir: str = None
       ) -> Dict[str, Any]:
           """
           调用Telegram HTML导入API
           
           Args:
               file_path: HTML文件路径
               source_dir: 源目录
               workspace_dir: 工作目录
           
           Returns:
               API响应
           """
           url = f"{self.base_url}/api/telegram-curation/ingest/start"
           
           payload = {
               "sourceDir": source_dir or str(Path(file_path).parent),
               "workspaceDir": workspace_dir or "outputs/"
           }
           
           response = requests.post(url, json=payload, timeout=self.timeout)
           response.raise_for_status()
           
           result = response.json()
           task_id = result.get("task_id")
           
           # 轮询任务状态
           return self._wait_for_task(task_id)
       
       def _wait_for_task(self, task_id: str) -> Dict[str, Any]:
           """轮询任务状态直到完成"""
           max_attempts = self.config.TIMEOUT // 2
           
           for attempt in range(max_attempts):
               response = requests.get(
                   f"{self.base_url}/api/tasks/{task_id}",
                   timeout=10
               )
               response.raise_for_status()
               
               result = response.json()
               status = result.get("status")
               
               if status == "completed":
                   return result
               elif status == "failed":
                   raise Exception(f"Task failed: {result.get('error')}")
               
               time.sleep(2)
           
           raise TimeoutError(f"Task {task_id} timeout after {self.config.TIMEOUT}s")
   ```
   ```
   写入文件：${TESTPLAN_DIR}/utils/api_client.py
   ```

5. **生成utils/db_client.py**：
   ```python
   # utils/db_client.py
   
   from pymongo import MongoClient
   import redis
   from test_config import TestConfig
   
   class DBClient:
       """数据库客户端，用于验证测试结果"""
       
       def __init__(self, config: TestConfig):
           self.config = config
           self.mongo_client = MongoClient(config.MONGODB_URL)
           self.redis_client = redis.from_url(config.REDIS_URL)
           
           # 获取MongoDB数据库
           db_name = config.MONGODB_URL.split('/')[-1]
           self.db = self.mongo_client[db_name]
       
       def count_messages(self, collection: str = "chat_messages") -> int:
           """统计MongoDB中的消息数量"""
           return self.db[collection].count_documents({})
       
       def clear_messages(self, collection: str = "chat_messages"):
           """清空MongoDB集合"""
           self.db[collection].delete_many({})
       
       def get_redis_keys(self, pattern: str = "*") -> list:
           """获取Redis中的键"""
           return [key.decode() for key in self.redis_client.keys(pattern)]
       
       def clear_redis(self):
           """清空Redis"""
           self.redis_client.flushdb()
   ```
   ```
   写入文件：${TESTPLAN_DIR}/utils/db_client.py
   ```

6. **生成utils/service_checker.py**：
   ```python
   # utils/service_checker.py
   
   import requests
   import redis
   import pymongo
   import pika
   from test_config import TestConfig
   
   class ServiceChecker:
       """服务状态检查器"""
       
       def __init__(self, config: TestConfig):
           self.config = config
       
       def check_redis(self) -> bool:
           """检查Redis"""
           try:
               r = redis.from_url(self.config.REDIS_URL, socket_connect_timeout=5)
               r.ping()
               return True
           except:
               return False
       
       def check_mongodb(self) -> bool:
           """检查MongoDB"""
           try:
               client = pymongo.MongoClient(
                   self.config.MONGODB_URL,
                   serverSelectionTimeoutMS=5000
               )
               client.server_info()
               return True
           except:
               return False
       
       def check_rabbitmq(self) -> bool:
           """检查RabbitMQ"""
           try:
               connection = pika.BlockingConnection(
                   pika.URLParameters(self.config.RABBITMQ_URL)
               )
               connection.close()
               return True
           except:
               return False
       
       def check_fastapi(self) -> bool:
           """检查FastAPI"""
           try:
               response = requests.get(
                   f"{self.config.FASTAPI_URL}/health",
                   timeout=5
               )
               return response.status_code == 200
           except:
               return False
       
       def check_all(self) -> dict:
           """检查所有服务"""
           return {
               "redis": self.check_redis(),
               "mongodb": self.check_mongodb(),
               "rabbitmq": self.check_rabbitmq(),
               "fastapi": self.check_fastapi()
           }
   ```
   ```
   写入文件：${TESTPLAN_DIR}/utils/service_checker.py
   ```

7. **生成utils/performance_monitor.py**：
   ```
   从技术决策文档第5节提取PerformanceMonitor类
   写入文件：${TESTPLAN_DIR}/utils/performance_monitor.py
   ```

8. **更新进度**：工具模块生成完成

**输出**：
- random_utils.py
- message_generator.py
- html_generator.py
- api_client.py
- db_client.py
- service_checker.py
- performance_monitor.py

---

### 步骤1.5：生成conftest.py

**动作**：
1. **生成完整的conftest.py**：

   ```python
   # test_cases/conftest.py
   
   import pytest
   import random
   import os
   from pathlib import Path
   from faker import Faker
   
   # 导入配置和工具
   import sys
   sys.path.insert(0, str(Path(__file__).parent.parent))
   
   from test_config import TestConfig
   from utils.api_client import APIClient
   from utils.db_client import DBClient
   from utils.service_checker import ServiceChecker
   from utils.performance_monitor import PerformanceMonitor
   
   # ===== Session级别的fixtures =====
   
   @pytest.fixture(scope="session")
   def test_config():
       """测试配置"""
       return TestConfig()
   
   @pytest.fixture(scope="session")
   def random_seed():
       """
       全局随机种子
       从环境变量读取，确保可复现
       """
       seed = int(os.getenv("TEST_RANDOM_SEED", random.randint(1, 1000000)))
       random.seed(seed)
       
       faker_instance = Faker('zh_CN')
       faker_instance.seed_instance(seed)
       
       print(f"\n{'='*60}")
       print(f"Random Seed: {seed}")
       print(f"To reproduce: TEST_RANDOM_SEED={seed} pytest")
       print(f"{'='*60}\n")
       
       return seed
   
   @pytest.fixture(scope="session", autouse=True)
   def check_services(test_config):
       """
       测试前检查所有依赖服务
       如果服务未启动，给出明确提示
       """
       checker = ServiceChecker(test_config)
       status = checker.check_all()
       
       print(f"\n{'='*60}")
       print("Service Status Check:")
       for service, is_running in status.items():
           status_str = "✓ Running" if is_running else "✗ Not Running"
           print(f"  {service:15s}: {status_str}")
       print(f"{'='*60}\n")
       
       # 如果核心服务未启动，给出启动指令
       if not status['fastapi']:
           pytest.exit("FastAPI is not running. Start it with: uvicorn main:app")
       
       if not status['mongodb']:
           print("WARNING: MongoDB is not running. Some tests may fail.")
       
       if not status['redis']:
           print("WARNING: Redis is not running. Caching tests will fail.")
   
   @pytest.fixture(scope="session")
   def performance_monitor():
       """全局性能监控器"""
       return PerformanceMonitor()
   
   # ===== Function级别的fixtures =====
   
   @pytest.fixture
   def api_client(test_config):
       """API客户端"""
       return APIClient(test_config)
   
   @pytest.fixture
   def db_client(test_config):
       """数据库客户端"""
       client = DBClient(test_config)
       yield client
       # 测试后清理（可选，根据需要启用）
       # client.clear_messages()
       # client.clear_redis()
   
   @pytest.fixture
   def test_data_dir(tmp_path):
       """测试数据目录（临时目录）"""
       data_dir = tmp_path / "test_data"
       data_dir.mkdir()
       return data_dir
   
   @pytest.fixture
   def cleanup(db_client):
       """清理fixture，用于需要清理的测试"""
       yield
       db_client.clear_messages()
       db_client.clear_redis()
   
   # ===== Pytest Hooks =====
   
   def pytest_configure(config):
       """pytest启动时执行"""
       print("\n" + "="*60)
       print("Starting Test Execution")
       print("="*60 + "\n")
   
   def pytest_unconfigure(config):
       """pytest结束时执行"""
       print("\n" + "="*60)
       print("Test Execution Completed")
       print("="*60 + "\n")
   ```
   ```
   写入文件：${TESTPLAN_DIR}/test_cases/conftest.py
   ```

2. **更新进度**：conftest.py生成完成

**输出**：conftest.py

---

### 步骤1.6：生成测试用例文件

**动作**：
1. **按维度生成测试文件**：

   从测试场景文档提取7个维度的场景，为每个维度生成一个测试文件。

   **示例：test_01_功能覆盖.py**：
   
   ```python
   # test_cases/test_01_功能覆盖.py
   """
   维度1：功能覆盖测试
   
   包含场景：
   - Scenario-1.1：正常导入小文件
   - Scenario-1.2：大文件导入
   - Scenario-1.3：空文件导入
   ...
   """
   
   import pytest
   from pathlib import Path
   import sys
   sys.path.insert(0, str(Path(__file__).parent.parent))
   
   from test_data.generators.html_generator import TelegramHTMLGenerator
   
   
   @pytest.mark.p0
   @pytest.mark.timeout(60)
   def test_scenario_1_1_normal_small_file(
       api_client,
       db_client,
       test_data_dir,
       random_seed,
       performance_monitor,
       cleanup
   ):
       """
       Scenario-1.1：正常导入小文件
       
       描述：导入包含10-20条消息的Telegram HTML文件
       优先级：P0
       """
       # 生成测试数据（10-20条消息，随机）
       generator = TelegramHTMLGenerator(seed=random_seed)
       test_file = test_data_dir / "small_file.html"
       
       html_content = generator.generate_html(count=None)  # None表示随机数量
       test_file.write_text(html_content, encoding='utf-8')
       
       # 执行测试（性能监控）
       with performance_monitor.monitor("Scenario-1.1"):
           result = api_client.ingest_telegram_html(str(test_file))
       
       # 验收标准
       assert result['status'] == 'completed', f"任务未完成：{result.get('status')}"
       
       message_count = db_client.count_messages()
       assert 10 <= message_count <= 20, f"消息数量{message_count}不在10-20范围内"
       
       metrics = performance_monitor.get_metrics("Scenario-1.1")
       assert metrics['duration'] < 30, f"响应时间{metrics['duration']:.1f}秒超过30秒"
   
   
   @pytest.mark.p1
   @pytest.mark.timeout(600)
   @pytest.mark.dependency(depends=["test_scenario_1_1_normal_small_file"])
   def test_scenario_1_2_large_file(
       api_client,
       db_client,
       test_data_dir,
       random_seed,
       performance_monitor,
       cleanup
   ):
       """
       Scenario-1.2：大文件导入
       
       描述：导入包含10000条消息的Telegram HTML文件
       优先级：P1
       依赖：Scenario-1.1
       """
       # 生成大文件（随机9000-11000条）
       from test_data.generators.random_utils import random_count
       count = random_count(9000, 11000)
       
       generator = TelegramHTMLGenerator(seed=random_seed)
       test_file = test_data_dir / "large_file.html"
       
       html_content = generator.generate_html(count=count)
       test_file.write_text(html_content, encoding='utf-8')
       
       # 执行测试
       with performance_monitor.monitor("Scenario-1.2"):
           result = api_client.ingest_telegram_html(str(test_file))
       
       # 验收标准
       assert result['status'] == 'completed'
       
       message_count = db_client.count_messages()
       assert 9000 <= message_count <= 11000
       
       metrics = performance_monitor.get_metrics("Scenario-1.2")
       assert metrics['duration'] < 300, f"响应时间{metrics['duration']:.1f}秒超过5分钟"
       assert metrics['memory']['peak'] < 500, f"内存峰值{metrics['memory']['peak']:.1f}MB超过500MB"
   
   
   @pytest.mark.p1
   @pytest.mark.timeout(60)
   def test_scenario_1_3_empty_file(
       api_client,
       db_client,
       test_data_dir,
       cleanup
   ):
       """
       Scenario-1.3：空文件导入
       
       描述：导入空的HTML文件（0条消息）
       优先级：P1
       """
       # 生成空文件
       generator = TelegramHTMLGenerator()
       test_file = test_data_dir / "empty_file.html"
       
       html_content = generator.generate_html(count=0)
       test_file.write_text(html_content, encoding='utf-8')
       
       # 执行测试（应该不抛出异常）
       result = api_client.ingest_telegram_html(str(test_file))
       
       # 验收标准
       assert result['status'] in ['completed', 'no_data']
       assert db_client.count_messages() == 0
   
   # ...继续为该维度的其他场景生成测试函数
   ```
   
   ```
   写入文件：${TESTPLAN_DIR}/test_cases/test_01_功能覆盖.py
   ```

2. **为其他6个维度生成测试文件**：
   - test_02_数据多样性.py
   - test_03_并发性能.py（使用ConcurrentTester）
   - test_04_配置分支.py
   - test_05_异常恢复.py（使用FailureInjector）
   - test_06_依赖服务.py
   - test_07_真实场景.py

3. **更新进度**：测试用例文件生成完成

**输出**：7个测试文件（每个包含该维度的所有场景）

---

### 步骤1.7：生成测试执行器和文档

**动作**：
1. **生成run_tests.py**：

   ```python
   #!/usr/bin/env python3
   """
   测试执行器
   
   功能：
   - 检查环境
   - 准备固定测试数据
   - 执行pytest
   - 生成报告
   """
   
   import sys
   import subprocess
   from pathlib import Path
   from utils.service_checker import ServiceChecker
   from test_config import TestConfig
   
   def check_environment():
       """检查环境"""
       config = TestConfig()
       checker = ServiceChecker(config)
       status = checker.check_all()
       
       print("="*60)
       print("Environment Check:")
       all_ok = True
       for service, is_running in status.items():
           status_str = "✓" if is_running else "✗"
           print(f"  [{status_str}] {service}")
           if not is_running and service in ['fastapi', 'mongodb']:
               all_ok = False
       print("="*60)
       
       return all_ok
   
   def prepare_fixtures():
       """准备固定测试数据"""
       print("\nPreparing test fixtures...")
       from test_data.generators.html_generator import TelegramHTMLGenerator
       
       fixtures_dir = Path("test_data/fixtures")
       fixtures_dir.mkdir(parents=True, exist_ok=True)
       
       generator = TelegramHTMLGenerator(seed=42)
       
       # 生成小文件样本
       small_file = fixtures_dir / "sample_small.html"
       if not small_file.exists():
           html = generator.generate_html(count=18)
           small_file.write_text(html, encoding='utf-8')
           print(f"  Created: {small_file}")
       
       # 生成空文件样本
       empty_file = fixtures_dir / "sample_empty.html"
       if not empty_file.exists():
           html = generator.generate_html(count=0)
           empty_file.write_text(html, encoding='utf-8')
           print(f"  Created: {empty_file}")
       
       print("Fixtures ready.\n")
   
   def run_pytest(args=None):
       """运行pytest"""
       cmd = ["pytest", "test_cases/"]
       if args:
           cmd.extend(args)
       
       print(f"Running: {' '.join(cmd)}\n")
       result = subprocess.run(cmd)
       return result.returncode
   
   def main():
       """主函数"""
       import argparse
       parser = argparse.ArgumentParser(description="Test Executor")
       parser.add_argument("--check-only", action="store_true", help="Only check environment")
       parser.add_argument("--priority", type=str, help="Run specific priority (p0, p1, p2, p3)")
       parser.add_argument("--parallel", type=int, help="Number of parallel workers")
       args, unknown = parser.parse_known_args()
       
       # 检查环境
       if not check_environment():
           print("\n[ERROR] Core services are not running. Please start them first.")
           return 1
       
       if args.check_only:
           return 0
       
       # 准备固定数据
       prepare_fixtures()
       
       # 构建pytest参数
       pytest_args = unknown
       if args.priority:
           pytest_args.extend(["-m", args.priority])
       if args.parallel:
           pytest_args.extend(["-n", str(args.parallel)])
       
       # 运行测试
       return run_pytest(pytest_args)
   
   if __name__ == "__main__":
       sys.exit(main())
   ```
   ```
   写入文件：${TESTPLAN_DIR}/run_tests.py
   ```

2. **生成README.md**：
   ```markdown
   # 测试组件：{MODULE_NAME}
   
   本目录包含 {MODULE_NAME} 模块的完整测试组件。
   
   ## 目录结构
   
   {列出目录结构}
   
   ## 快速开始
   
   ### 1. 安装依赖
   
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`
   
   ### 2. 检查环境
   
   \`\`\`bash
   python run_tests.py --check-only
   \`\`\`
   
   ### 3. 运行测试
   
   \`\`\`bash
   # 运行P0场景
   python run_tests.py --priority p0
   
   # 运行所有场景
   pytest test_cases/
   
   # 并行运行
   python run_tests.py --parallel 4
   \`\`\`
   
   ## 查看报告
   
   - HTML报告：`results/report.html`
   - JSON报告：`results/report.json`
   - 日志：`logs/`
   
   ## 复现测试
   
   测试运行时会打印随机种子，使用相同的种子可以复现测试：
   
   \`\`\`bash
   TEST_RANDOM_SEED=123456 pytest test_cases/
   \`\`\`
   ```
   ```
   写入文件：${TESTPLAN_DIR}/README.md
   ```

3. **更新进度**：测试组件实现完成

**输出**：
- run_tests.py
- README.md

---

## 阶段2：执行与调试

### 步骤2.1：执行测试

**动作**：
1. **安装依赖**：
   ```bash
   cd ${TESTPLAN_DIR}
   pip install -r requirements.txt
   ```

2. **检查环境**：
   ```bash
   python run_tests.py --check-only
   ```
   
   → 如果环境检查失败：
   - 记录哪些服务未启动
   - 提示用户启动服务
   - 进入"基础设施问题"调试模式

3. **运行P0场景**（核心场景）：
   ```bash
   python run_tests.py --priority p0
   ```
   
   → 如果P0场景失败：
   - 立即进入Debugging模式
   - P0场景必须100%通过才能继续

4. **运行P1场景**（如果P0全部通过）：
   ```bash
   python run_tests.py --priority p1
   ```
   
   → 如果P1场景失败：
   - 记录失败场景
   - 继续执行其他无依赖的场景
   - 测试结束后进入Debugging模式

5. **生成测试报告**：
   - 检查 `results/report.html` 和 `results/report.json`
   - 统计通过率、失败场景、性能指标

6. **更新进度**：测试执行完成

**输出**：
- 测试报告
- 日志文件
- 失败场景清单（如果有）

---

### 步骤2.2：智能Debugging（关键！）

**触发条件**：
- 任何P0场景失败
- P1场景失败率 > 5%
- 任何场景抛出意外异常

**Debugging核心原则**（重申）：
- **不是死磕单个bug**：不是反复尝试修改某行代码
- **从源头考虑问题**：从项目背景、架构、配置、基础设施整体分析
- **系统性诊断**：按5个维度逐一检查
- **根本性解决方案**：解决根本原因，不是临时修补

**动作**：

### 2.2.1 收集失败信息

1. **读取测试报告**：
   - 失败的场景列表
   - 错误消息和堆栈跟踪
   - 失败时的日志

2. **读取场景日志**：
   ```
   读取文件：logs/by_scenario/{失败场景ID}.log
   提取关键信息：
   - API调用参数
   - API响应
   - 数据库状态
   - 错误堆栈
   ```

3. **识别错误类型**：
   
   | 错误类型 | 识别特征 | 可能原因 |
   |---------|---------|---------|
   | 连接错误 | ConnectionError, Connection refused | 服务未启动 |
   | 超时错误 | Timeout, TimeoutError | 服务响应慢或卡死 |
   | 404错误 | 404 Not Found | API端点不存在 |
   | 500错误 | 500 Server Error | 服务内部错误 |
   | 数据库错误 | pymongo.errors, redis.exceptions | 数据库问题 |
   | 断言失败 | AssertionError | 结果不符合预期 |
   | 其他 | - | 需深入分析 |

### 2.2.2 系统性诊断（5个维度）

**维度1：理解项目背景（关键！）**

```
目的：理解为什么要开发这个功能，功能的核心价值是什么

1. 重新读取需求文档（DemandDescription.md）：
   - 第1节：业务背景
     * 为什么要开发这个功能？
     * 解决什么问题？
   - 第2节：核心功能需求
     * 应该实现哪些功能？
     * 这个失败的场景测试的是哪个功能？
   - 第4节：技术要求
     * 有哪些技术约束？

2. 分析失败场景与开发意图的关系：
   - 这个场景测试的功能是核心功能还是辅助功能？
   - 开发文档中对这个功能有什么说明？
   - 失败是因为功能未实现，还是实现方式有问题？

3. 思考：
   - 如果这是用户的真实使用场景，用户会遇到什么问题？
   - 这个问题会严重影响用户使用吗？
```

**维度2：检查基础设施**

```
目的：排查最常见的问题——服务未启动或配置错误

1. 检查所有依赖服务状态：
   $ ps aux | grep redis
   $ ps aux | grep mongod
   $ ps aux | grep celery
   $ ps aux | grep uvicorn
   
   → 如果Celery worker未启动：
     * 根本原因：Celery worker未启动
     * 不是代码bug，是部署问题
     * 解决方案：
       - 立即启动worker：celery -A main.celery_app worker --loglevel=info
       - 更新启动脚本，确保同时启动FastAPI和Celery
       - 更新部署文档，明确说明需要启动两个服务

2. 检查服务配置：
   - 读取项目的config.py或.env文件
   - 检查数据库连接字符串是否正确
   - 检查端口是否冲突
   
   → 如果MongoDB连接字符串错误：
     * 根本原因：配置文件中的URL不正确
     * 解决方案：修正配置，不是修改代码

3. 检查网络连通性：
   $ curl http://localhost:8000/health
   $ redis-cli ping
   $ mongo --eval "db.serverStatus()"
```

**维度3：检查配置和环境**

```
目的：排查配置差异导致的问题

1. 对比测试配置与生产配置：
   - 测试配置：test_config.py
   - 生产配置：Kobe/{MODULE}/config.py
   
   → 如果数据库名称不一致：
     * 测试连接到test_db，但代码默认连接到prod_db
     * 解决方案：统一配置管理

2. 检查环境变量：
   $ env | grep MONGO
   $ env | grep REDIS
   
   → 如果环境变量覆盖了配置文件：
     * 根本原因：环境变量优先级高于配置文件
     * 解决方案：清除环境变量或调整配置加载顺序

3. 检查依赖版本：
   $ pip list | grep pymongo
   $ pip list | grep redis
   
   → 如果依赖版本不兼容：
     * 根本原因：依赖版本冲突
     * 解决方案：在requirements.txt中固定版本
```

**维度4：检查代码实现**

```
目的：如果前3个维度都没问题，才检查代码

1. 读取实际代码实现：
   - 定位失败场景涉及的模块
   - 读取核心代码文件
   
2. 对比代码与技术决策文档：
   - Tech_Decisions.md中定义了API端点吗？
   - 实际代码实现了这个端点吗？
   - API的路由路径一致吗？
   
   → 如果API端点不存在：
     * 根本原因：功能未实现或路由路径错误
     * 解决方案：
       - 如果未实现：这是功能缺失，不是bug
       - 如果路径错误：修正路由路径

3. 检查代码逻辑：
   - 数据处理逻辑是否正确？
   - 错误处理是否完善？
   - 异步任务是否正确注册？
```

**维度5：检查测试本身**

```
目的：排除测试代码本身的问题

1. 检查测试代码：
   - 测试数据生成是否正确？
   - API调用参数是否正确？
   - 验收标准是否合理？
   
   → 如果验收标准过于严格：
     * 例如：响应时间 < 10秒，但实际需要15秒
     * 根本原因：验收标准不现实
     * 解决方案：调整验收标准，更新测试场景文档

2. 检查测试环境隔离：
   - 测试是否互相影响？
   - 数据是否清理干净？
   
   → 如果测试数据未清理：
     * 根本原因：cleanup fixture未生效
     * 解决方案：修复cleanup逻辑

3. 检查随机化：
   - 随机种子是否设置？
   - 随机数据是否导致不可预测的失败？
   
   → 如果随机数据导致失败：
     * 使用相同种子复现问题
     * 分析特定随机数据为何导致失败
```

### 2.2.3 生成诊断报告

```markdown
# Debugging报告：{失败场景ID}

## 1. 失败摘要

- 场景：{场景名称}
- 错误类型：{ConnectionError / Timeout / AssertionError / ...}
- 错误消息：{错误消息}

## 2. 系统性诊断结果

### 维度1：项目背景理解

- 该场景测试的功能：{功能名称}
- 在需求文档中的描述：{引用需求文档}
- 开发意图：{理解的开发目的}

### 维度2：基础设施检查

- Redis状态：{Running / Not Running}
- MongoDB状态：{Running / Not Running}
- Celery Worker状态：{Running / Not Running}
- FastAPI状态：{Running / Not Running}

**发现的问题**：
- {问题描述}

### 维度3：配置和环境检查

- 测试配置：{test_config.py内容}
- 生产配置：{config.py内容}
- 环境变量：{相关环境变量}

**发现的问题**：
- {问题描述}

### 维度4：代码实现检查

- 涉及的模块：{模块路径}
- 核心代码片段：{代码引用}

**发现的问题**：
- {问题描述}

### 维度5：测试本身检查

- 测试代码：{测试函数}
- 验收标准：{标准描述}

**发现的问题**：
- {问题描述}

## 3. 根本原因

{识别的根本原因，不是表面现象}

## 4. 解决方案

### 根本性解决方案

{解决根本原因的方案，不是临时修补}

### 实施步骤

1. {步骤1}
2. {步骤2}
...

### 预防措施

{如何避免类似问题再次发生}

## 5. 为何会发生

{反思：为什么会发生这个问题？是文档不清晰？是流程缺失？是沟通不足？}
```

### 2.2.4 实施解决方案

1. **根据诊断结果实施解决方案**：
   - 如果是基础设施问题：启动服务，更新文档
   - 如果是配置问题：修正配置
   - 如果是代码问题：修复代码
   - 如果是测试问题：调整测试

2. **重新运行失败的场景**：
   ```bash
   pytest test_cases/ -k "{失败场景ID}"
   ```

3. **验证修复**：
   - 场景是否通过？
   - 修复是否引入新问题？
   - 其他场景是否受影响？

4. **更新文档**（如果需要）：
   - 如果发现需求文档或技术决策不清晰，更新相应文档
   - 如果发现测试场景的验收标准不合理，更新测试场景文档

5. **更新进度**：Debugging完成，修复已验证

---

### 步骤2.3：生成最终测试报告

**动作**：
1. **收集所有测试结果**：
   - 读取 `results/report.json`
   - 读取 `logs/test_run_*.log`
   - 收集性能指标

2. **生成执行总结**：

   ```markdown
   # 测试执行报告：{MODULE_NAME}
   
   **执行时间**：{YYYY-MM-DD HH:mm:ss}
   **随机种子**：{seed值}
   **执行环境**：{操作系统、Python版本}
   
   ---
   
   ## 1. 测试摘要
   
   | 指标 | 数值 |
   |------|------|
   | 总场景数 | {total} |
   | 通过场景数 | {passed} |
   | 失败场景数 | {failed} |
   | 跳过场景数 | {skipped} |
   | 通过率 | {pass_rate}% |
   | 总执行时间 | {duration} |
   
   ---
   
   ## 2. 按优先级统计
   
   | 优先级 | 总数 | 通过 | 失败 | 通过率 |
   |--------|------|------|------|--------|
   | P0 | {p0_total} | {p0_passed} | {p0_failed} | {p0_rate}% |
   | P1 | {p1_total} | {p1_passed} | {p1_failed} | {p1_rate}% |
   | P2 | {p2_total} | {p2_passed} | {p2_failed} | {p2_rate}% |
   | P3 | {p3_total} | {p3_passed} | {p3_failed} | {p3_rate}% |
   
   ---
   
   ## 3. 按维度统计
   
   {维度统计表}
   
   ---
   
   ## 4. 失败场景详情
   
   {如果有失败场景，列出详情和Debugging报告链接}
   
   ---
   
   ## 5. 性能分析
   
   ### 5.1 响应时间统计
   
   - 平均响应时间：{avg}秒
   - P50响应时间：{p50}秒
   - P95响应时间：{p95}秒
   - P99响应时间：{p99}秒
   
   ### 5.2 资源使用统计
   
   - 平均内存占用：{avg_mem}MB
   - 峰值内存占用：{peak_mem}MB
   - 平均CPU使用率：{avg_cpu}%
   
   ---
   
   ## 6. 结论
   
   {总体评价}
   
   ---
   
   **测试版本**：2.0 | **报告生成时间**：{timestamp}
   ```

3. **写入执行报告**：
   ```
   写入文件：${TESTPLAN_DIR}/results/execution_report.md
   ```

4. **更新进度**：最终报告生成完成

**输出**：
- execution_report.md
- debugging_reports/（如果有失败场景）

---

## 进度跟踪

**阶段1：测试实现**：
- [ ] 步骤1.1：所有文档加载完成
- [ ] 步骤1.2：目录结构创建完成
- [ ] 步骤1.3：配置文件生成完成
- [ ] 步骤1.4：工具模块生成完成
- [ ] 步骤1.5：conftest.py生成完成
- [ ] 步骤1.6：测试用例文件生成完成
- [ ] 步骤1.7：测试组件实现完成

**阶段2：执行与调试**：
- [ ] 步骤2.1：测试执行完成
- [ ] 步骤2.2：Debugging完成（如果需要）
- [ ] 步骤2.3：最终报告生成完成

---

## 验收标准

**测试组件要求**：
- [ ] 目录结构完整（7个主要目录）
- [ ] 配置文件齐全（requirements.txt, pytest.ini, test_config.py）
- [ ] 工具模块完整（7个工具文件）
- [ ] conftest.py包含所有必需fixtures
- [ ] 测试文件覆盖所有7个维度
- [ ] README.md包含使用指南

**测试执行要求**：
- [ ] P0场景通过率100%
- [ ] P1场景通过率≥95%
- [ ] 生成HTML和JSON报告
- [ ] 性能指标记录完整

**Debugging要求**（如果失败）：
- [ ] 按5个维度系统性诊断
- [ ] 生成详细的Debugging报告
- [ ] 识别根本原因
- [ ] 提供根本性解决方案
- [ ] 实施并验证修复

---

## 错误处理

**ERROR 级别**（终止执行）：
- 缺少任何一个测试文档（场景/计划/技术）
- P0场景通过率 < 100%（必须Debugging后重试）

**WARN 级别**（记录警告但继续）：
- P1场景失败率 < 5%（记录但不强制Debugging）
- 性能指标超出预期（记录但不中止测试）

---

## 规范引用

**测试规范**：
- `CodexFeatured/Common/SimulationTestingConstitution.yaml` - 测试专用宪法

**项目规范**：
- `CodexFeatured/Common/BackendConstitution.yaml` - 项目技术栈

**开发文档**（Debugging时使用）：
- `DemandDescription.md` - 需求文档（理解开发意图）
- `DevPlan.md` - 开发计划（理解架构）
- `Tech_Decisions.md` - 技术决策（理解实现细节）

**上游工作流**：
- `TestScenarioAnalysis_V2` - 测试场景分析
- `TestPlanGeneration_V2` - 测试计划生成
- `TestTechDecisions_V2` - 测试技术选型

**工作流版本**：2.0 | **最后更新**：2025-10-11

---

*完整的测试执行与智能调试工作流 - 从源头考虑问题，不是死磕bug*

