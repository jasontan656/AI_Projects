---
description: 深度调研问答工作流（精简版）- 用更少步骤产出更高信噪比的报告
version: 2.1
language: zh-CN
scripts:
  ps: CodexFeatured/Scripts/get-qa-context.ps1 -Json
---

# DeepResearchQA - 深度调研问答工作流

## 工作流概述

**目标**：识别问题类型，快速产出可验证、可复用的高质量结论型报告。

**原则（7条）**：
- 结论先行；证据随后
- 分析维度按需，不为凑数
- 搜索三段式：基础→深度→验证
- 术语准确，类比辅助
- 图表与代码按需呈现
- 来源可复核，时间有标注
- 最小充分：只保留影响结论的内容

**输入**：$ARGUMENTS（可含背景 + 问题）

**输出**：`D:/AI_Projects/Learning/QA/{COUNT_3D}_{QUESTION_SUMMARY}.md`

---

## 参数

```yaml
OUTPUT_DIR: "D:/AI_Projects/Learning/QA"
USER_QUESTION: "$ARGUMENTS"
COUNT_3D: "{{RUNTIME_RESOLVE}}"
QUESTION_SUMMARY: "{{RUNTIME_RESOLVE}}"
OUTPUT_FILE: "${OUTPUT_DIR}/${COUNT_3D}_${QUESTION_SUMMARY}.md"
```

---

## 执行流程（4步）

### 步骤1｜理解问题

1) 校验输入非空；为空则提示使用 `-a` 传参
2) 提取核心问题与真实意图（可为多问）
3) 判定类型：技术学习｜现状调研｜对比分析｜建议咨询｜故障排查｜趋势预测｜决策支持｜开放探讨
4) 标注领域（技术/国家地区/行业/生活 等）与核心关键词
5) 生成摘要（10-30 字，PascalCase/下划线），示例："WhatIsCelery"、"PhilippinesCurrentSituation"
6) 通过 `CodexFeatured/Scripts/get-qa-context.ps1` 生成 `COUNT_3D`

输出：原始输入｜核心问题｜类型｜领域｜关键词｜摘要｜编号

---

### 步骤2｜选择分析框架并调研

依据类型选择框架；用“速览矩阵”替代冗长细节，深度信息按需展开。

分析框架速览：

| 类型 | 识别特征 | 关键维度 | 产出要点 |
|------|---------|---------|---------|
| 技术学习 | “什么是/如何用” | What/How/Why/Best Practices | 入门示例+配置要点+常见坑 |
| 现状调研 | 国家/行业“现状” | 基本面/指标/风险/展望 | 指标卡+总评+是否合适 |
| 对比分析 | A vs B | 矩阵/核心差异/迁移 | 选择建议+取舍依据 |
| 建议咨询 | “如何/建议” | 目标/路径/步骤/评估 | 可执行清单+时间预算 |
| 故障排查 | “为什么/错误” | 现象/原因概率/诊断/修复 | 排障SOP+预防措施 |
| 趋势预测 | “未来/趋势” | 历史/驱动/场景/不确定性 | 时间线+情景推演 |

补充维度（按需）：生态/版本/性能/成本/监管/用户声音

#### 维度1：核心概念解释（What）

**目标**：用最通俗的语言解释这是什么

**分析内容**：

1. **一句话定义**：
   ```
   用一句话（不超过50字）说清楚这是什么
   
   示例：
   "Celery是一个Python分布式任务队列框架，用于异步执行耗时任务。"
   "菲律宾文化融入是指了解并适应菲律宾的社会习俗、价值观和生活方式。"
   ```

2. **通俗解释**（关键！）：
   ```
   用生活场景比喻，让完全不懂的人也能理解
   
   示例（Celery）：
   "想象你是一家餐厅老板。顾客点单后，如果你让服务员现场做菜，
   顾客就得等很久。但如果你让服务员把订单传给后厨，后厨慢慢做，
   服务员可以继续接待下一位顾客，这就是Celery的核心思想：
   把耗时的工作交给'后厨'（Worker），主程序（服务员）继续干其他事。"
   
   示例（菲律宾文化）：
   "就像你去朋友家做客，你需要先观察他们家的规矩（脱鞋吗？帮忙洗碗吗？），
   然后慢慢适应，最后成为'自己人'。融入菲律宾文化也是这样：
   先观察、再模仿、最后内化。"
   ```

3. **核心要素**：
   ```
   列出核心组成部分（3-5个）
   
   示例（Celery）：
   1. Task（任务）：要执行的工作
   2. Worker（工人）：实际执行任务的进程
   3. Broker（中间人）：传递任务的消息队列（Redis/RabbitMQ）
   4. Result Backend（结果存储）：存储任务结果的地方
   5. Beat（定时器）：定时触发任务的调度器
   ```

