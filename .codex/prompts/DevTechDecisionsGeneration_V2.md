---
description: 工程化"技术决策文档生成"工作流 - 定义具体的技术实现细节
version: 2.0
language: zh-CN
upstream: DevPlanGeneration_V2
downstream: DevPipelineGeneration_V2
scripts:
  ps: CodexFeatured/Scripts/get-tech-context.ps1 -Json
---

# TechDecisionsGeneration - 技术决策文档生成工作流

## 工作流概述

**目标**：读取需求文档和开发计划，定义所有技术实现细节，生成完整的技术决策文档。

**核心原则**：
- 聚焦技术层面的"用什么、怎么配置"
- 所有依赖必须指定具体库名和版本
- 所有提示词必须完整定义（如果需要大模型）
- 所有接口必须明确端口和路由
- 所有字段必须定义规范和示例

**输入**：
- 需求文档 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/DemandDescription.md`
- 开发计划 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/DevPlan.md`

**输出**：技术决策文档 `CodexFeatured/DevPlans/{COUNT_3D}_{INTENT_TITLE_2_4}/Tech_Decisions.md`

---

## 参数定义

```yaml
OUTPUT_DIR_PATH: "D:/AI_Projects/CodexFeatured/DevPlans"
COUNT_3D: "{{RUNTIME_RESOLVE}}"          # 从文档解析
INTENT_TITLE_2_4: "{{RUNTIME_RESOLVE}}"  # 从文档解析
DEMAND_FILENAME: "DemandDescription.md"
PLAN_FILENAME: "DevPlan.md"
TECH_FILENAME: "Tech_Decisions.md"
TARGET_DIR: "${OUTPUT_DIR_PATH}/${COUNT_3D}_${INTENT_TITLE_2_4}"
DEMAND_PATH: "${TARGET_DIR}/${DEMAND_FILENAME}"
PLAN_PATH: "${TARGET_DIR}/${PLAN_FILENAME}"
TECH_PATH: "${TARGET_DIR}/${TECH_FILENAME}"
```

---

## 执行流程（TechDecisionsGeneration 工作流范围）

**用户输入处理**：

$ARGUMENTS

---

### 步骤1：加载需求文档与开发计划

**动作**：
1. **运行上下文获取脚本**：
   ```
   从仓库根目录运行 `{SCRIPT}` 并解析JSON获取：
   - TARGET_DIR: 目标目录
   - EXISTING_TECH: 是否已存在 Tech_Decisions.md
   ```

2. **定位目标文档**：
   - 扫描最新的开发计划文档（DevPlan.md）
   → 如果未找到：ERROR "未找到开发计划，请先运行 DevPlanGeneration"
   - 读取标识信息：COUNT_3D、INTENT_TITLE_2_4
   - 设置路径：DEMAND_PATH、PLAN_PATH、TECH_PATH

3. **读取需求文档**：
   - 读取 `${DEMAND_PATH}` 完整内容
   - 提取关键信息：
     * 性能要求（响应时间、吞吐量、并发）
     * 数据需求（数据来源、类型、量级）
     * 安全要求（数据敏感性、访问控制）
     * 项目约束（技术栈、路径、环境变量）

4. **读取开发计划**：
   - 读取 `${PLAN_PATH}` 完整内容
   - 提取关键信息：
     * 功能域与模块清单
     * 架构分层设计
     * 目录结构规划
     * 数据模型定义
     * API接口规范（如果有）
     * Celery任务接口（如果有）
     * 外部依赖清单（需要什么能力）

5. **验证技术决策文件状态**：
   → 如果 `${TECH_PATH}` 已存在：
     * WARN "技术决策文档已存在，将覆盖"

6. **更新进度**：文档加载完成

**输出**：
- 需求文档核心信息
- 开发计划核心信息
- 外部依赖清单（待定义具体库）

---

### 步骤2：加载项目规范与调研准备

**动作**：
1. **加载项目规范**：
   - 读取 `CodexFeatured/Common/BackendConstitution.yaml`：
     * 技术栈定义（Python版本、框架、存储）
     * 强制要求（mandates）
     * 禁止项（prohibitions）
     * 基础设施配置（Redis、MongoDB、RabbitMQ等）
   - 读取 `CodexFeatured/Common/BestPractise.yaml`：
     * 官方文档链接索引

