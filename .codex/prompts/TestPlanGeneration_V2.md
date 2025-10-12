---
description: 测试计划生成工作流 - 基于测试场景设计测试组织方案
version: 2.0
language: zh-CN
upstream: TestScenarioAnalysis_V2, TestScenarioSpecify_V2
downstream: TestTechDecisions_V2
scripts:
  ps: CodexFeatured/Scripts/get-test-context.ps1 -Json
---

# TestPlanGeneration - 测试计划生成工作流

## 工作流概述

**目标**：基于测试场景文档，设计测试代码的组织方案和执行计划。

**核心问题**：
- 如何组织测试代码？（目录结构）
- 如何准备测试数据？（生成器 vs 固定数据）
- 如何搭建测试环境？（依赖服务、配置）
- 测试执行顺序是什么？（依赖关系、并行 vs 串行）
- 如何收集和报告结果？（日志、报告格式）

**核心原则**：
- 遵循pytest最佳实践
- 保留原有SimulationTest目录规范
- 测试数据与测试代码分离
- 支持环境隔离（避免污染生产数据）
- 完整的日志和报告机制

**输入**：
- 测试场景文档 `Kobe/SimulationTest/{MODULE_NAME}_testscenarios.md`

**输出**：
- 测试计划文档 `Kobe/SimulationTest/{MODULE_NAME}_testplan.md`

---

## 参数定义

```yaml
OUTPUT_DIR: "D:/AI_Projects/Kobe/SimulationTest"
MODULE_NAME: "{{RUNTIME_RESOLVE}}"
SCENARIO_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testscenarios.md"
TESTPLAN_FILE: "${OUTPUT_DIR}/${MODULE_NAME}_testplan.md"
TESTPLAN_DIR: "${OUTPUT_DIR}/${MODULE_NAME}_testplan"
```

---

## 执行流程

### 步骤1：加载测试场景文档

**动作**：
1. **运行上下文脚本**（如果配置）：
   ```
   从仓库根目录运行 `{SCRIPT}` 并解析JSON获取：
   - MODULE_NAME: 模块名称
   - SCENARIO_FILE: 测试场景文档路径
   ```
   → 如果脚本执行失败或未配置：继续手动扫描

2. **自动定位测试场景文档**：
   - 扫描 `${OUTPUT_DIR}` 下所有 *_testscenarios.md 文件
   - 按修改时间倒序，选择最新的
   → 如果未找到：ERROR "未找到测试场景文档。请先运行 TestScenarioAnalysis_V2"

3. **读取测试场景文档**：
   - 读取 `${SCENARIO_FILE}` 完整内容
   - 提取标识信息：MODULE_NAME、COUNT_3D、INTENT_TITLE_2_4
   - 解析场景清单：
     * 场景总数
     * 场景分布（7个维度）
     * 优先级分布（P0/P1/P2/P3）
     * 依赖关系
     * 随机化策略清单

4. **提取关键信息**：
   ```python
   场景统计 = {
       "总场景数": 68,
       "P0场景数": 19,
       "P1场景数": 36,
       "P2场景数": 12,
       "P3场景数": 1,
       "维度分布": {
           "功能覆盖": 15,
           "数据多样性": 10,
           "并发与性能": 8,
           "配置分支": 12,
           "异常恢复": 10,
           "依赖服务": 8,
           "真实场景": 5
       }
   }
   
   依赖关系 = [
       ("Scenario-1.2", "Scenario-1.1"),
       ("Scenario-3.1", "Scenario-1.1"),
       ("Scenario-7.1", ["Scenario-1.1", "Scenario-2.1"]),
       ...
   ]
   
   随机化策略类型 = [
       "数据量随机",
       "顺序随机",
       "延迟随机",
       "失败注入",
       "内容随机",
       ...
   ]
   ```

5. **更新进度**：测试场景文档加载完成

**输出**：
- MODULE_NAME
- 场景统计数据
- 依赖关系图
- 随机化策略清单

---

### 步骤2：设计目录结构