4. **技术术语保留**：
   ```
   在通俗解释后，明确列出标准技术术语
   
   示例：
   "上面说的'后厨'，技术上叫做 Worker（工作进程）
   '订单传递'，技术上叫做 Message Broker（消息代理）
   '订单'本身，技术上叫做 Task（任务）"
   ```

---

#### 维度2：工作原理（How）

**目标**：深入解释它是如何运作的

**分析内容**：

1. **核心工作流程**（关键！）：
   ```
   用流程图或步骤列表展示完整流程
   
   示例（Celery）：
   
   1. 用户请求 → FastAPI接收
   2. FastAPI调用 celery_task.delay() → 任务创建
   3. 任务序列化 → 发送到Broker（Redis/RabbitMQ）
   4. Broker存储任务 → 等待Worker获取
   5. Worker从Broker拉取任务 → 开始执行
   6. Worker执行完成 → 结果存储到Result Backend
   7. 用户查询结果 → 从Result Backend读取
   
   关键点：
   - 步骤2和3是非阻塞的（FastAPI立即返回）
   - 步骤5-6是异步的（在后台执行）
   - 步骤7是按需的（用户需要时才查询）
   ```

2. **内部机制**：
   ```
   解释关键的内部实现细节
   
   示例（Celery）：
   - 任务序列化：使用pickle或JSON将Python对象转为字节流
   - 消息传递：使用AMQP协议（RabbitMQ）或Redis协议
   - Worker轮询：Worker每隔一定时间向Broker请求新任务
   - 结果存储：使用Redis、MongoDB或数据库存储任务结果
   - 并发模型：支持多进程（prefork）、多线程、协程（gevent）
   ```

3. **数据流图**：
   ```
   画出数据如何在各个组件之间流动
   
   示例（Celery）：
   
   用户 → FastAPI → Celery Client → Broker → Worker → Result Backend
          ↑                                              ↓
          └─────────── 查询结果 ─────────────────────────┘
   ```

4. **生命周期**：
   ```
   描述从创建到销毁的完整生命周期
   
   示例（Celery任务）：
   1. PENDING（等待）：任务刚创建，还没被Worker获取
   2. STARTED（开始）：Worker已获取，正在执行
   3. RETRY（重试）：执行失败，正在重试
   4. SUCCESS（成功）：执行成功，结果已存储
   5. FAILURE（失败）：执行失败，错误已记录
   ```

---

#### 维度3：解决什么问题（Why）

**目标**：说明为什么需要它，它解决了什么痛点

**分析内容**：

1. **核心问题**：
   ```
   列出3-5个核心痛点
   
   示例（Celery）：
   1. Web请求超时：用户上传大文件，处理需要5分钟，HTTP会超时
   2. 服务器资源占用：大量耗时任务阻塞主进程，无法处理新请求
   3. 定时任务需求：需要每天凌晨执行数据备份
   4. 任务失败重试：网络不稳定导致任务失败，需要自动重试
   5. 分布式执行：单机处理不过来，需要多台机器协同工作
   ```

2. **传统方案的问题**：
   ```
   如果不用这个技术，传统方案有什么问题？
   
   示例（Celery）：
   
   传统方案1：同步执行
   问题：用户等待时间长，体验差；服务器资源被占用，并发能力低
   
   传统方案2：多线程
   问题：Python GIL限制，多线程无法充分利用多核；内存占用高
   
   传统方案3：定时任务（cron）
   问题：无法动态调度；失败后不会自动重试；无法查看执行状态
   ```

3. **技术价值**：
   ```
   这个技术带来了什么价值？
   
   示例（Celery）：
   1. 用户体验：请求立即返回，后台慢慢处理
   2. 系统性能：主进程不被阻塞，可以处理更多请求
   3. 可扩展性：可以增加更多Worker来提升处理能力
   4. 可靠性：自动重试、结果持久化、任务监控
   5. 灵活性：支持定时任务、优先级、任务链等高级功能
   ```

4. **实际案例**：
   ```
   列举3-5个真实使用场景
   
   示例（Celery）：
   1. 电商网站：用户下单后，异步发送邮件通知、更新库存、生成发票
   2. 视频网站：用户上传视频后，异步转码、生成缩略图、提取字幕
   3. 数据分析：定时爬取数据、清洗处理、生成报告
   4. 社交平台：用户发帖后，异步推送通知、更新推荐算法
   5. 金融系统：定时计算利息、生成对账单、风控检查
   ```

---

#### 维度4：正确使用方式（How to Use）

**目标**：教用户如何正确使用

**分析内容**：