2. **提取调研需求**：
   - 从开发计划的"外部依赖清单"中提取需要调研的能力：
     * 示例："需要SQL解析能力" → 调研 SQL 解析库
     * 示例："需要异步HTTP客户端" → 调研 HTTP 客户端库
     * 示例："需要大模型交互" → 调研大模型SDK
   - 列出所有需要调研的技术点

3. **更新进度**：调研准备完成

**输出**：
- 项目规范约束
- 调研需求清单

---

### 步骤3：技术选型与调研（质量门控点）

*门控：所有依赖必须基于官方文档调研，必须验证兼容性*

**动作**：
1. **对每个调研需求，执行技术选型**：

   **选型流程**（对每个需求）：
   a. **确定候选库**：
      - 搜索并列出 2-3 个候选库
      - 示例："SQL解析" → `sqlparse`、`pglast`、`sqlglot`
   
   b. **调研官方文档**：
      - 访问官方文档（优先 ReadTheDocs、官方GitHub）
      - 验证功能满足需求
      - 查看快速开始示例
      - 查看最佳实践建议
      - 记录推荐版本
   
   c. **验证兼容性**：
      - Python 版本兼容（≥ 3.10）
      - 异步I/O支持（asyncio 兼容）
      - 类型注解支持（type hints）
      - Pydantic v2 兼容（如果涉及数据验证）
   
   d. **评估社区成熟度**：
      - GitHub stars（≥ 500为佳）
      - 最近更新时间（≤ 6个月为佳）
      - Issue响应速度
      - 下载量（PyPI）
   
   e. **做出选择**：
      - 选择最符合需求的库
      - 记录选型理由（100-200字）
      - 记录官方文档链接
      - 记录推荐版本
   
   f. **记录配置示例**：
      - 从官方文档摘录初始化示例
      - 从官方文档摘录常用配置
      - 标注注意事项

2. **验证所有依赖已选型**：
   → 如果有依赖未选型：ERROR "依赖 {依赖名} 未完成选型"
   → 如果有依赖未调研官方文档：ERROR "依赖 {依赖名} 缺少官方文档调研"
   → 如果有依赖不兼容项目约束：ERROR "依赖 {依赖名} 不兼容: {冲突详情}"

3. **更新进度**：技术选型完成（门控通过）

**输出**：
- 完整的依赖清单（库名、版本、选型理由、官方文档、配置示例）

---

### 步骤4：大模型提示词定义（如果需要）

**动作**：
1. **判断是否需要大模型**：
   - 从需求文档判断：
     * 是否涉及自然语言处理
     * 是否涉及内容生成
     * 是否涉及智能分析
   → 如果不需要：跳过此步骤

2. **确定大模型用途**：
   - 列出所有需要大模型的场景：
     * 场景1：{描述，如"判断字段是否属于用户画像"}
     * 场景2：{描述}
   - 对每个场景，确定：
     * 输入格式
     * 期望输出格式
     * 准确度要求

3. **定义提示词模板**（重要！必须非常详细）：

   **对于每个场景，定义完整的提示词**：
   
   **示例：字段分类场景**
   ```yaml
   场景: 判断数据库字段是否属于用户画像
   
   提示词模板: |
     你是一个数据库字段分类专家。现在需要判断以下字段是否属于"用户画像"类别。
     
     **判断标准**：
     - 用户画像字段：直接描述用户个人特征的字段，如姓名、年龄、地址、联系方式等
     - 非用户画像字段：系统字段、业务字段、日志字段等
     
     **输入信息**：
     - 字段键名：{field_key}
     - 示例值：{samples}
     
     **输出要求**：
     请严格按照以下 JSON 格式输出，不要包含任何其他文字：
     {{
       "verify": "true|false|verify",
       "reason": "中文判定理由（30-50字）",
       "confidence": 0.0-1.0
     }}
     
     **说明**：
     - verify = "true"：确定属于用户画像
     - verify = "false"：确定不属于用户画像
     - verify = "verify"：不确定，需要人工复核
     - reason：简要说明判定依据（不要包含原始数据）
     - confidence：置信度（0.0-1.0）
   
   输入变量:
     - field_key: 字段键名（如 "UserHomeAddress"）
     - samples: 示例值列表（如 ["xx省xx市...", "路名..."]）
   
   输出格式: JSON
   
   解析方法: json.loads(response)
   
   错误处理:
     - 如果输出不是有效JSON：重试（最多3次）
     - 如果 verify 不是 "true|false|verify"：标记为 "verify"
   
   使用示例:
     输入: field_key="UserEmail", samples=["user@example.com", "test@test.com"]
     输出: {"verify": "true", "reason": "邮箱地址属于用户联系方式", "confidence": 0.95}
   ```