**动作**：
1. **设计完整的测试组件目录**：

   ```
   SimulationTest/{MODULE_NAME}_testplan/
   ├── test_cases/                      # 测试用例目录
   │   ├── __init__.py
   │   ├── conftest.py                  # pytest配置和fixtures
   │   ├── test_01_功能覆盖.py           # 按维度组织测试
   │   ├── test_02_数据多样性.py
   │   ├── test_03_并发性能.py
   │   ├── test_04_配置分支.py
   │   ├── test_05_异常恢复.py
   │   ├── test_06_依赖服务.py
   │   └── test_07_真实场景.py
   ├── test_data/                       # 测试数据目录
   │   ├── __init__.py
   │   ├── generators/                  # 数据生成器
   │   │   ├── __init__.py
   │   │   ├── base_generator.py       # 基础生成器
   │   │   ├── message_generator.py    # 消息生成器
   │   │   ├── html_generator.py       # HTML生成器
   │   │   └── random_utils.py         # 随机化工具
   │   └── fixtures/                    # 固定测试数据
   │       ├── sample_small.html        # 小文件样本
   │       ├── sample_empty.html        # 空文件样本
   │       └── sample_special.html      # 特殊字符样本
   ├── results/                         # 测试结果目录
   │   ├── .gitkeep
   │   └── README.md                    # 结果说明
   ├── logs/                            # 日志目录
   │   ├── .gitkeep
   │   └── README.md                    # 日志说明
   ├── utils/                           # 工具函数目录
   │   ├── __init__.py
   │   ├── api_client.py               # API调用封装
   │   ├── db_client.py                # 数据库客户端
   │   ├── service_checker.py          # 服务状态检查
   │   └── result_validator.py         # 结果验证工具
   ├── requirements.txt                 # Python依赖
   ├── pytest.ini                       # pytest配置
   ├── run_tests.py                     # 测试执行器
   └── README.md                        # 测试计划说明
   ```

2. **按维度映射测试文件**：

   | 维度 | 测试文件 | 场景数量 | 预估时间 |
   |------|---------|---------|---------|
   | 功能覆盖 | test_01_功能覆盖.py | 15 | 1小时 |
   | 数据多样性 | test_02_数据多样性.py | 10 | 40分钟 |
   | 并发与性能 | test_03_并发性能.py | 8 | 2小时 |
   | 配置分支 | test_04_配置分支.py | 12 | 1.5小时 |
   | 异常恢复 | test_05_异常恢复.py | 10 | 1小时 |
   | 依赖服务 | test_06_依赖服务.py | 8 | 1.5小时 |
   | 真实场景 | test_07_真实场景.py | 5 | 1小时 |
   | **总计** | **7个文件** | **68个场景** | **约9小时** |

3. **定义conftest.py结构**（pytest fixtures）：

   ```python
   # conftest.py 应包含：
   
   fixtures = [
       "api_client",         # API客户端fixture
       "db_client",          # 数据库客户端fixture
       "redis_client",       # Redis客户端fixture
       "test_config",        # 测试配置fixture
       "cleanup",            # 测试清理fixture
       "mock_llm_api",       # 模拟大模型API fixture
       "test_data_dir",      # 测试数据目录fixture
       "random_seed",        # 随机种子fixture（可复现）
   ]
   
   hooks = [
       "pytest_configure",   # pytest启动时执行（环境检查）
       "pytest_unconfigure",  # pytest结束时执行（清理）
       "pytest_runtest_setup",  # 每个测试前执行
       "pytest_runtest_teardown",  # 每个测试后执行
   ]
   ```

4. **更新进度**：目录结构设计完成

**输出**：
- 完整的目录结构设计
- 测试文件映射表
- conftest.py结构定义

---

### 步骤3：设计测试数据准备方案

**动作**：
1. **分类测试数据需求**：

   **分类维度**：
   - **小数据**：10-20条消息（快速生成，可缓存）
   - **中数据**：100-500条消息（按需生成）
   - **大数据**：10000+条消息（动态生成，不缓存）
   - **特殊数据**：固定样本（手工准备或生成后缓存）

   **数据类型**：
   - **正常数据**：标准格式的Telegram HTML
   - **边界数据**：空文件、单条消息、超大文件
   - **异常数据**：格式错误、缺少字段、特殊字符
   - **随机数据**：每次运行动态生成