1. **基础使用**（必需）：
   ```
   提供完整的入门示例（可直接运行）
   
   示例（Celery）：
   
   # 1. 安装
   pip install celery redis
   
   # 2. 创建任务文件 tasks.py
   from celery import Celery
   
   app = Celery('tasks', broker='redis://localhost:6379/0')
   
   @app.task
   def add(x, y):
       return x + y
   
   # 3. 启动Worker
   celery -A tasks worker --loglevel=info
   
   # 4. 调用任务（在另一个Python脚本中）
   from tasks import add
   result = add.delay(4, 6)
   print(result.get())  # 输出：10
   ```

2. **完整配置**（推荐）：
   ```
   提供生产级配置示例
   
   示例（Celery）：
   
   # celeryconfig.py
   
   # Broker设置
   broker_url = 'redis://localhost:6379/0'
   result_backend = 'redis://localhost:6379/1'
   
   # 序列化
   task_serializer = 'json'
   result_serializer = 'json'
   accept_content = ['json']
   
   # 时区
   timezone = 'Asia/Shanghai'
   enable_utc = True
   
   # 任务配置
   task_track_started = True  # 追踪任务开始
   task_time_limit = 30 * 60  # 任务超时时间（30分钟）
   task_soft_time_limit = 25 * 60  # 软超时（25分钟）
   
   # 重试配置
   task_acks_late = True  # 任务完成后才确认
   task_reject_on_worker_lost = True  # Worker丢失时拒绝任务
   
   # Worker配置
   worker_prefetch_multiplier = 4  # 预取任务数量
   worker_max_tasks_per_child = 1000  # 每个Worker最多执行1000个任务后重启
   ```

3. **常见用法**（重要）：
   ```
   列出5-10个常用场景的代码示例
   
   示例（Celery）：
   
   用法1：异步任务
   @app.task
   def send_email(to, subject, body):
       # 发送邮件的代码
       pass
   
   # 调用
   send_email.delay('user@example.com', 'Hello', 'World')
   
   用法2：定时任务
   from celery.schedules import crontab
   
   app.conf.beat_schedule = {
       'backup-every-night': {
           'task': 'tasks.backup_database',
           'schedule': crontab(hour=2, minute=0),
       },
   }
   
   用法3：任务链（一个任务完成后执行下一个）
   from celery import chain
   
   result = chain(task1.s(arg1), task2.s(), task3.s()).apply_async()
   
   用法4：任务组（并行执行多个任务）
   from celery import group
   
   job = group(task1.s(1), task2.s(2), task3.s(3))
   result = job.apply_async()
   
   用法5：获取任务结果
   result = task.delay(arg)
   if result.ready():  # 任务是否完成
       print(result.get())  # 获取结果
   else:
       print(result.state)  # 获取当前状态
   ```

4. **最佳实践**（关键！）：
   ```
   列出5-10个业界公认的最佳实践
   
   示例（Celery）：
   1. 任务要幂等：同一个任务执行多次，结果应该一致
   2. 避免在任务中使用数据库连接：每次任务都重新创建连接
   3. 合理设置超时时间：防止任务卡死
   4. 使用任务重试：处理临时性错误（如网络抖动）
   5. 不要在任务中执行长时间I/O：会阻塞Worker
   6. 监控任务队列长度：防止任务堆积
   7. 使用不同的队列：区分优先级（重要任务、普通任务）
   8. 定期重启Worker：防止内存泄漏
   9. 记录详细日志：方便调试和监控
   10. 测试任务逻辑：确保任务代码健壮
   ```

5. **常见陷阱**（重要）：
   ```
   列出5-8个常见错误和解决方案
   
   示例（Celery）：
   
   陷阱1：忘记启动Worker
   现象：任务一直PENDING状态
   解决：celery -A tasks worker --loglevel=info
   
   陷阱2：任务参数无法序列化
   现象：报错 "Object of type X is not JSON serializable"
   解决：只传递简单类型（int, str, list, dict），不要传递复杂对象
   
   陷阱3：Broker连接失败
   现象：报错 "Error while trying to connect to redis"
   解决：检查Redis是否启动，连接字符串是否正确
   
   陷阱4：任务超时
   现象：任务执行到一半被杀死
   解决：增加task_time_limit配置
   
   陷阱5：任务重复执行
   现象：同一个任务执行了多次
   解决：设置task_acks_late=True，确保任务完成后才确认
   ```

---

#### 维度5：相关技术生态（Ecosystem）

**目标**：自动关联相关技术，形成完整知识图谱

**分析内容**：

