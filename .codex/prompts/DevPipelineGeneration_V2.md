---
description: 工程化"任务清单生成"工作流 - 基于需求、开发计划、技术决策生成可执行任务清单
version: 2.1
language: zh-CN
upstream: TechDecisionsGeneration_V2
downstream: DevPiplineExcute_V2
scripts:
  ps: CodexFeatured/Scripts/get-task-context.ps1 -Json
---

# DevPipelineGeneration - 任务清单生成工作流

## 工作流概述

**目标**：读取需求文档、开发计划、技术决策三个文档，拆解为最小可执行的开发步骤（Tasks.md）。

**核心原则**：
- 综合参考所有前置文档（需求+计划+技术决策）
- 每个 sub_step 必须是人类开发者可手动执行的原子操作
- 任务步骤必须包含所有技术细节（依赖、提示词、配置、字段规范）
- 任务步骤必须可测试、可验证

**输入文档**：
- 需求文档 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/DemandDescription.md` - 业务需求
- 开发计划 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/DevPlan.md` - 架构设计
- 技术决策 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/Tech_Decisions.md` - 技术细节

**输出**：任务清单 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/Tasks.md`

---

## 参数定义

```yaml
OUTPUT_DIR_PATH: "D:/AI_Projects/CodexFeatured/DevPlans"
COUNT_3D: "{{RUNTIME_RESOLVE}}"          # 从文档解析
INTENT_TITLE_2_4: "{{RUNTIME_RESOLVE}}"  # 从文档解析
DEMAND_FILENAME: "DemandDescription.md"
PLAN_FILENAME: "DevPlan.md"
TECH_FILENAME: "Tech_Decisions.md"
TASKS_FILENAME: "Tasks.md"
TARGET_DIR: "${OUTPUT_DIR_PATH}/${COUNT_3D}_${INTENT_TITLE_2_4}"
DEMAND_PATH: "${TARGET_DIR}/${DEMAND_FILENAME}"
PLAN_PATH: "${TARGET_DIR}/${PLAN_FILENAME}"
TECH_PATH: "${TARGET_DIR}/${TECH_FILENAME}"
TASKS_PATH: "${TARGET_DIR}/${TASKS_FILENAME}"
```

---

## 执行流程（DevPipelineGeneration 工作流范围）

**用户输入处理**：

用户可通过命令参数传入文档路径或其他配置。在继续执行前，你**必须**考虑用户输入（若不为空）。

用户输入：

$ARGUMENTS

---

### 步骤1：加载所有前置文档（关键改进）

**动作**：
1. **运行上下文获取脚本**（如果配置）：
   ```
   从仓库根目录运行 `{SCRIPT}` 并解析JSON获取：
   - TARGET_DIR: 目标目录
   - DEMAND_PATH: 需求文档路径
   - PLAN_PATH: 开发计划路径
   - TECH_PATH: 技术决策路径
   - EXISTING_TASKS: 是否已存在 Tasks.md
   ```
   → 如果脚本执行失败或未配置：继续手动扫描

2. **自动定位目标目录**：
   - 扫描 `${OUTPUT_DIR_PATH}` 下所有子目录
   - 查找同时包含 DemandDescription.md、DevPlan.md、Tech_Decisions.md 的目录
   - 按目录编号倒序排列（最大编号优先）
   - 选择最近修改的目录作为目标
   → 如果找到多个候选：
     * 检查文件修改时间，选择最新的
     * WARN "找到多个候选目录，选择最新的: {选择的路径}"
   → 如果未找到完整目录：
     * ERROR "未找到包含所有前置文档的目录。请确保已完成：需求文档、开发计划、技术决策"

3. **验证所有前置文档存在**：
   - 验证 `${DEMAND_PATH}` 存在
     → 如果不存在：ERROR "需求文档不存在，请先运行 DevFuncDemandsWrite"
   - 验证 `${PLAN_PATH}` 存在
     → 如果不存在：ERROR "开发计划不存在，请先运行 DevPlanGeneration"
   - 验证 `${TECH_PATH}` 存在
     → 如果不存在：ERROR "技术决策不存在，请先运行 TechDecisionsGeneration"

4. **读取并解析需求文档**：
   - 读取 `${DEMAND_PATH}` 完整内容
   - 从文档头部提取标识信息：COUNT_3D、INTENT_TITLE_2_4
   - 提取关键需求信息：
     * **功能需求清单**：所有功能点列表
     * **数据需求摘要**：数据来源、类型、量级
     * **性能指标清单**：响应时间、吞吐量、并发
     * **交付物清单**：需要生成的文件/产出