2. **设计数据生成器架构**：

   ```python
   # base_generator.py
   class BaseGenerator:
       def __init__(self, seed=None):
           self.seed = seed or random.randint(1, 1000000)
           random.seed(self.seed)
           self.faker = Faker('zh_CN')
           self.faker.seed_instance(self.seed)
       
       def set_seed(self, seed):
           """设置随机种子（用于复现）"""
           pass
   
   # message_generator.py
   class MessageGenerator(BaseGenerator):
       def generate_message(self, **kwargs):
           """生成单条消息"""
           pass
       
       def generate_messages(self, count=None, **kwargs):
           """生成多条消息（count可为None，表示随机数量）"""
           pass
       
       def generate_special_message(self, type='emoji'):
           """生成特殊类型消息（表情、代码块、HTML标签）"""
           pass
   
   # html_generator.py
   class TelegramHTMLGenerator(BaseGenerator):
       def generate_html(self, messages):
           """将消息列表渲染为Telegram HTML格式"""
           pass
       
       def generate_file(self, count=None, output_path=None):
           """生成HTML文件"""
           pass
   
   # random_utils.py
   def random_count(min_val, max_val):
       """随机数量"""
       return random.randint(min_val, max_val)
   
   def random_shuffle(items):
       """随机打乱"""
       shuffled = items.copy()
       random.shuffle(shuffled)
       return shuffled
   
   def random_delay(min_sec=0, max_sec=5):
       """随机延迟"""
       time.sleep(random.uniform(min_sec, max_sec))
   
   def inject_failure(probability=0.1):
       """失败注入（返回True表示应该模拟失败）"""
       return random.random() < probability
   ```

3. **设计固定数据样本清单**：

   | 样本文件 | 描述 | 生成方式 | 大小 |
   |---------|------|---------|------|
   | sample_small.html | 正常小文件（18条消息） | 一次生成，缓存 | ~10KB |
   | sample_empty.html | 空文件（0条消息） | 手工创建 | ~1KB |
   | sample_special.html | 特殊字符样本 | 一次生成，缓存 | ~5KB |
   | sample_malformed.html | 格式错误样本 | 手工创建 | ~5KB |

4. **定义数据准备流程**：

   ```
   run_tests.py 启动
       ↓
   检查 test_data/fixtures/ 是否存在固定样本
       ↓ 如果不存在
   运行 test_data/generators/prepare_fixtures.py
       ↓ 生成所有固定样本并缓存
       ↓
   测试用例运行
       ↓ 小数据场景
   直接使用 fixtures/ 中的样本
       ↓ 大数据场景
   调用 generators/ 动态生成
       ↓
   测试结束，清理动态生成的数据
   ```

5. **更新进度**：测试数据准备方案设计完成

**输出**：
- 数据分类清单
- 数据生成器架构设计
- 固定样本清单
- 数据准备流程图

---

### 步骤4：设计测试环境搭建方案

**动作**：
1. **识别依赖服务**（从测试场景文档提取）：

   | 服务 | 默认地址 | 检查方式 | 启动方式 |
   |------|---------|---------|---------|
   | Redis | localhost:6379 | redis-cli ping | docker run redis |
   | MongoDB | localhost:27017 | pymongo.MongoClient | docker run mongo |
   | RabbitMQ | localhost:5672 | pika连接测试 | docker run rabbitmq |
   | Chromadb | localhost:8001 | HTTP GET /api/v1/heartbeat | docker run chromadb |
   | Celery Worker | N/A | ps aux \| grep celery | celery -A main worker |
   | FastAPI | localhost:8000 | HTTP GET /health | uvicorn main:app |

2. **设计环境检查脚本**（`utils/service_checker.py`）：

   ```python
   class ServiceChecker:
       def check_redis(self) -> bool:
           """检查Redis是否运行"""
           pass
       
       def check_mongodb(self) -> bool:
           """检查MongoDB是否运行"""
           pass
       
       def check_rabbitmq(self) -> bool:
           """检查RabbitMQ是否运行"""
           pass
       
       def check_chromadb(self) -> bool:
           """检查Chromadb是否运行"""
           pass
       
       def check_celery_worker(self) -> bool:
           """检查Celery Worker是否运行"""
           pass
       
       def check_fastapi(self) -> bool:
           """检查FastAPI是否运行"""
           pass
       
       def check_all(self) -> dict:
           """检查所有服务，返回状态字典"""
           pass
       
       def wait_for_service(self, service_name, timeout=30):
           """等待服务启动"""
           pass
   ```