4. **定义调用参数**：
   - 模型名称：从项目规范获取（如 `gpt-4o-mini`）
   - API Key 环境变量：`OPENAI_API_KEY`
   - 温度参数：`temperature=0.0`（确保一致性）
   - 最大tokens：`max_tokens=200`
   - 超时设置：`timeout=30`秒
   - 重试策略：最大3次，指数退避

5. **定义批处理策略**（如果需要大量调用）：
   - 批处理大小：每批 20-50 个请求
   - 并发控制：每分钟最多 60 个请求
   - 进度保存：每处理100个保存一次中间结果

6. **验证提示词完整性**：
   → 如果提示词模板不完整：FAIL "提示词模板缺少: {缺少项}"
   → 如果输出格式未定义：FAIL "提示词输出格式未定义"
   → 如果错误处理未定义：FAIL "提示词错误处理未定义"

7. **更新进度**：大模型提示词定义完成

**输出**：
- 完整的提示词模板（每个场景）
- 调用参数配置
- 批处理策略（如适用）

---

### 步骤5：API对接方案定义（如果需要）

**动作**：
1. **判断是否需要HTTP API**：
   - 从开发计划判断：
     * 是否定义了 API 接口规范
     * 是否需要对外提供HTTP服务
   → 如果不需要：跳过此步骤

2. **确定端口分配**：
   - 读取项目现有端口占用：
     * 从 `BackendConstitution.yaml` 获取主服务端口（如 8000）
     * 扫描现有服务占用的端口
   - 分配新端口（如果需要独立服务）：
     * 避免冲突
     * 记录端口用途
   - 或确定接入现有服务：
     * 主服务端口：8000
     * 接入方式：添加新的路由

3. **定义路由规划**：
   
   **对于每个API端点**（从开发计划的API接口规范提取）：
   
   ```yaml
   端点: POST /api/users/register
   
   路由定义:
     method: POST
     path: /api/users/register
     handler: routers.user.register_user
     middleware: []  # 不需要认证
   
   请求格式:
     content_type: application/json
     schema:
       email:
         type: string
         required: true
         format: email
         example: "user@example.com"
       password:
         type: string
         required: true
         min_length: 8
         example: "password123"
   
   响应格式:
     success (200):
       content_type: application/json
       schema:
         user_id:
           type: string
           example: "uuid-1234"
         token:
           type: string
           example: "jwt_token_xxx"
     
     error (400):
       content_type: application/json
       schema:
         error:
           type: string
           example: "Invalid email format"
     
     error (409):
       content_type: application/json
       schema:
         error:
           type: string
           example: "User already exists"
   
   认证要求: 无
   
   速率限制: 10次/分钟（per IP）
   
   超时设置: 5秒
   
   实现文件: Kobe/{功能模块名}/routers.py
   
   测试命令:
     curl -X POST http://localhost:8000/api/users/register \
       -H "Content-Type: application/json" \
       -d '{"email":"user@example.com","password":"password123"}'
   ```

4. **定义中间件需求**（如果需要）：
   - 认证中间件：
     * 验证JWT token
     * 提取用户信息
   - 日志中间件：
     * 记录请求/响应
     * 记录耗时
   - 错误处理中间件：
     * 统一错误格式
     * 异常捕获

5. **定义CORS配置**（如果前后端分离）：
   ```yaml
   CORS配置:
     allow_origins: ["http://localhost:3000", "https://yourdomain.com"]
     allow_methods: ["GET", "POST", "PUT", "DELETE"]
     allow_headers: ["Content-Type", "Authorization"]
     allow_credentials: true
   ```

6. **更新进度**：API对接方案定义完成

**输出**：
- 端口分配方案
- 完整的路由定义（每个端点）
- 中间件需求
- CORS配置（如适用）

---

### 步骤6：数据字段规范定义

**动作**：
1. **提取数据模型**：
   - 从开发计划的"模块接口设计"提取所有数据模型
   - 列出所有需要定义字段规范的模型