5. **读取并解析开发计划**：
   - 读取 `${PLAN_PATH}` 完整内容
   - 提取架构信息：
     * **功能域与模块清单**：模块名称、职责、依赖关系
     * **目录结构树**：完整的目录结构规划
     * **文件清单**：需要创建的文件及其职责
     * **数据模型清单**：模型名称、字段列表（概要）
     * **接口清单**：API端点/函数接口（概要）
     * **复用模块清单**：需要复用的现有模块

6. **读取并解析技术决策**（重点！最详细的技术信息）：
   - 读取 `${TECH_PATH}` 完整内容
   - 提取技术实现细节：
     * **依赖清单**：
       - 新增依赖：库名、版本、选型理由、官方文档、配置示例
       - 项目现有依赖：复用的依赖
     * **大模型提示词**（如果有）：
       - 完整的提示词模板
       - 输入变量、输出格式
       - 调用参数、错误处理
       - 批处理策略
     * **API对接方案**（如果有）：
       - 端口分配
       - 路由定义（路径、请求/响应格式、测试命令）
       - 中间件配置
     * **数据字段规范**：
       - 每个模型的完整字段定义（类型、验证、示例）
       - Pydantic 模型定义
       - 字段命名规范
     * **配置文件内容**：
       - .env 文件模板（完整）
       - config.py 文件内容（完整）
     * **实现路径映射**：
       - 技术决策到具体文件的映射

7. **验证任务清单文件状态**：
   → 如果 `${TASKS_PATH}` 已存在：
     * WARN "任务清单已存在: {TASKS_PATH}，将覆盖现有文件"

8. **更新进度**：所有前置文档加载完成

**输出**：
- TARGET_DIR、所有文档路径
- COUNT_3D、INTENT_TITLE_2_4
- 需求文档关键信息（功能、数据、性能、交付物）
- 开发计划关键信息（模块、目录、文件、接口）
- 技术决策关键信息（依赖、提示词、API、字段、配置）

---

### 步骤2：构建任务上下文

**动作**：
1. **整合三份文档的信息**：
   - **业务层**（需求文档）：
     * 要实现的功能列表
     * 要满足的性能指标
     * 要生成的交付物
   - **架构层**（开发计划）：
     * 要创建的目录结构
     * 要创建的文件列表
     * 要实现的模块与接口
   - **技术层**（技术决策）：
     * 要安装的依赖清单
     * 要编写的提示词
     * 要配置的API路由
     * 要定义的数据字段
     * 要创建的配置文件

2. **建立需求到实现的映射**：
   - 对于每个功能需求：
     * 映射到具体模块（从开发计划）
     * 映射到具体文件（从开发计划）
     * 映射到具体技术（从技术决策）
   - 示例映射：
     ```
     功能需求："判断字段是否属于用户画像"
       ↓ 映射到模块（开发计划）
     模块："FieldClassifier"
       ↓ 映射到文件（开发计划）
     文件："Kobe/VisaDBOperation/classifier.py"
       ↓ 映射到技术（技术决策）
     技术：使用大模型 gpt-4o-mini，提示词模板见 Tech_Decisions.md 第2.1节
     ```

3. **识别任务依赖关系**：
   - 基础设施任务（目录、依赖、配置）必须最先执行
   - 数据模型定义必须在业务逻辑之前
   - API路由必须在业务逻辑之后
   - 测试必须在实现之后

4. **更新进度**：任务上下文构建完成

**输出**：
- 需求到实现的映射表
- 任务依赖关系图
- 任务优先级排序

---

### 步骤3：按阶段拆解任务

**动作**：
1. **阶段0：环境准备与依赖安装**
   
   **从技术决策文档提取依赖清单**：
   - 读取 Tech_Decisions.md 第1节"依赖清单"
   - 列出所有新增依赖（库名、版本）
   
   **生成任务步骤**：
   ```yaml
   Step 0.1: 更新依赖清单
     sub_steps:
       - 打开 Kobe/Requirements.txt 文件
       - 在文件末尾添加以下依赖（从技术决策提取）：
         * sqlparse==0.4.4  # SQL解析（用途见 Tech_Decisions.md 第1.1节）
         * httpx==0.24.0    # HTTP客户端（用途见 Tech_Decisions.md 第1.2节）
         * [其他依赖...]
       - 保存文件
     acceptance:
       - Requirements.txt 包含所有新增依赖
       - 依赖版本号正确
   
   Step 0.2: 安装依赖
     sub_steps:
       - 激活虚拟环境：cd Kobe && source .venv/bin/activate (Linux/Mac) 或 .venv\Scripts\activate (Windows)
       - 运行：pip install -r Requirements.txt
       - 验证安装：pip list | grep sqlparse
     acceptance:
       - 所有依赖安装成功（无错误）
       - 可以 import sqlparse 无报错
   ```