3. **设计环境隔离方案**：

   **数据库隔离**：
   ```python
   # 使用独立的测试数据库
   TEST_MONGODB_DB = "test_telegram_curation"
   TEST_REDIS_DB = 1  # 使用Redis DB 1（生产使用DB 0）
   
   # pytest fixture
   @pytest.fixture(scope="session")
   def db_client():
       client = MongoClient("localhost", 27017)
       db = client[TEST_MONGODB_DB]
       yield db
       # 测试结束后清理
       client.drop_database(TEST_MONGODB_DB)
   ```

   **文件隔离**：
   ```python
   # 使用独立的测试工作目录
   TEST_WORKSPACE = "D:/AI_Projects/Kobe/SimulationTest/{MODULE_NAME}_testplan/workspace"
   
   # pytest fixture
   @pytest.fixture
   def test_workspace(tmp_path):
       workspace = tmp_path / "workspace"
       workspace.mkdir()
       yield workspace
       # 测试结束后清理
       shutil.rmtree(workspace)
   ```

4. **设计配置管理方案**：

   **测试专用配置**（`test_config.py`）：
   ```python
   from pydantic_settings import BaseSettings
   
   class TestConfig(BaseSettings):
       # 服务地址
       REDIS_URL: str = "redis://localhost:6379/1"
       MONGODB_URL: str = "mongodb://localhost:27017/test_telegram_curation"
       RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
       CHROMADB_URL: str = "http://localhost:8001"
       FASTAPI_URL: str = "http://localhost:8000"
       
       # 测试配置
       RANDOM_SEED: int = 42
       TIMEOUT: int = 300
       MAX_WORKERS: int = 100
       RETRY_TIMES: int = 3
       
       # 大模型配置（测试时使用mock）
       MOCK_LLM: bool = True
       LLM_RESPONSE_DELAY: float = 0.1  # 模拟延迟
       
       class Config:
           env_prefix = "TEST_"
   ```

5. **设计启动与清理流程**：

   ```
   测试前（conftest.py pytest_configure）：
   1. 检查所有依赖服务状态
   2. 如果服务未启动，提示用户启动或自动启动（Docker）
   3. 等待所有服务就绪
   4. 创建测试数据库/目录
   5. 设置随机种子
   6. 初始化日志
   
   测试后（conftest.py pytest_unconfigure）：
   1. 清理测试数据库
   2. 清理临时文件
   3. 关闭所有连接
   4. 生成最终报告
   ```

6. **更新进度**：测试环境搭建方案设计完成

**输出**：
- 依赖服务清单
- 环境检查脚本设计
- 环境隔离方案
- 配置管理方案
- 启动与清理流程

---

### 步骤5：设计测试执行顺序

**动作**：
1. **构建依赖关系图**：

   ```
   从测试场景文档提取所有依赖关系：
   
   Scenario-1.1（正常导入小文件）
       ↓
   ├── Scenario-1.2（大文件导入）
   ├── Scenario-3.1（10并发）
   │       ↓
   │   Scenario-3.2（100并发）
   └── Scenario-7.1（用户典型流程）
           ↑
           └── Scenario-2.1（特殊字符）
   
   依赖关系列表：
   - Scenario-1.2 → Scenario-1.1
   - Scenario-3.1 → Scenario-1.1
   - Scenario-3.2 → Scenario-3.1
   - Scenario-7.1 → [Scenario-1.1, Scenario-2.1]
   ```

2. **拓扑排序确定执行顺序**：

   ```python
   执行阶段划分：
   
   阶段1：基础场景（无依赖）
   - Scenario-1.1（正常导入小文件）
   - Scenario-1.3（空文件导入）
   - Scenario-2.1（特殊字符）
   - ...
   
   阶段2：依赖阶段1的场景
   - Scenario-1.2（大文件导入）← 依赖1.1
   - Scenario-3.1（10并发）← 依赖1.1
   - ...
   
   阶段3：依赖阶段2的场景
   - Scenario-3.2（100并发）← 依赖3.1
   - Scenario-7.1（用户典型流程）← 依赖1.1, 2.1
   - ...
   ```