2. **对每个数据模型，定义完整的字段规范**：

   **示例：UserProfile 模型**
   ```yaml
   模型: UserProfile
   
   用途: 用户画像数据结构
   
   字段规范:
     user_id:
       类型: str
       必需: true
       格式: UUID v4
       长度: 36
       示例: "550e8400-e29b-41d4-a716-446655440000"
       验证: 符合UUID格式
       索引: 主键
     
     email:
       类型: str
       必需: true
       格式: email
       最大长度: 255
       示例: "user@example.com"
       验证: 符合邮箱格式，唯一性
       索引: 唯一索引
     
     full_name:
       类型: str
       必需: false
       最大长度: 100
       示例: "张三"
       验证: 不含特殊字符
       默认值: null
     
     age:
       类型: int
       必需: false
       范围: 1-150
       示例: 25
       验证: 正整数，1-150范围
       默认值: null
     
     created_at:
       类型: datetime
       必需: true
       格式: ISO 8601
       示例: "2025-10-11T12:00:00Z"
       验证: 有效日期时间
       默认值: 当前时间
       索引: 普通索引
   
   Pydantic定义:
     from pydantic import BaseModel, Field, EmailStr
     from datetime import datetime
     from uuid import UUID
     
     class UserProfile(BaseModel):
         """用户画像数据模型"""
         user_id: UUID = Field(..., description="用户ID")
         email: EmailStr = Field(..., description="邮箱")
         full_name: str | None = Field(None, max_length=100, description="姓名")
         age: int | None = Field(None, ge=1, le=150, description="年龄")
         created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
   
   存储方式: MongoDB collection "user_profiles"
   
   索引定义:
     - user_id: 主键
     - email: 唯一索引
     - created_at: 普通索引（查询优化）
   ```

3. **定义字段命名规范**：
   - Python代码中：snake_case（如 `user_id`、`full_name`）
   - 数据库中：snake_case（如 `user_id`、`created_at`）
   - API JSON中：camelCase（如 `userId`、`fullName`）
   - 转换规则：
     ```python
     # Python → JSON
     {"user_id": "123"} → {"userId": "123"}
     
     # JSON → Python
     {"userId": "123"} → {"user_id": "123"}
     ```

4. **定义数据转换规则**（如果需要）：
   - 输入数据转换：
     * 去除前后空格
     * 统一编码（UTF-8）
     * 类型转换（字符串 → 整数）
   - 输出数据转换：
     * 脱敏处理（邮箱、手机号）
     * 格式化（日期时间、数值）

5. **更新进度**：数据字段规范定义完成

**输出**：
- 完整的字段规范（每个模型）
- 字段命名规范
- 数据转换规则

---

### 步骤7：配置文件详细定义

**动作**：
1. **确定配置文件类型**：
   - 环境变量文件：`.env`（敏感配置）
   - 应用配置文件：`config.py`（业务配置）
   - 日志配置文件：`logging_config.yaml`（如果需要）

2. **定义 .env 文件内容**：
   ```env
   # 数据库配置
   MONGODB_URI=mongodb://localhost:27017
   REDIS_URL=redis://localhost:6379/0
   
   # 消息队列配置
   RABBITMQ_URL=amqp://guest:guest@localhost:5672/
   
   # 大模型配置
   OPENAI_API_KEY=sk-xxxxxxxxxxxxx
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_BASE_URL=https://api.openai.com/v1
   
   # 应用配置
   APP_ENV=development
   DEBUG=true
   LOG_LEVEL=INFO
   
   # API配置
   API_PORT=8000
   API_HOST=0.0.0.0
   
   # 功能模块配置
   {功能模块特定配置}
   FEATURE_ENABLED=true
   BATCH_SIZE=50
   TIMEOUT=30
   ```

3. **定义 config.py 文件内容**：
   ```python
   from pydantic_settings import BaseSettings
   from pydantic import Field
   
   class Settings(BaseSettings):
       """应用配置"""
       
       # 数据库配置
       mongodb_uri: str = Field(..., env="MONGODB_URI")
       redis_url: str = Field(..., env="REDIS_URL")
       
       # 大模型配置
       openai_api_key: str = Field(..., env="OPENAI_API_KEY")
       openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
       
       # 应用配置
       app_env: str = Field(default="development", env="APP_ENV")
       debug: bool = Field(default=False, env="DEBUG")
       log_level: str = Field(default="INFO", env="LOG_LEVEL")
       
       # API配置
       api_port: int = Field(default=8000, env="API_PORT")
       api_host: str = Field(default="0.0.0.0", env="API_HOST")
       
       # 功能模块配置
       batch_size: int = Field(default=50, env="BATCH_SIZE")
       timeout: int = Field(default=30, env="TIMEOUT")
       
       class Config:
           env_file = ".env"
           case_sensitive = False
   
   settings = Settings()
   ```