2. **阶段1：基础结构与配置**

   **从开发计划提取目录结构**：
   - 读取 DevPlan.md 第3节"目录结构规划"
   - 提取需要创建的所有目录和文件
   
   **从技术决策提取配置内容**：
   - 读取 Tech_Decisions.md 第5节"配置文件定义"
   - 提取 .env 模板和 config.py 内容
   
   **生成任务步骤**：
   ```yaml
   Step 1.1: 创建目录结构
     sub_steps:
       - 创建主功能模块目录（从开发计划 DevPlan.md 第3.1节）：
         * mkdir -p Kobe/{功能模块名}
       - 创建子目录（如果需要）：
         * mkdir -p Kobe/{功能模块名}/utils
       - 创建 __init__.py 文件：
         * touch Kobe/{功能模块名}/__init__.py
     acceptance:
       - 所有目录存在
       - __init__.py 文件存在
   
   Step 1.2: 创建配置文件
     sub_steps:
       - 在 Kobe/ 目录创建 .env 文件
       - 复制以下内容到 .env（从技术决策 Tech_Decisions.md 第5.1节）：
         ```
         [完整的 .env 内容，从技术决策文档复制]
         ```
       - 修改敏感配置（如 OPENAI_API_KEY）为实际值
       - 在 Kobe/{功能模块名}/ 创建 config.py 文件
       - 复制以下内容到 config.py（从技术决策 Tech_Decisions.md 第5.2节）：
         ```python
         [完整的 config.py 内容，从技术决策文档复制]
         ```
     acceptance:
       - .env 文件存在且包含所有必需配置
       - config.py 文件存在且可以 import 无报错
       - 运行 from config import settings 无报错
   ```

3. **阶段2：数据模型定义**

   **从技术决策提取数据模型定义**：
   - 读取 Tech_Decisions.md 第4节"数据字段规范"
   - 提取每个模型的完整 Pydantic 定义
   
   **生成任务步骤**：
   ```yaml
   Step 2.1: 创建数据模型文件
     sub_steps:
       - 创建 Kobe/{功能模块名}/models.py 文件
       - 添加基础导入：
         ```python
         from pydantic import BaseModel, Field, EmailStr
         from datetime import datetime
         from uuid import UUID
         ```
       - [P] 定义 UserProfile 模型（从技术决策 Tech_Decisions.md 第4.1节复制完整定义）：
         ```python
         [完整的 Pydantic 模型定义]
         ```
       - [P] 定义其他模型（如果有多个）
     acceptance:
       - models.py 文件存在
       - 所有模型定义完整（字段、类型、验证规则）
       - 可以 from models import UserProfile 无报错
       - 验证示例：profile = UserProfile(user_id="uuid", email="test@test.com") 成功
   ```