1. **必需的相关技术**（业界最佳组合）：
   ```
   列出必须配合使用的技术（3-5个）
   
   示例（Celery）：
   
   技术1：Redis（Broker + Result Backend）
   - 作用：存储任务队列和结果
   - 为什么：性能高、配置简单、支持持久化
   - 关系：Celery的大脑，存储所有任务信息
   
   技术2：RabbitMQ（Broker，企业级）
   - 作用：更可靠的消息队列
   - 为什么：支持消息确认、死信队列、集群
   - 关系：Celery的高级Broker选项
   
   技术3：FastAPI / Django（Web框架）
   - 作用：接收用户请求，触发Celery任务
   - 为什么：主应用程序，Celery是它的后台助手
   - 关系：Celery的老板，分配任务
   
   技术4：Flower（监控工具）
   - 作用：可视化监控Celery任务
   - 为什么：实时查看任务状态、Worker状态
   - 关系：Celery的仪表盘
   ```

2. **技术栈组合**：
   ```
   展示完整的技术栈架构
   
   示例（Celery完整技术栈）：
   
   前端：Vue.js / React
      ↓ HTTP请求
   后端：FastAPI / Django
      ↓ 触发任务
   任务队列：Celery
      ↓ 任务存储
   消息队列：Redis / RabbitMQ
      ↓ 任务分发
   Worker：Celery Worker（多个）
      ↓ 结果存储
   结果存储：Redis / MongoDB
      ↓ 监控
   监控：Flower / Prometheus
   ```

3. **对比其他方案**（重要）：
   ```
   列出2-3个竞品或替代方案
   
   示例（Celery vs 其他）：
   
   方案1：Celery vs RQ（Redis Queue）
   - RQ优势：更简单、纯Python、易学习
   - Celery优势：功能更强、支持多种Broker、企业级
   - 选择建议：小项目用RQ，大项目用Celery
   
   方案2：Celery vs Kafka + Consumer
   - Kafka优势：更高吞吐量、日志式存储、分布式
   - Celery优势：更简单、Python生态、任务管理
   - 选择建议：大数据流处理用Kafka，任务队列用Celery
   
   方案3：Celery vs 云服务（AWS Lambda / Azure Functions）
   - 云服务优势：无需管理基础设施、自动扩展
   - Celery优势：自主控制、成本更低、无供应商锁定
   - 选择建议：无状态短任务用云服务，复杂任务用Celery
   ```

4. **版本兼容性**：
   ```
   说明版本依赖和兼容性
   
   示例（Celery）：
   - Celery 5.x：Python 3.6+，推荐3.8+
   - Redis 5.x+：推荐6.x
   - RabbitMQ 3.8+：推荐3.10+
   - 注意：Celery 5.x不兼容Celery 4.x的配置
   ```

---

#### 维度6：新奇玩法和高级技巧（Advanced）

**目标**：展示创意用法和高级技巧

**分析内容**：

1. **创意用法**（3-5个）：
   ```
   展示一些非常规但有效的用法
   
   示例（Celery）：
   
   玩法1：动态创建任务
   @app.task(bind=True)
   def dynamic_task(self, func_code, *args):
       exec(func_code)  # 动态执行代码（注意安全）
   
   玩法2：任务作为Actor（有状态任务）
   @app.task(bind=True, base=Task)
   class Counter(Task):
       def __init__(self):
           self.count = 0
       
       def run(self, increment):
           self.count += increment
           return self.count
   
   玩法3：任务链式调用（Pipeline）
   from celery import chain
   
   # 任务1的输出自动作为任务2的输入
   pipeline = chain(
       fetch_data.s(),
       process_data.s(),
       save_result.s()
   ).apply_async()
   
   玩法4：任务作为Webhook回调
   @app.task
   def webhook_callback(url, data):
       requests.post(url, json=data)
   
   # 任务完成后自动调用Webhook
   task.apply_async(link=webhook_callback.s('http://callback.url'))
   ```

2. **性能优化技巧**（5-8个）：
   ```
   列出性能优化的高级技巧
   
   示例（Celery）：
   1. 使用消息压缩：减少网络传输
      task_compression = 'gzip'
   
   2. 批量任务：减少Broker开销
      @app.task
      def batch_process(items):
          for item in items:
              process(item)
   
   3. 任务预热：避免冷启动
      worker启动时自动加载常用模块
   
   4. 使用gevent：提升I/O密集型任务性能
      celery -A tasks worker --pool=gevent --concurrency=1000
   
   5. 任务结果过期：避免Result Backend膨胀
      task_ignore_result = True  # 不需要结果的任务
      result_expires = 3600  # 结果1小时后过期
   
   6. 使用优先级队列：重要任务优先
      from kombu import Queue
      task_queues = (
          Queue('high', routing_key='high'),
          Queue('normal', routing_key='normal'),
          Queue('low', routing_key='low'),
      )
   
   7. Worker进程池：充分利用多核
      worker_pool = 'prefork'  # 多进程
      worker_concurrency = 8  # 8个进程
   
   8. 任务路由：不同任务分配到不同Worker
      task_routes = {
          'tasks.heavy_task': {'queue': 'heavy'},
          'tasks.light_task': {'queue': 'light'},
      }
   ```