4. **定义配置验证规则**：
   - 必需配置检查：启动时验证
   - 配置格式检查：类型验证、范围验证
   - 配置兼容性检查：相互依赖的配置

5. **定义配置使用示例**：
   ```python
   from config import settings
   
   # 使用配置
   client = MongoClient(settings.mongodb_uri)
   api_port = settings.api_port
   ```

6. **更新进度**：配置文件定义完成

**输出**：
- 完整的 .env 文件模板
- 完整的 config.py 文件内容
- 配置验证规则
- 配置使用示例

---

### 步骤8：明确边界与约束

**动作**：
1. **定义"做什么"**：
   - 从需求文档和开发计划提取
   - 明确列出所有要实现的功能
   - 明确列出所有要生成的文件

2. **定义"不做什么"**：
   - 明确排除的功能：
     * 示例："不包含用户管理界面"
     * 示例："不包含实时数据同步"
   - 明确排除的技术：
     * 示例："不使用 GraphQL"
     * 示例："不引入前端框架"

3. **定义技术边界**：
   - 与现有系统的集成方式：
     * 复用现有模块：{列表}
     * 对接现有接口：{列表}
     * 独立运行：是/否
   - 数据边界：
     * 只读外部数据：{列表}
     * 写入外部数据：{列表}
     * 独立数据存储：是/否

4. **定义性能边界**：
   - 从需求文档提取性能要求
   - 转化为技术指标：
     * 响应时间 < 500ms → 数据库查询优化、缓存策略
     * 吞吐量 > 1000/s → 异步处理、批处理
     * 并发 ≥ 100 → 连接池配置、限流策略

5. **更新进度**：边界与约束定义完成

**输出**：
- "做什么"清单
- "不做什么"清单
- 技术边界说明
- 性能边界与实现策略

---

### 步骤9：生成技术决策文档