4. **阶段3：核心功能实现**

   **从开发计划提取模块接口**：
   - 读取 DevPlan.md 第4节"模块接口设计"
   - 提取每个函数/方法的签名
   
   **从技术决策提取实现细节**：
   - 读取 Tech_Decisions.md 第7节"实现路径映射"
   - 确定每个函数使用什么技术（如 sqlparse、大模型）
   
   **生成任务步骤**：
   ```yaml
   Step 3.1: 实现核心服务逻辑
     sub_steps:
       - 创建 Kobe/{功能模块名}/services.py 文件
       - 添加导入（根据技术决策文档）：
         ```python
         import sqlparse  # SQL解析（见 Tech_Decisions.md 第1.1节）
         from openai import AsyncOpenAI
         from config import settings
         from models import UserProfile
         from Kobe.SharedUtility.RichLogger import get_logger
         
         logger = get_logger(__name__)
         ```
       
       - [P] 实现 parse_sql_file() 函数（从开发计划 DevPlan.md 第4.2节获取函数签名）：
         ```python
         async def parse_sql_file(path: str) -> tuple[list[Table], list[Field]]:
             """
             解析 SQL 文件，提取表和字段信息
             
             参数:
                 path: SQL 文件路径
             
             返回:
                 (tables, fields): 表列表和字段列表
             
             异常:
                 FileNotFoundError: 文件不存在
                 ValueError: 文件格式错误
             """
             logger.info(f"开始解析SQL文件: {path}")
             
             # 使用 sqlparse 解析（配置见 Tech_Decisions.md 第1.1节）
             with open(path, 'r', encoding='utf-8') as f:
                 content = f.read()
             
             parsed = sqlparse.parse(content)
             # [实现解析逻辑]
             
             logger.info(f"解析完成，表数量: {len(tables)}, 字段数量: {len(fields)}")
             return tables, fields
         ```
       
       - [P] 实现 classify_field() 函数（如果需要大模型）：
         ```python
         async def classify_field(field_key: str, samples: list[str]) -> dict:
             """
             使用大模型判断字段是否属于用户画像
             
             提示词模板见 Tech_Decisions.md 第2.1节
             """
             logger.info(f"开始分类字段: {field_key}")
             
             # 构造提示词（从技术决策文档复制完整提示词模板）
             prompt = f"""
             [从 Tech_Decisions.md 第2.1节复制完整的提示词模板]
             
             字段键名: {field_key}
             示例值: {samples}
             """
             
             # 调用大模型（参数见 Tech_Decisions.md 第2.1节）
             client = AsyncOpenAI(api_key=settings.openai_api_key)
             response = await client.chat.completions.create(
                 model=settings.openai_model,
                 messages=[
                     {"role": "system", "content": "你是一个数据库字段分类专家。"},
                     {"role": "user", "content": prompt}
                 ],
                 temperature=0.0,
                 max_tokens=200,
                 timeout=30
             )
             
             # 解析响应
             result = json.loads(response.choices[0].message.content)
             logger.info(f"字段分类完成: {field_key} -> {result['verify']}")
             return result
         ```
     
     acceptance:
       - services.py 文件存在
       - 所有函数定义完整（函数签名、Docstring、实现）
       - Docstring 包含参数、返回值、异常说明
       - 使用 RichLogger 记录关键事件
       - 可以 from services import parse_sql_file 无报错
   ```

5. **阶段4：API路由实现**（如果需要HTTP API）

   **从技术决策提取API路由定义**：
   - 读取 Tech_Decisions.md 第3节"API对接方案"
   - 提取每个端点的完整定义
   
   **生成任务步骤**：
   ```yaml
   Step 4.1: 实现API路由
     sub_steps:
       - 创建 Kobe/{功能模块名}/routers.py 文件
       - 添加导入：
         ```python
         from fastapi import APIRouter, HTTPException, BackgroundTasks
         from models import UserProfile
         from services import parse_sql_file, classify_field
         from Kobe.SharedUtility.RichLogger import get_logger
         
         router = APIRouter(prefix="/api/{功能模块名}", tags=["{功能模块名}"])
         logger = get_logger(__name__)
         ```
       
       - 实现 POST /start 端点（定义见 Tech_Decisions.md 第3.2节）：
         ```python
         @router.post("/start")
         async def start_processing(request: StartRequest):
             """
             启动处理任务
             
             请求格式见 Tech_Decisions.md 第3.2节
             """
             logger.info(f"收到处理请求: {request}")
             
             try:
                 # 调用服务层
                 result = await parse_sql_file(request.file_path)
                 return {"success": True, "result": result}
             except Exception as e:
                 logger.error(f"处理失败: {str(e)}")
                 raise HTTPException(status_code=500, detail=str(e))
         ```
       
       - 在 Kobe/main.py 中注册路由：
         ```python
         from {功能模块名}.routers import router as {功能模块名}_router
         app.include_router({功能模块名}_router)
         ```
     
     acceptance:
       - routers.py 文件存在
       - 所有端点定义完整（路由、请求/响应格式、错误处理）
       - 路由已在 main.py 中注册
       - 启动服务：uvicorn Kobe.main:app --reload 无报错
       - 测试端点（使用 Tech_Decisions.md 第3.2节的测试命令）：
         curl -X POST http://localhost:8000/api/{功能模块名}/start -H "Content-Type: application/json" -d '{...}'
       - 返回正确的响应格式
   ```