3. **高级模式**（3-5个）：
   ```
   展示设计模式和架构模式
   
   示例（Celery）：
   
   模式1：任务分片（Map-Reduce）
   from celery import group
   
   # 将大任务分片处理
   def process_large_dataset(data):
       chunks = split_data(data, chunk_size=1000)
       job = group(process_chunk.s(chunk) for chunk in chunks)
       results = job.apply_async()
       return merge_results(results.get())
   
   模式2：任务重试策略（指数退避）
   @app.task(bind=True, max_retries=5)
   def retry_task(self, url):
       try:
           return requests.get(url)
       except requests.RequestException as exc:
           raise self.retry(exc=exc, countdown=2 ** self.request.retries)
   
   模式3：任务依赖图（DAG）
   from celery import chord
   
   # 任务A和B并行执行，完成后执行任务C
   callback = aggregate_results.s()
   header = [task_a.s(), task_b.s()]
   result = chord(header)(callback)
   
   模式4：任务幂等性保证
   @app.task
   def idempotent_task(user_id, action):
       key = f"task:{user_id}:{action}"
       if redis.exists(key):
           return "Already processed"
       
       # 执行任务
       result = do_work(user_id, action)
       
       # 标记已处理
       redis.set(key, 1, ex=3600)
       return result
   ```

4. **调试技巧**（3-5个）：
   ```
   展示调试和排查问题的技巧
   
   示例（Celery）：
   1. 实时查看任务执行：flower -A tasks --port=5555
   2. 查看Worker日志：celery -A tasks worker --loglevel=debug
   3. 手动重试失败任务：result = task.retry(task_id='xxx')
   4. 查看任务状态：from celery.result import AsyncResult; AsyncResult('task_id').state
   5. 清空队列：celery -A tasks purge
   ```

---

#### 维度7：用户评价和实践经验（User Experience）

**目标**：收集真实用户的使用经验和评价

**分析内容**：

1. **网络搜索用户评价**（关键！）：
   ```
   使用web_search工具搜索：
   - "{技术名} 使用经验"
   - "{技术名} 踩坑"
   - "{技术名} best practices"
   - "{技术名} reddit"
   - "{技术名} stackoverflow"
   
   提取关键信息：
   - 用户普遍认为的优点
   - 用户普遍遇到的问题
   - 用户推荐的替代方案
   - 用户分享的经验教训
   ```

2. **整理用户反馈**：
   ```
   分类整理用户评价：
   
   示例（Celery）：
   
   优点（用户普遍认可）：
   - "Celery非常稳定，我们用了5年没出过大问题" - Reddit用户
   - "文档详细，社区活跃，遇到问题很容易找到答案" - StackOverflow
   - "与Django集成非常方便" - 知乎用户
   
   缺点（用户普遍吐槽）：
   - "配置复杂，初学者容易迷失" - Medium文章
   - "版本升级有坑，4.x到5.x改动很大" - GitHub Issue
   - "监控不够直观，需要额外安装Flower" - 博客文章
   
   常见问题（用户经常问）：
   - "为什么任务一直PENDING？" - StackOverflow高频问题
   - "如何避免任务重复执行？" - Reddit讨论
   - "Worker内存泄漏怎么办？" - GitHub Issue
   ```

3. **实际案例分享**：
   ```
   收集真实项目的使用案例
   
   示例（Celery）：
   
   案例1：Instagram（技术博客）
   - 规模：每秒处理数百万任务
   - 用途：图片处理、推送通知、数据分析
   - 经验：使用RabbitMQ而非Redis，更可靠
   
   案例2：Mozilla（开源项目）
   - 规模：中等规模
   - 用途：Firefox测试、构建任务
   - 经验：使用任务链处理复杂工作流
   
   案例3：个人项目（博客文章）
   - 规模：小规模
   - 用途：爬虫、邮件发送
   - 经验：Redis足够用，RabbitMQ太重
   ```

4. **专家建议**：
   ```
   引用行业专家的观点
   
   示例（Celery）：
   - "Celery适合Python生态，但如果你的项目不止Python，
      考虑Kafka或AWS SQS" - 某云架构师
   - "小项目用RQ，大项目用Celery，超大规模考虑自研" - 某CTO
   - "Celery的最大优势是Python生态和简单易用，
      最大劣势是性能比不上Go或Rust实现的队列" - 某性能工程师
   ```