**动作**：
1. **生成文档结构**（必须非常详细！≥ 5000字）：

   ```markdown
   # 技术决策文档：{功能名称}

   标识信息：INTENT_TITLE_2_4={INTENT_TITLE_2_4}；COUNT_3D={COUNT_3D}；生成时间={YYYY-MM-DD HH:mm:ss}
   需求文档：{DEMAND_PATH}
   开发计划：{PLAN_PATH}
   输出路径：{TECH_PATH}

   ---

   ## 1. 依赖清单

   ### 1.1 新增依赖

   [从步骤3提取，每个依赖详细说明]

   #### sqlparse
   - **用途**：SQL语句解析
   - **版本**：^0.4.4
   - **选型理由**（200字）：
     sqlparse 是 Python 社区最成熟的SQL解析库，支持多种SQL方言。
     官方文档完整，提供了丰富的解析API。经验证与Python 3.10+完全兼容，
     支持异步操作（通过 asyncio.to_thread）。社区活跃，GitHub 3.5k stars，
     最近更新在3个月内。相比其他候选库（pglast仅支持PostgreSQL，sqlglot
     性能较高但API复杂），sqlparse 最适合我们的场景。
   - **官方文档**：https://sqlparse.readthedocs.io/
   - **安装命令**：`pip install sqlparse==0.4.4`
   - **兼容性验证**：
     * Python 3.10+：✓
     * Asyncio兼容：✓（通过 to_thread）
     * 类型注解：✓
   - **配置示例**：
     ```python
     import sqlparse
     
     # 基本用法
     parsed = sqlparse.parse("SELECT * FROM users")[0]
     
     # 格式化SQL
     formatted = sqlparse.format(
         "SELECT * FROM users",
         reindent=True,
         keyword_case='upper'
     )
     ```
   - **注意事项**：
     * 大文件解析时注意内存占用
     * 使用 `sqlparse.split()` 分割多条SQL语句

   [重复其他依赖，每个依赖同样详细]

   ### 1.2 项目现有依赖（复用）

   | 依赖 | 版本 | 用途 |
   |-----|------|------|
   | pydantic | ^2.7 | 数据验证 |
   | fastapi | latest | Web框架（如果需要API） |
   | celery | latest | 任务队列（如果需要后台任务） |

   ---

   ## 2. 大模型提示词定义

   [从步骤4提取，如果需要]

   ### 2.1 场景1：字段分类

   **场景描述**：判断数据库字段是否属于用户画像

   **提示词模板**（完整版本）：
   ```
   [从步骤4复制完整的提示词模板，包含所有细节]
   ```

   **输入变量**：
   - `field_key`：字段键名（字符串）
   - `samples`：示例值列表（字符串数组，最多20个）

   **输出格式**：JSON
   ```json
   {
     "verify": "true|false|verify",
     "reason": "中文判定理由（30-50字）",
     "confidence": 0.0-1.0
   }
   ```

   **调用参数**：
   ```python
   from openai import AsyncOpenAI
   from config import settings
   
   client = AsyncOpenAI(
       api_key=settings.openai_api_key,
       base_url=settings.openai_base_url
   )
   
   response = await client.chat.completions.create(
       model=settings.openai_model,  # "gpt-4o-mini"
       messages=[
           {"role": "system", "content": "你是一个数据库字段分类专家。"},
           {"role": "user", "content": prompt}
       ],
       temperature=0.0,
       max_tokens=200,
       timeout=30
   )
   ```

   **错误处理**：
   - 超时：重试3次，指数退避（1s, 2s, 4s）
   - 限流：等待60秒后重试
   - 解析失败：标记为 "verify"（需人工复核）

   **批处理策略**：
   - 批处理大小：每批50个字段
   - 并发控制：每分钟最多60个请求
   - 进度保存：每处理100个保存一次

   **成本估算**：
   - 单次调用tokens：约150 tokens
   - 1000个字段：约150k tokens
   - 成本：约 $0.03（gpt-4o-mini pricing）

   [重复其他场景]

   ---

   ## 3. API对接方案

   [从步骤5提取，如果需要]

   ### 3.1 端口分配

   - **主服务端口**：8000（现有FastAPI服务）
   - **接入方式**：添加新的路由模块
   - **路由前缀**：`/api/{功能模块名}/`

   ### 3.2 路由定义

   [从步骤5复制每个端点的完整定义]

   #### POST /api/{功能模块名}/start
   ```yaml
   [完整的路由定义，包含请求/响应格式、认证、测试命令]
   ```

   ### 3.3 中间件配置

   [如果需要]

   #### 认证中间件
   ```python
   from fastapi import Depends, HTTPException
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   async def verify_token(token: str = Depends(security)):
       # 验证JWT token
       pass
   ```

   ### 3.4 CORS配置

   [如果需要前后端分离]
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

   ---

   ## 4. 数据字段规范

   [从步骤6提取]

   ### 4.1 数据模型定义

   [从步骤6复制每个模型的完整定义]

   #### UserProfile
   ```yaml
   [完整的字段规范，包含类型、验证、示例、Pydantic定义]
   ```

   ### 4.2 字段命名规范

   - Python代码：snake_case
   - 数据库：snake_case
   - API JSON：camelCase
   - 转换方法：
     ```python
     def to_camel_case(snake_str: str) -> str:
         components = snake_str.split('_')
         return components[0] + ''.join(x.title() for x in components[1:])
     ```

   ### 4.3 数据转换规则

   [如果需要]

   ---

   ## 5. 配置文件定义

   [从步骤7提取]

   ### 5.1 环境变量（.env）

   ```env
   [从步骤7复制完整的 .env 模板]
   ```

   **说明**：
   - `OPENAI_API_KEY`：从 OpenAI 官网获取
   - `MONGODB_URI`：本地开发使用 localhost，生产使用实际地址

   ### 5.2 应用配置（config.py）

   ```python
   [从步骤7复制完整的 config.py 内容]
   ```

   ### 5.3 配置验证

   启动时自动验证：
   - 必需配置存在性检查
   - 配置格式检查
   - 数据库连接测试

   ---

   ## 6. 边界与约束

   [从步骤8提取]

   ### 6.1 功能边界

   **包含功能**：
   - 功能1：{描述}
   - 功能2：{描述}

   **不包含功能**：
   - 不包含1：{描述}
   - 不包含2：{描述}

   ### 6.2 技术边界

   **与现有系统集成**：
   - 复用模块：RichLogger、TaskQueue
   - 对接接口：FastAPI主服务（8000端口）
   - 独立数据存储：否（使用现有MongoDB）

   **数据边界**：
   - 只读：SQL文件（外部输入）
   - 写入：分类结果（MongoDB）
   - 临时存储：中间数据（本地JSON文件）

   ### 6.3 性能边界

   [从需求文档提取性能要求并转化为技术策略]

   | 性能要求 | 技术策略 |
   |---------|---------|
   | 响应时间 < 500ms | 数据库索引优化、Redis缓存 |
   | 吞吐量 > 1000/s | 异步处理、批处理 |
   | 并发 ≥ 100 | 连接池（size=20）、限流（100/s） |

   ---

   ## 7. 实现路径映射

   [将技术决策映射到具体文件]

   | 技术决策 | 实现文件 | 备注 |
   |---------|---------|------|
   | sqlparse SQL解析 | `services.py` | 在 `parse_sql_file()` 函数中使用 |
   | 大模型字段分类 | `tasks.py` | 在 `classify_fields()` 任务中调用 |
   | API端点 `/start` | `routers.py` | FastAPI路由定义 |
   | UserProfile模型 | `models.py` | Pydantic模型定义 |
   | 配置管理 | `config.py` | 读取 .env 文件 |

   ---

   ## 8. 测试策略

   ### 8.1 单元测试

   - 测试模块：models, services, utils
   - 测试框架：pytest
   - 覆盖率要求：≥ 80%

   ### 8.2 集成测试

   - 测试场景：完整业务流程
   - 测试数据：使用真实SQL样本
   - 验收标准：功能正确性 + 性能达标

   ### 8.3 大模型测试（如适用）

   - 测试数据集：100个标注字段
   - 准确率要求：≥ 95%
   - 成本控制：测试成本 < $0.10

   ---

   ## 9. 部署与运维

   ### 9.1 部署方式

   - 开发环境：本地运行
   - 生产环境：Docker容器部署

   ### 9.2 监控指标

   - API响应时间
   - 大模型调用成功率（如适用）
   - 任务队列长度（如适用）
   - 错误率

   ### 9.3 日志策略

   - 日志级别：INFO
   - 日志输出：RichLogger
   - 关键事件：
     * 任务开始/结束
     * 大模型调用（如适用）
     * 错误与异常

   ---

   ## 10. 下一步工作

   **立即进入**：DevPipelineGeneration 工作流（v2版本）
   - 参考本技术决策文档
   - 参考开发计划文档
   - 参考需求文档
   - 生成最小可执行步骤的任务清单

   **后续工作**：
   1. 任务清单生成（参考所有文档）
   2. 任务执行
   3. 简单功能测试

   ---

   **工作流版本**：2.0 | **生成时间**：{YYYY-MM-DD HH:mm:ss}
   **文档字数**：{字数}（≥ 5000字）
   ```