6. **阶段5：Celery任务封装**（如果需要后台任务）

   **从技术决策提取任务接口**：
   - 读取 Tech_Decisions.md（如果定义了Celery任务）
   - 或从开发计划 DevPlan.md 第4.4节提取任务接口
   
   **生成任务步骤**：
   ```yaml
   Step 5.1: 实现Celery任务
     sub_steps:
       - 创建 Kobe/{功能模块名}/tasks.py 文件
       - 添加导入：
         ```python
         from Kobe.SharedUtility.TaskQueue import task
         from services import parse_sql_file, classify_field
         from Kobe.SharedUtility.RichLogger import get_logger
         
         logger = get_logger(__name__)
         ```
       
       - 注册 Celery 任务：
         ```python
         @task(name="{功能模块名}.process_data")
         async def process_data_task(file_path: str):
             """
             后台处理任务
             
             任务定义见 Tech_Decisions.md 或 DevPlan.md 第4.4节
             """
             logger.info(f"开始后台任务: {file_path}")
             
             try:
                 result = await parse_sql_file(file_path)
                 logger.info(f"后台任务完成: 处理了 {len(result)} 条记录")
                 return {"success": True, "count": len(result)}
             except Exception as e:
                 logger.error(f"后台任务失败: {str(e)}")
                 raise
         ```
     
     acceptance:
       - tasks.py 文件存在
       - 任务已通过 @task 装饰器注册
       - 任务名称符合规范（{功能模块名}.task_name）
       - 使用 RichLogger 记录关键事件
       - 可以通过 API 或代码调用：process_data_task.delay(file_path)
   ```

7. **阶段6：集成与完善**

   **生成任务步骤**：
   ```yaml
   Step 6.1: 更新模块索引
     sub_steps:
       - 在 Kobe/{功能模块名}/ 创建 index.yaml 文件
       - 添加以下内容：
         ```yaml
         module_name: {功能模块名}
         description: {从开发计划 DevPlan.md 第2.2节提取模块职责描述}
         version: 1.0.0
         
         exports:
           - name: parse_sql_file
             type: function
             path: services.py
             description: 解析SQL文件
           
           - name: UserProfile
             type: model
             path: models.py
             description: 用户画像数据模型
         
         dependencies:
           - RichLogger
           - TaskQueue
         ```
       
       - 更新 Kobe/index.yaml，添加本模块引用：
         ```yaml
         relations:
           - path: {功能模块名}/index.yaml
             type: feature_module
         ```
     
     acceptance:
       - index.yaml 文件存在且格式正确
       - 包含所有导出的函数/类
       - Kobe/index.yaml 已更新
   
   Step 6.2: 编写模块文档
     sub_steps:
       - 在 Kobe/{功能模块名}/ 创建 README.md 文件
       - 添加以下内容：
         ```markdown
         # {功能模块名}
         
         ## 功能说明
         [从需求文档 DemandDescription.md 提取功能描述]
         
         ## 使用方式
         ```python
         from {功能模块名}.services import parse_sql_file
         
         result = await parse_sql_file("path/to/file.sql")
         ```
         
         ## 配置说明
         [从技术决策 Tech_Decisions.md 第5节提取配置说明]
         
         ## API文档
         [如果有API，从技术决策 Tech_Decisions.md 第3节提取]
         ```
     
     acceptance:
       - README.md 文件存在
       - 包含功能说明、使用方式、配置说明
       - 示例代码完整可运行
   ```