---

#### 维度8：学习路径和资源（Learning Path）

**目标**：提供完整的学习路径和资源

**分析内容**：

1. **学习路径**（分阶段）：
   ```
   设计3-4个学习阶段
   
   示例（Celery）：
   
   阶段1：入门（1-2天）
   - 目标：理解Celery基本概念，运行第一个任务
   - 学习内容：
     * Celery是什么？解决什么问题？
     * 安装和配置
     * 创建第一个任务
     * 启动Worker
   - 实践项目：发送邮件任务
   
   阶段2：进阶（1周）
   - 目标：掌握常用功能，能在实际项目中使用
   - 学习内容：
     * 任务配置和最佳实践
     * 定时任务（Beat）
     * 任务重试和错误处理
     * 监控（Flower）
   - 实践项目：异步图片处理服务
   
   阶段3：高级（2-4周）
   - 目标：优化性能，处理复杂场景
   - 学习内容：
     * 任务路由和优先级
     * 任务链、组、和弦
     * 性能优化
     * 分布式部署
   - 实践项目：分布式爬虫系统
   
   阶段4：精通（持续）
   - 目标：深入源码，贡献社区
   - 学习内容：
     * Celery源码阅读
     * 自定义Task类
     * 扩展Celery
     * 贡献开源
   - 实践项目：基于Celery的企业级任务调度系统
   ```

2. **推荐资源**：
   ```
   列出5-10个优质学习资源
   
   示例（Celery）：
   
   官方资源：
   1. 官方文档：https://docs.celeryproject.org/
   2. 官方教程：https://docs.celeryproject.org/en/stable/getting-started/
   
   书籍：
   3. 《Celery分布式任务队列》（Mastering Celery）
   
   在线课程：
   4. Udemy: "Celery - The Complete Guide"
   5. YouTube: "Celery Tutorial for Beginners"
   
   博客文章：
   6. Real Python: "Asynchronous Tasks with Django and Celery"
   7. Medium: "Celery Best Practices"
   
   开源项目：
   8. Django + Celery示例：https://github.com/xxx/django-celery-example
   9. FastAPI + Celery示例：https://github.com/xxx/fastapi-celery
   
   社区：
   10. Reddit: r/celery
   11. StackOverflow: celery标签
   ```

3. **练习项目**（5-8个）：
   ```
   从易到难的练习项目
   
   示例（Celery）：
   1. Hello World任务：创建最简单的异步任务
   2. 邮件发送服务：批量发送邮件
   3. 图片处理服务：上传图片后异步生成缩略图
   4. 定时数据备份：每天凌晨自动备份数据库
   5. 分布式爬虫：多台机器协同爬取网站
   6. 视频转码服务：上传视频后异步转码
   7. 数据ETL流水线：定时抓取、清洗、存储数据
   8. 实时通知系统：用户行为触发异步推送通知
   ```

4. **常见FAQ**（10-15个）：
   ```
   整理最常见的问题和答案
   
   示例（Celery）：
   Q1: Celery和Cron有什么区别？
   A: Cron是定时任务，Celery支持定时+异步+分布式
   
   Q2: Celery必须用Redis吗？
   A: 不是，也可以用RabbitMQ、Amazon SQS等
   
   Q3: Celery适合实时任务吗？
   A: 不太适合，有一定延迟（秒级），实时任务用WebSocket
   
   Q4: Celery任务可以传递大对象吗？
   A: 不建议，应该传递ID，Worker从数据库读取对象
   
   Q5: 如何确保任务不重复执行？
   A: 使用幂等性设计 + task_acks_late配置
   
   ...（继续10-15个）
   ```

---

## 分析框架2：现状调研（用于国家/地区/行业现状问题）

**适用于**："菲律宾现状怎么样？"、"AI行业发展现状？"、"东南亚经济情况？"

**分析维度**（动态，根据问题调整）：

### 针对国家/地区现状：

1. **基本概况**：地理位置、人口、面积、气候、主要城市
2. **政治现状**：政体、政局稳定性、主要政策、对外关系
3. **经济现状**：GDP、主要产业、经济增长率、失业率、通胀率
4. **社会现状**：人民生活水平、贫富差距、教育、医疗、治安
5. **文化现状**：语言、宗教、习俗、节日、饮食
6. **基础设施**：交通、网络、水电、公共服务
7. **对外贸易和投资**：主要贸易伙伴、外资情况、旅游业
8. **未来展望**：发展趋势、机遇、挑战

### 针对行业现状：