2. **写入文件**：
   ```
   写入文件：${TECH_PATH}
   编码：UTF-8（无BOM）
   ```

3. **更新进度**：技术决策文档生成完成

**输出文件**：`${TECH_PATH}`

---

### 步骤10：规范对齐验证（质量门控）

*门控：必须在输出文档前通过。最多尝试3轮修正。*

**动作**：
1. **执行验证检查**：

   **检查1：文档完整性**
   - 验证包含所有10个必需章节
   → 如果缺少：FAIL "技术决策文档缺少章节: {章节名}"

   **检查2：依赖定义完整性**
   - 验证每个依赖包含：库名、版本、选型理由、官方文档、配置示例
   - 验证选型理由 ≥ 100字
   → 如果不完整：FAIL "依赖 {依赖名} 定义不完整"

   **检查3：提示词定义完整性**（如适用）
   - 验证每个提示词包含：模板、输入变量、输出格式、错误处理
   - 验证提示词模板 ≥ 200字
   → 如果不完整：FAIL "提示词 {场景名} 定义不完整"

   **检查4：API定义完整性**（如适用）
   - 验证每个端点包含：路由、请求/响应格式、认证要求、测试命令
   → 如果不完整：FAIL "API端点 {端点} 定义不完整"

   **检查5：字段规范完整性**
   - 验证每个模型包含：字段类型、验证规则、示例、Pydantic定义
   → 如果不完整：FAIL "数据模型 {模型名} 定义不完整"

   **检查6：配置文件完整性**
   - 验证 .env 模板包含所有必需配置
   - 验证 config.py 包含 Pydantic 定义
   → 如果不完整：FAIL "配置文件定义不完整"

   **检查7：文档详细度（关键！针对GPT-5）**
   - 验证文档总字数 ≥ 5000字
   - 验证每个依赖选型理由 ≥ 100字
   - 验证每个提示词 ≥ 200字（如适用）
   → 如果不够详细：FAIL "文档不够详细，总字数: {字数}，要求 ≥ 5000字"

2. **处理验证结果**：
   → 如果所有检查通过：
     * 更新进度：质量门控通过
     * 继续步骤11
   → 如果任何检查失败：
     * 修正内容
     * 重新写入
     * 重新验证（最多3轮）
     * 如果3轮后仍失败：ERROR "质量门控验证失败: {详情}"