8. **阶段7：测试验证**

   **从需求文档提取验收标准**：
   - 读取 DemandDescription.md 第11节"交付与验收标准"
   - 转化为测试用例
   
   **生成任务步骤**：
   ```yaml
   Step 7.1: 编写单元测试
     sub_steps:
       - 创建 Kobe/tests/{功能模块名}/ 目录
       - 创建 test_models.py 文件：
         ```python
         import pytest
         from {功能模块名}.models import UserProfile
         
         def test_user_profile_validation():
             """测试数据模型验证"""
             # 正常情况
             profile = UserProfile(
                 user_id="uuid",
                 email="test@test.com"
             )
             assert profile.email == "test@test.com"
             
             # 异常情况：邮箱格式错误
             with pytest.raises(ValidationError):
                 UserProfile(user_id="uuid", email="invalid")
         ```
       
       - [P] 创建 test_services.py 文件：
         ```python
         import pytest
         from {功能模块名}.services import parse_sql_file
         
         @pytest.mark.asyncio
         async def test_parse_sql_file():
             """测试SQL文件解析"""
             result = await parse_sql_file("test_data/sample.sql")
             assert len(result[0]) > 0  # 有表
             assert len(result[1]) > 0  # 有字段
         ```
       
       - 运行测试：pytest Kobe/tests/{功能模块名}/ -v
     
     acceptance:
       - 测试文件存在
       - 所有核心函数都有测试用例
       - 测试覆盖率 ≥ 70%
       - 所有测试通过（无失败）
   
   Step 7.2: 功能验证测试
     sub_steps:
       - 准备测试数据（从需求文档获取示例数据）
       - 运行完整功能流程：
         * 启动服务（如果有API）：uvicorn Kobe.main:app
         * 调用API端点（使用 Tech_Decisions.md 第3.2节的测试命令）
         * 验证响应格式正确
         * 验证业务逻辑正确（对比需求文档的验收标准）
       - 验证性能指标（从需求文档 DemandDescription.md 第5节提取）：
         * 响应时间 < {要求值}
         * 吞吐量 > {要求值}
       - 验证错误处理：
         * 输入无效数据，验证返回正确错误码
         * 输入边界值，验证处理正确
     
     acceptance:
       - 所有功能点测试通过
       - 性能指标达标
       - 错误处理正确
       - 符合需求文档的验收标准
   ```

9. **更新进度**：任务拆解完成

**输出**：
- 按7个阶段组织的完整任务步骤
- 每个步骤包含详细的 sub_steps
- 所有 sub_steps 都是原子操作

---

### 步骤4：生成任务清单文档

**动作**：
1. **生成文档结构**（必须包含所有技术细节）：

   ```markdown
   # 任务清单：{功能名称}

   标识信息：INTENT_TITLE_2_4={INTENT_TITLE_2_4}；COUNT_3D={COUNT_3D}；生成时间={YYYY-MM-DD HH:mm:ss}
   
   **参考文档**：
   - 需求文档：{DEMAND_PATH}
   - 开发计划：{PLAN_PATH}
   - 技术决策：{TECH_PATH}
   
   输出路径：{TASKS_PATH}

   ---

   ## 技术决策摘要

   **本任务清单基于以下技术决策生成，所有细节请参考技术决策文档**

   ### 新增依赖
   [从技术决策文档 Tech_Decisions.md 第1节提取]
   
   | 依赖 | 版本 | 用途 | 参考 |
   |-----|------|------|------|
   | sqlparse | 0.4.4 | SQL解析 | Tech_Decisions.md 第1.1节 |
   | httpx | 0.24.0 | HTTP客户端 | Tech_Decisions.md 第1.2节 |
   | [其他依赖...] | ... | ... | ... |

   ### 大模型配置（如果需要）
   [从技术决策文档 Tech_Decisions.md 第2节提取]
   
   - 模型：gpt-4o-mini
   - 提示词模板：见 Tech_Decisions.md 第2.1节
   - 调用参数：temperature=0.0, max_tokens=200
   - 批处理：每批50个，并发60/分钟

   ### API配置（如果需要）
   [从技术决策文档 Tech_Decisions.md 第3节提取]
   
   - 端口：8000（接入现有服务）
   - 路由前缀：/api/{功能模块名}/
   - 端点清单：见 Tech_Decisions.md 第3.2节

   ### 数据模型
   [从技术决策文档 Tech_Decisions.md 第4节提取]
   
   - UserProfile：见 Tech_Decisions.md 第4.1节（完整Pydantic定义）
   - [其他模型...]

   ### 配置文件
   [从技术决策文档 Tech_Decisions.md 第5节提取]
   
   - .env：见 Tech_Decisions.md 第5.1节（完整模板）
   - config.py：见 Tech_Decisions.md 第5.2节（完整代码）

   ---

   ## 任务清单

   [从步骤3生成的任务步骤复制，保持完整]

   ### 阶段0：环境准备与依赖安装
   
   **Step 0.1**: 更新依赖清单
   - sub_steps:
     - 打开 Kobe/Requirements.txt 文件
     - 在文件末尾添加以下依赖：
       * sqlparse==0.4.4  # SQL解析（用途见 Tech_Decisions.md 第1.1节）
       * httpx==0.24.0    # HTTP客户端（用途见 Tech_Decisions.md 第1.2节）
       * [其他依赖...]
     - 保存文件
   - acceptance:
     - Requirements.txt 包含所有新增依赖
     - 依赖版本号正确

   [继续所有阶段和步骤...]

   ---

   ## 执行顺序说明

   1. **严格按阶段顺序执行**（阶段0 → 阶段7）
   2. **阶段内并行任务** [P] 可同时执行
   3. **依赖关系**：
      - 配置文件（Step 1.2）必须在所有使用配置的步骤之前
      - 数据模型（Step 2.1）必须在业务逻辑（Step 3.1）之前
      - 业务逻辑（Step 3.1）必须在API路由（Step 4.1）之前
   4. **验收标准**：每完成一个 Step，验证 acceptance 是否满足

   ---

   ## 性能验证清单

   [从需求文档 DemandDescription.md 第5节提取]
   
   - [ ] 响应时间 < {指标}
   - [ ] 吞吐量 > {指标}
   - [ ] 并发支持 ≥ {指标}

   ---

   ## 功能验收清单

   [从需求文档 DemandDescription.md 第11节提取]
   
   - [ ] 功能1：{描述}
   - [ ] 功能2：{描述}
   - [ ] 交付物1：{文件名}
   - [ ] 交付物2：{文件名}

   ---

   ## 规范引用

   - `CodexFeatured/Common/BackendConstitution.yaml` - 技术栈约束
   - `CodexFeatured/Common/CodeCommentStandard.yaml` - 注释规范
   - `DemandDescription.md` - 需求文档
   - `DevPlan.md` - 开发计划
   - `Tech_Decisions.md` - 技术决策

   **工作流版本**：2.1 | **生成时间**：{YYYY-MM-DD HH:mm:ss}
   ```