1. **行业规模**：市场规模、增长率、主要玩家
2. **技术现状**：主流技术、新兴技术、技术趋势
3. **竞争格局**：头部企业、市场份额、竞争态势
4. **商业模式**：主流商业模式、盈利方式
5. **政策环境**：相关政策、监管要求
6. **用户需求**：目标用户、核心需求、痛点
7. **投资热度**：融资情况、投资趋势
8. **未来趋势**：发展方向、机遇、挑战

**网络搜索策略**（关键！）：
```
搜索1："{主体} 2024 现状"
搜索2："{主体} 最新新闻"
搜索3："{主体} 经济 GDP 统计数据"
搜索4："{主体} 政治 政局"
搜索5："{主体} 生活 治安 旅游"
搜索6："{主体} reddit 经验分享"
搜索7："{主体} 优缺点 问题"
搜索8-10：根据初步搜索结果，针对性深入搜索
```

---

## 分析框架3：对比分析（用于对比选择问题）

**适用于**："Redis vs Memcached？"、"菲律宾vs泰国移居？"、"Vue vs React？"

**分析维度**：

1. **对比矩阵**：多维度对比表格（15-20个维度）
2. **核心差异**：最重要的3-5个差异点
3. **适用场景**：A适合什么场景，B适合什么场景
4. **优缺点分析**：各自的优势和劣势
5. **性能对比**：量化指标对比（如果适用）
6. **成本对比**：价格、学习成本、维护成本
7. **社区生态**：社区活跃度、文档质量、第三方库
8. **用户评价对比**：用户更偏爱哪个，为什么
9. **选择建议**：什么情况下选A，什么情况下选B
10. **迁移成本**：从A迁移到B的难度

**网络搜索策略**：
```
搜索1："{A} vs {B}"
搜索2："{A} vs {B} reddit"
搜索3："{A} vs {B} 2024"
搜索4："{A} 优缺点"
搜索5："{B} 优缺点"
搜索6："{A} vs {B} benchmark"（如果是技术对比）
搜索7："{A} vs {B} 选择建议"
```

---

## 分析框架4：建议咨询（用于"如何"问题）

**适用于**："如何融入当地文化？"、"如何学习编程？"、"如何提升效率？"

**分析维度**：

1. **问题分析**：为什么需要这个，核心痛点是什么
2. **目标设定**：理想状态是什么样的
3. **现状差距**：现状与目标的差距
4. **解决方案**（多个，分优先级）：
   - 方案1：快速见效方案
   - 方案2：长期持续方案
   - 方案3：资源丰富方案
   - 方案4：资源有限方案
5. **具体步骤**：每个方案的详细执行步骤（1-2-3...）
6. **常见陷阱**：容易犯的错误，如何避免
7. **资源推荐**：书籍、课程、工具、社区
8. **成功案例**：他人的成功经验
9. **时间规划**：预计需要多长时间
10. **评估标准**：如何知道自己做得好不好

**网络搜索策略**：
```
搜索1："如何 {目标}"
搜索2："{目标} 步骤 方法"
搜索3："{目标} 经验分享"
搜索4："{目标} 常见错误"
搜索5："{目标} reddit 建议"
搜索6："{目标} 成功案例"
```

---

## 分析框架5：故障排查（用于"为什么"问题）

**适用于**："为什么Celery任务不执行？"、"为什么网站很慢？"

**分析维度**：

1. **问题描述**：重新梳理问题现象
2. **可能原因**（列举5-10个）：
   - 原因1（概率60%）：{描述}
   - 原因2（概率30%）：{描述}
   - ...
3. **诊断方法**：如何确定是哪个原因
4. **解决方案**：针对每个原因的解决方法
5. **预防措施**：如何避免再次发生
6. **相关案例**：网上类似问题的解决经验

**网络搜索策略**：
```
搜索1："{错误现象} 原因"
搜索2："{错误现象} stackoverflow"
搜索3："{错误现象} 解决方法"
搜索4："{技术} 常见问题"
```

---

## 分析框架6：趋势预测（用于"未来"问题）

**适用于**："AI未来发展趋势？"、"远程工作未来如何？"

**分析维度**：

1. **历史回顾**：过去5-10年的发展历程
2. **现状分析**：当前的发展阶段
3. **驱动因素**：推动发展的核心因素
4. **未来趋势**（3-5个）：
   - 趋势1（短期，1-2年）
   - 趋势2（中期，3-5年）
   - 趋势3（长期，5-10年）
5. **机遇与挑战**：带来的机会和面临的挑战
6. **专家观点**：行业专家的预测
7. **不确定性**：可能的变数

**网络搜索策略**：
```
搜索1："{主题} 未来趋势 2024"
搜索2："{主题} 预测 专家观点"
搜索3："{主题} 发展报告"
搜索4："{主题} 趋势 reddit"
```