3. **更新进度**：质量门控验证通过

---

### 步骤11：完成与报告

**动作**：
1. **输出执行摘要**：
   ```markdown
   ## 技术决策文档生成完成

   **输出文件**：{TECH_PATH}
   **编号**：{COUNT_3D}
   **意图标识**：{INTENT_TITLE_2_4}
   **生成时间**：{YYYY-MM-DD HH:mm:ss}
   **文档字数**：{字数}

   **技术统计**：
   - 新增依赖：{数量}
   - 大模型场景：{数量}（如适用）
   - API端点：{数量}（如适用）
   - 数据模型：{数量}
   - 配置项：{数量}

   **下一步**：
   请使用 DevPipelineGeneration 工作流（v2版本）生成任务清单。
   该工作流将参考需求文档、开发计划、技术决策三个文档，
   生成最小可执行步骤的任务清单。
   ```

2. **更新进度**：工作流执行完成

---

## 进度跟踪

**阶段状态**：
- [ ] 步骤1：文档加载完成
- [ ] 步骤2：项目规范加载完成
- [ ] 步骤3：技术选型完成（门控通过）
- [ ] 步骤4：大模型提示词定义完成
- [ ] 步骤5：API对接方案定义完成
- [ ] 步骤6：数据字段规范定义完成
- [ ] 步骤7：配置文件定义完成
- [ ] 步骤8：边界与约束定义完成
- [ ] 步骤9：技术决策文档生成完成
- [ ] 步骤10：质量门控验证通过
- [ ] 步骤11：工作流执行完成

**质量门控状态**：
- [ ] 技术选型门控：通过（步骤3）
- [ ] 文档完整性检查：通过（步骤10）
- [ ] 依赖定义完整性检查：通过（步骤10）
- [ ] 提示词定义完整性检查：通过（步骤10）
- [ ] API定义完整性检查：通过（步骤10）
- [ ] 字段规范完整性检查：通过（步骤10）
- [ ] 配置文件完整性检查：通过（步骤10）
- [ ] 文档详细度检查：通过（步骤10）

---

## 验收标准（Acceptance Criteria）

**输出文件要求**：
- [ ] 文件编码为 UTF-8（无BOM）
- [ ] 文件大小 > 40KB（确保详细）
- [ ] 文档总字数 ≥ 5000字

**依赖定义要求**：
- [ ] 每个依赖包含：库名、版本、选型理由（≥100字）、官方文档、配置示例
- [ ] 所有依赖已验证兼容性（Python版本、asyncio、类型注解）
- [ ] 所有依赖已调研官方文档

**提示词定义要求**（如适用）：
- [ ] 每个提示词 ≥ 200字
- [ ] 包含：模板、输入变量、输出格式、错误处理、批处理策略
- [ ] 包含调用参数和成本估算

**API定义要求**（如适用）：
- [ ] 每个端点包含：路由、请求/响应格式、认证要求、测试命令
- [ ] 包含端口分配方案
- [ ] 包含中间件和CORS配置（如需要）

**字段规范要求**：
- [ ] 每个模型包含：字段类型、验证规则、示例、Pydantic定义
- [ ] 包含字段命名规范
- [ ] 包含数据转换规则（如需要）

**配置文件要求**：
- [ ] 包含完整的 .env 模板
- [ ] 包含完整的 config.py 定义（Pydantic Settings）
- [ ] 包含配置验证规则

**详细度要求**（针对GPT-5）：
- [ ] 文档总体详细且充实（≥ 5000字）
- [ ] 每个技术决策包含详细说明和示例
- [ ] 所有代码示例完整可运行

---

## 错误处理约定

**ERROR 级别**（终止执行）：
- 需求文档或开发计划未找到
- 依赖选型未基于官方文档
- 依赖不兼容项目约束
- 质量门控验证失败（3轮后仍未通过）
- 文档详细度不足（< 5000字）

**WARN 级别**（记录警告但继续）：
- 技术决策文档已存在（可选覆盖）

---

## 规范引用

**项目规范**：
- `CodexFeatured/Common/BackendConstitution.yaml` - 技术栈约束与禁止项
- `CodexFeatured/Common/BestPractise.yaml` - 官方文档索引

**工作流版本**：2.0 | **最后更新**：2025-10-11

---

*基于 SpecKit 工程实践 v2.1.1 - 专注技术实现细节*