2. **写入文件**：
   ```
   写入文件：${TASKS_PATH}
   编码：UTF-8（无BOM）
   ```

3. **更新进度**：任务清单文档生成完成

**输出文件**：`${TASKS_PATH}`

---

### 步骤5：规范对齐验证（质量门控）

*门控：必须在输出文档前通过。最多尝试3轮修正。*

**动作**：
1. **执行验证检查**：

   **检查1：前置文档引用完整性**
   - 验证任务步骤中引用了技术决策文档
   - 验证依赖安装步骤使用了 Tech_Decisions.md 的依赖清单
   - 验证配置文件步骤使用了 Tech_Decisions.md 的配置内容
   - 验证数据模型步骤使用了 Tech_Decisions.md 的字段定义
   → 如果缺少引用：FAIL "任务步骤未引用技术决策文档"

   **检查2：业务目标覆盖度**
   - 对比需求文档的功能需求与任务清单
   - 验证每个功能点都有对应的任务步骤
   - 验证每个交付物都有生成步骤
   → 如果缺少覆盖：FAIL "功能点 {功能点} 无对应任务步骤"

   **检查3：任务原子性**
   - 随机抽查10个 sub_step
   - 验证是否可手动执行
   - 验证是否有明确产出
   → 如果不满足：FAIL "sub_step 不满足原子性: {内容}"

   **检查4：技术细节完整性**（重要！）
   - 验证依赖安装步骤包含具体的库名和版本
   - 验证配置文件步骤包含完整的配置内容
   - 验证提示词步骤包含完整的提示词模板（如果需要大模型）
   - 验证API步骤包含具体的路由和测试命令（如果需要API）
   → 如果不完整：FAIL "技术细节不完整: {详情}"

   **检查5：验收标准完整性**
   - 验证每个 Step 都有 acceptance 清单
   - 验证 acceptance 包含可测试的条件
   → 如果缺少：FAIL "Step {编号} 缺少验收标准"

2. **处理验证结果**：
   → 如果所有检查通过：
     * 更新进度：质量门控通过
     * 继续步骤6
   → 如果任何检查失败：
     * 修正内容
     * 重新写入
     * 重新验证（最多3轮）
     * 如果3轮后仍失败：ERROR "质量门控验证失败: {详情}"

3. **更新进度**：质量门控验证通过

---

### 步骤6：完成与报告