---

### 步骤3｜网络搜索（三段式）

1) 基础：关键词 + 年份/现状/社区（reddit/知乎）
2) 深度：框架维度定向检索与数据源（报告、统计、论文）
3) 验证：多源交叉、冲突标注、时间有效性标注

---

### 步骤4｜生成报告

使用统一精简模板（随框架按需增删小节）：

```markdown
# {问题标题}

问题：{原始输入}
核心问题：{提取}
类型/框架：{类型｜框架名}
生成时间：{YYYY-MM-DD HH:mm:ss}
文件编号：{COUNT_3D}
版本：2.1

---

## 结论先行
- 一句话：{≤100字}
- 关键要点：{3-5条}

## 证据与分析（按需）
- 维度A：{要点 + 证据链接/数据}
- 维度B：{要点 + 证据链接/数据}

## 行动/选择建议（如适用）
- 建议：{可执行清单}
- 评估：{成功标准/时间预算}

## 参考与数据来源（分组）
- 官方/文档：
- 新闻/报告：
- 社区/经验：
- 数据/统计：

---
（编号）{COUNT_3D}｜（生成）{YYYY-MM-DD HH:mm:ss}｜（信息截止）{搜索日期}
```

格式要求：目录内链、术语准确、代码高亮按需、来源含可点击链接。

写入：`${OUTPUT_FILE}`（UTF-8 无BOM）

---

## 进度跟踪

**阶段状态**：
- [ ] 步骤1：问题理解
- [ ] 步骤2：框架选择与调研
- [ ] 步骤3：网络搜索（验证完成）
- [ ] 步骤4：报告生成

---

## 验收标准

**输入**：
- [ ] 通过 `-a` 提供清晰问题（可含背景）

**输出文件**：
- [ ] 写入 `${OUTPUT_FILE}`，UTF-8（无BOM）

**内容质量**（以质为先）：
- [ ] 结论先行 + 关键要点（3-5条）
- [ ] 维度按需覆盖，能支撑结论即可
- [ ] 来源真实可点开（≥10条，视题型可调）
- [ ] 关键信息跨源验证，矛盾处已标注
- [ ] 时间敏感信息标注日期/版本
- [ ] 技术术语准确，必要处给通俗解释

**搜索要求**：
- [ ] 基础/深度/验证三段式执行完备

---

## 错误处理

**ERROR 级别**（终止执行）：
- 用户未提供问题（$ARGUMENTS 为空）

**WARN 级别**（记录警告但继续）：
- 网络搜索失败（使用通用知识补充）
- 找不到特定资源（标注"需自行搜索"）

---

## 使用示例

### 示例1：技术学习

```bash
codex -p .codex/prompts/DeepAnswers.md -a "什么是Celery？如何与Redis配合使用？"
# 输出：Learning/QA/001_WhatIsCelery.md（结论先行 + 入门示例 + 常见坑）
```

### 示例2：对比分析

```bash
codex -p .codex/prompts/DeepAnswers.md -a "Redis vs Memcached？"
# 输出：Learning/QA/002_RedisVsMemcached.md（对比矩阵 + 选择建议）
```

### 示例5：复杂问题（包含背景）

```bash
codex -p .codex/prompts/DeepResearchQA_V2.md -a "我在做一个项目，需要处理大量异步任务。有人推荐Celery，也有人推荐RQ。我的项目是Python后端，用FastAPI，数据库是PostgreSQL，预计每天处理10万个任务。请问：1) Celery适合我的场景吗？2) 和Redis、RabbitMQ是什么关系？3) 有什么坑需要注意？4) 如何部署？"

# AI执行：
# 1. 智能提取：
#    - 背景：Python后端、FastAPI、PostgreSQL、10万任务/天
#    - 核心问题：Celery是否适合、技术关系、注意事项、部署方法
# 2. 识别问题类型：技术学习 + 决策支持
# 3. 选择分析框架：混合（技术学习 + 针对性建议）
# 4. 网络搜索12-18次
# 5. 生成报告

# 输出：Learning/QA/005_CeleryForAsyncTasks.md
# 内容：
# - 结论先行（是否适合 + 核心建议）
# - 针对用户场景的分析（10万任务/天，Celery完全够用）
# - Celery详细介绍（8维分析）
# - 与Redis、RabbitMQ的关系（详细解释）
# - 针对用户场景的最佳实践
# - 部署方案（Docker、K8s、云服务）
# - 常见问题和解决方案
# - 参考资源
# ...约3000-4000行
```

---

## 工作流版本

**版本**：2.1 | **最后更新**：2025-10-12

---

*通用深度调研工作流 - 更少废话，更强结论*