3. **按优先级分组**：

   ```
   第一轮：P0场景（19个）
   - 串行执行（确保基础功能）
   - 如果失败，立即停止
   - 预计时间：2小时
   
   第二轮：P1场景（36个）
   - 可并行执行（无依赖的场景）
   - 如果失败，记录但继续
   - 预计时间：4小时
   
   第三轮：P2场景（12个，可选）
   - 可并行执行
   - 失败不影响整体结果
   - 预计时间：2小时
   
   第四轮：P3场景（1个，可选）
   - 边缘情况
   - 预计时间：30分钟
   ```

4. **设计pytest执行策略**：

   **pytest markers**：
   ```python
   # 在测试函数上添加标记
   @pytest.mark.p0  # 核心场景
   @pytest.mark.p1  # 重要场景
   @pytest.mark.p2  # 辅助场景
   @pytest.mark.p3  # 边缘场景
   
   @pytest.mark.depends(on=['test_scenario_1_1'])  # 依赖关系
   @pytest.mark.timeout(300)  # 超时时间
   @pytest.mark.asyncio  # 异步测试
   ```

   **执行命令**：
   ```bash
   # 只执行P0场景
   pytest -m p0 --tb=short
   
   # 执行P0和P1场景
   pytest -m "p0 or p1" --tb=short
   
   # 并行执行（无依赖的场景）
   pytest -n 4 -m "p1 and not depends"
   
   # 按文件执行
   pytest test_cases/test_01_功能覆盖.py
   ```

5. **设计失败处理策略**：

   | 场景优先级 | 失败时的行为 | 影响范围 |
   |-----------|------------|---------|
   | P0 | 立即停止所有测试 | 全局 |
   | P1 | 记录失败但继续执行无依赖的场景 | 依赖链 |
   | P2 | 记录失败，不影响其他场景 | 局部 |
   | P3 | 记录失败，不影响其他场景 | 局部 |

6. **更新进度**：测试执行顺序设计完成

**输出**：
- 依赖关系图
- 拓扑排序结果
- 执行阶段划分
- pytest执行策略
- 失败处理策略

---

### 步骤6：设计结果收集与报告方案

**动作**：
1. **设计日志结构**：

   **日志文件**：
   ```
   logs/
   ├── test_run_{timestamp}.log       # 总日志
   ├── debug.log                      # 调试日志
   ├── error.log                      # 错误日志
   ├── performance.log                # 性能日志
   └── by_scenario/                   # 按场景分类
       ├── scenario_1_1.log
       ├── scenario_1_2.log
       └── ...
   ```

   **日志内容**：
   ```
   [2025-10-11 10:00:00] [INFO] [Scenario-1.1] 开始执行：正常导入小文件
   [2025-10-11 10:00:01] [DEBUG] [Scenario-1.1] 生成测试数据：18条消息
   [2025-10-11 10:00:02] [DEBUG] [Scenario-1.1] 调用API: POST /api/telegram-curation/ingest/start
   [2025-10-11 10:00:03] [DEBUG] [Scenario-1.1] 任务ID: abc123
   [2025-10-11 10:00:05] [DEBUG] [Scenario-1.1] 任务状态: processing (20%)
   [2025-10-11 10:00:15] [DEBUG] [Scenario-1.1] 任务状态: completed (100%)
   [2025-10-11 10:00:16] [INFO] [Scenario-1.1] 验证结果：MongoDB包含18条记录 ✓
   [2025-10-11 10:00:16] [INFO] [Scenario-1.1] 响应时间：14秒 ✓
   [2025-10-11 10:00:16] [SUCCESS] [Scenario-1.1] 场景通过
   ```