**动作**：
1. **输出执行摘要**：
   ```markdown
   ## 任务清单生成完成

   **输出文件**：{TASKS_PATH}
   **编号**：{COUNT_3D}
   **意图标识**：{INTENT_TITLE_2_4}
   **生成时间**：{YYYY-MM-DD HH:mm:ss}

   **任务统计**：
   - 阶段数量：{数量}
   - 任务步骤数量：{数量}
   - 并行任务数量：{数量}
   - 新增依赖数量：{数量}
   - 复用模块数量：{数量}

   **参考文档**：
   - 需求文档：{DEMAND_PATH}
   - 开发计划：{PLAN_PATH}
   - 技术决策：{TECH_PATH}

   **关键改进**：
   - 任务步骤包含所有技术细节（依赖、提示词、配置、字段）
   - 每个步骤都引用了对应的技术决策章节
   - 任务原子性：每个 sub_step 可手动执行

   **下一步**：
   请使用 DevPiplineExcute 工作流执行此任务清单，完成功能开发。
   ```

2. **更新进度**：工作流执行完成

---

## 进度跟踪

*此检查清单在执行流程中更新*

**阶段状态**：
- [ ] 步骤1：所有前置文档加载完成
- [ ] 步骤2：任务上下文构建完成
- [ ] 步骤3：任务拆解完成（7个阶段）
- [ ] 步骤4：任务清单文档生成完成
- [ ] 步骤5：质量门控验证通过
- [ ] 步骤6：工作流执行完成

**质量门控状态**：
- [ ] 前置文档引用完整性检查：通过
- [ ] 业务目标覆盖度检查：通过
- [ ] 任务原子性检查：通过
- [ ] 技术细节完整性检查：通过
- [ ] 验收标准完整性检查：通过

---

## 验收标准（Acceptance Criteria）

**输出文件要求**：
- [ ] 输出路径符合 `${TASKS_PATH}`（与前置文档同目录）
- [ ] 文件编码为 UTF-8（无BOM）
- [ ] 文件大小 > 15KB（确保详细）

**文档结构要求**：
- [ ] 包含"技术决策摘要"章节（引用 Tech_Decisions.md）
- [ ] 包含所有7个阶段的任务清单
- [ ] 包含"执行顺序说明"章节
- [ ] 包含"性能验证清单"和"功能验收清单"

**技术细节要求**（关键！）：
- [ ] 依赖安装步骤包含具体库名和版本（从 Tech_Decisions.md 提取）
- [ ] 配置文件步骤包含完整内容（从 Tech_Decisions.md 复制）
- [ ] 数据模型步骤包含完整 Pydantic 定义（从 Tech_Decisions.md 复制）
- [ ] 提示词步骤包含完整模板（如果需要大模型，从 Tech_Decisions.md 复制）
- [ ] API步骤包含路由定义和测试命令（如果需要API，从 Tech_Decisions.md 复制）

**引用完整性要求**：
- [ ] 每个技术步骤都注明参考章节（如"见 Tech_Decisions.md 第1.1节"）
- [ ] 任务步骤覆盖 Tech_Decisions.md 的所有关键技术决策

**任务拆解要求**：
- [ ] 每个 sub_step 是原子操作（可手动执行、有明确产出、可验证）
- [ ] 每个 Step 包含明确的 acceptance
- [ ] 并行任务标记 `[P]`
- [ ] 任务依赖顺序合理

**业务覆盖要求**：
- [ ] 需求文档的所有核心功能点都有对应任务步骤
- [ ] 需求文档声明的所有交付物都有生成步骤
- [ ] 性能验证清单与需求文档的性能指标一致

---

## 错误处理约定

**ERROR 级别**（终止执行）：
- 任何前置文档未找到（需求、开发计划、技术决策）
- 前置文档标识信息缺失
- 质量门控验证失败（3轮后仍未通过）
- 技术细节不完整（缺少依赖/配置/提示词定义）
- 需求点无对应任务步骤

**WARN 级别**（记录警告但继续）：
- 任务清单已存在（可选覆盖）
- 任务依赖顺序可能不合理

---

## 规范引用

**项目规范**：
- `CodexFeatured/Common/BackendConstitution.yaml` - 技术栈约束与禁止项
- `CodexFeatured/Common/CodeCommentStandard.yaml` - 注释风格要求
- `CodexFeatured/Common/BestPractise.yaml` - 最佳实践指南

**前置文档**：
- `DemandDescription.md` - 需求文档（业务需求）
- `DevPlan.md` - 开发计划（架构设计）
- `Tech_Decisions.md` - 技术决策（技术细节）

**工作流版本**：2.1 | **最后更新**：2025-10-11

---

*基于 SpecKit 工程实践 v2.1.1 - 综合参考需求、架构、技术三份文档*