2. **设计报告格式**：

   **JSON报告**（`results/report.json`）：
   ```json
   {
     "summary": {
       "total": 68,
       "passed": 65,
       "failed": 2,
       "skipped": 1,
       "duration": "8.5h",
       "pass_rate": "95.6%"
     },
     "by_priority": {
       "P0": {"total": 19, "passed": 19, "failed": 0},
       "P1": {"total": 36, "passed": 34, "failed": 2},
       "P2": {"total": 12, "passed": 11, "failed": 0, "skipped": 1}
     },
     "by_dimension": {
       "功能覆盖": {"total": 15, "passed": 15, "failed": 0},
       "数据多样性": {"total": 10, "passed": 10, "failed": 0},
       "并发性能": {"total": 8, "passed": 6, "failed": 2},
       ...
     },
     "failed_scenarios": [
       {
         "id": "Scenario-3.2",
         "name": "100并发用户",
         "error": "数据库连接池耗尽",
         "log": "logs/by_scenario/scenario_3_2.log"
       }
     ]
   }
   ```

   **HTML报告**（`results/report.html`）：
   - 使用pytest-html生成
   - 包含场景统计、通过率、失败详情
   - 可视化图表（通过率、执行时间）

3. **设计性能指标收集**：

   ```python
   # 每个测试场景收集的指标
   metrics = {
       "scenario_id": "Scenario-1.1",
       "start_time": "2025-10-11 10:00:00",
       "end_time": "2025-10-11 10:00:16",
       "duration": 16.0,  # 秒
       "api_response_time": 14.0,  # 秒
       "memory_usage": {
           "peak": "120MB",
           "average": "80MB"
       },
       "cpu_usage": {
           "peak": "45%",
           "average": "25%"
       },
       "database": {
           "queries": 5,
           "inserts": 18,
           "query_time": 0.5  # 秒
       }
   }
   ```

4. **设计结果验证器**（`utils/result_validator.py`）：

   ```python
   class ResultValidator:
       def validate_api_response(self, response, expected):
           """验证API响应"""
           pass
       
       def validate_database_state(self, db, expected_records):
           """验证数据库状态"""
           pass
       
       def validate_file_output(self, file_path, expected_format):
           """验证文件输出"""
           pass
       
       def validate_performance(self, metrics, thresholds):
           """验证性能指标"""
           pass
   ```

5. **更新进度**：结果收集与报告方案设计完成

**输出**：
- 日志结构设计
- 报告格式设计
- 性能指标收集方案
- 结果验证器设计

---

### 步骤7：生成测试计划文档

**动作**：
1. **生成完整的测试计划文档**：

   ```markdown
   # 测试计划：{MODULE_NAME}

   标识信息：MODULE_NAME={MODULE_NAME}；COUNT_3D={COUNT_3D}；INTENT_TITLE_2_4={INTENT_TITLE_2_4}；生成时间={YYYY-MM-DD HH:mm:ss}

   **参考文档**：
   - 测试场景文档：{SCENARIO_FILE}

   **输出路径**：{TESTPLAN_FILE}

   ---

   ## 1. 测试组织结构

   ### 1.1 目录结构

   {完整目录树，从步骤2}

   ### 1.2 测试文件映射

   {测试文件映射表，从步骤2}

   ### 1.3 关键组件说明

   #### conftest.py
   - 作用：pytest配置和公共fixtures
   - 包含fixtures：{列表，从步骤2}
   - 包含hooks：{列表，从步骤2}

   #### run_tests.py
   - 作用：测试执行器，自动化整个测试流程
   - 功能：环境检查、数据准备、执行测试、生成报告

   ---

   ## 2. 测试数据准备

   ### 2.1 数据分类

   {数据分类表，从步骤3}

   ### 2.2 数据生成器

   {数据生成器架构，从步骤3}

   ### 2.3 固定样本清单

   {固定样本表，从步骤3}

   ### 2.4 数据准备流程

   {流程图，从步骤3}

   ---

   ## 3. 测试环境搭建

   ### 3.1 依赖服务

   {依赖服务表，从步骤4}

   ### 3.2 环境检查

   - 检查脚本：utils/service_checker.py
   - 检查内容：{服务清单}
   - 失败处理：{策略}

   ### 3.3 环境隔离

   {环境隔离方案，从步骤4}

   ### 3.4 配置管理

   {配置管理方案，从步骤4}

   ### 3.5 启动与清理

   {启动与清理流程，从步骤4}

   ---

   ## 4. 测试执行计划

   ### 4.1 依赖关系图

   {依赖关系图，从步骤5}

   ### 4.2 执行阶段

   {执行阶段划分，从步骤5}

   ### 4.3 执行策略

   {pytest执行策略，从步骤5}

   ### 4.4 失败处理

   {失败处理策略表，从步骤5}

   ---

   ## 5. 结果收集与报告

   ### 5.1 日志结构

   {日志结构，从步骤6}

   ### 5.2 报告格式

   {报告格式，从步骤6}

   ### 5.3 性能指标

   {性能指标清单，从步骤6}

   ### 5.4 结果验证

   {结果验证器说明，从步骤6}

   ---

   ## 6. 使用指南

   ### 6.1 初次运行

   ```bash
   # 1. 进入测试目录
   cd Kobe/SimulationTest/{MODULE_NAME}_testplan

   # 2. 安装依赖
   pip install -r requirements.txt

   # 3. 检查环境
   python run_tests.py --check-only

   # 4. 运行P0场景（核心场景）
   python run_tests.py --priority p0

   # 5. 查看报告
   open results/report.html
   ```

   ### 6.2 常用命令

   ```bash
   # 运行所有P0和P1场景
   python run_tests.py --priority p0,p1

   # 运行特定维度
   pytest test_cases/test_01_功能覆盖.py

   # 并行运行（4个worker）
   pytest -n 4 test_cases/

   # 生成详细报告
   pytest --html=results/report.html --self-contained-html

   # 只运行失败的场景
   pytest --lf
   ```

   ### 6.3 调试指南

   {如何使用日志定位问题}
   {如何复现失败场景（使用随机种子）}
   {如何单独运行某个场景}

   ---

   ## 7. 预期产出

   ### 7.1 测试报告

   - JSON报告：results/report.json
   - HTML报告：results/report.html
   - 性能报告：results/performance.json

   ### 7.2 日志文件

   - 总日志：logs/test_run_{timestamp}.log
   - 调试日志：logs/debug.log
   - 错误日志：logs/error.log
   - 场景日志：logs/by_scenario/*.log

   ### 7.3 测试数据

   - 固定样本：test_data/fixtures/*.html
   - 生成样本（临时）：test_data/generated/*.html

   ---

   **工作流版本**：2.0 | **生成时间**：{YYYY-MM-DD HH:mm:ss}
   ```

2. **写入文件**：
   ```
   写入文件：${TESTPLAN_FILE}
   编码：UTF-8（无BOM）
   ```

3. **更新进度**：测试计划文档生成完成

**输出文件**：`${TESTPLAN_FILE}`

---

## 进度跟踪

**阶段状态**：
- [ ] 步骤1：测试场景文档加载完成
- [ ] 步骤2：目录结构设计完成
- [ ] 步骤3：测试数据准备方案设计完成
- [ ] 步骤4：测试环境搭建方案设计完成
- [ ] 步骤5：测试执行顺序设计完成
- [ ] 步骤6：结果收集与报告方案设计完成
- [ ] 步骤7：测试计划文档生成完成

---

## 验收标准

**输出文件要求**：
- [ ] 输出路径符合 `${TESTPLAN_FILE}`
- [ ] 文件编码为 UTF-8（无BOM）
- [ ] 文件大小 > 15KB（确保详细）

**测试计划要求**：
- [ ] 包含完整的目录结构设计（7个章节）
- [ ] 包含数据准备方案（生成器 + 固定样本）
- [ ] 包含环境搭建方案（依赖服务 + 检查脚本）
- [ ] 包含执行计划（依赖关系 + 拓扑排序）
- [ ] 包含结果收集方案（日志 + 报告）
- [ ] 包含使用指南（命令示例）

**可执行性要求**：
- [ ] pytest执行策略明确（markers、命令）
- [ ] 依赖关系清晰（拓扑排序正确）
- [ ] 失败处理策略明确

---

## 错误处理

**ERROR 级别**（终止执行）：
- 未找到测试场景文档

**WARN 级别**（记录警告但继续）：
- 测试场景文档缺少某些章节（使用默认值）

---

## 规范引用

**测试规范**：
- `CodexFeatured/Common/SimulationTestingConstitution.yaml` - 测试专用宪法

**上游工作流**：
- `TestScenarioAnalysis_V2` - 测试场景分析
- `TestScenarioSpecify_V2` - 测试场景精化（可选）

**下游工作流**：
- `TestTechDecisions_V2` - 测试技术选型

**工作流版本**：2.0 | **最后更新**：2025-10-11

---

*基于测试场景的完整测试组织方案设计*

