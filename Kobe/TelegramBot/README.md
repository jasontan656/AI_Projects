# Telegram Bot 模块

Telegram 机器人集成模块，提供实时消息处理、智能对话和群组监控能力。

## 功能特性

- **Webhook 实时模式**：0 延迟消息接收（不支持 Long Polling）
- **智能对话**：集成 LangChain + OpenAI，支持上下文记忆
- **私聊自动回复**：所有私聊消息自动回复
- **群组智能回复**：
  - 被 @ 提及时：立即回复（0延迟）
  - 未被 @ 时：15秒防抖机制（聚合多条消息）
- **速率限制**：基于 Redis 的防滥用机制
- **临时上下文**：Redis 存储最近对话（重启清空）

## 快速开始

### 1. 创建 Telegram Bot

1. 在 Telegram 中找到 [@BotFather](https://t.me/botfather)
2. 发送 `/newbot` 创建新机器人
3. 记录机器人的 Token（格式：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）

### 2. 配置环境变量

编辑 `Kobe/.env`，添加以下配置：

```bash
# Telegram Bot Token（必需）
TELEGRAM_BOT_TOKEN=你的机器人token

# Webhook URL（ngrok 提供的公网地址）
TELEGRAM_WEBHOOK_URL=https://your-domain.ngrok-free.app

# 可选：Webhook 密钥
TELEGRAM_WEBHOOK_SECRET=your-secret-key

# 群组消息处理
TELEGRAM_GROUP_DEBOUNCE_SECONDS=15

# 速率限制
TELEGRAM_USER_RATE_LIMIT=10
TELEGRAM_GROUP_RATE_LIMIT=20
```

### 3. 启动服务

#### 步骤 1：启动 FastAPI

```bash
cd D:\AI_Projects\Kobe
python app.py
```

#### 步骤 2：启动 ngrok

在另一个终端：

```bash
ngrok http 8000
```

记下 ngrok 提供的 HTTPS 地址，例如：`https://abc123.ngrok-free.app`

#### 步骤 3：更新 .env

将 ngrok 地址填入 `.env`：

```bash
TELEGRAM_WEBHOOK_URL=https://abc123.ngrok-free.app
```

#### 步骤 4：设置 Webhook

使用 curl 或浏览器访问：

```bash
curl -X POST http://localhost:8000/telegram/setup-webhook
```

或直接访问：http://localhost:8000/docs，找到 `/telegram/setup-webhook` 接口并执行。

### 4. 测试机器人

1. **私聊测试**：在 Telegram 中找到你的机器人，发送任意消息
2. **群组测试**：
   - 将机器人添加到群组
   - @机器人 发送消息
   - 或发送包含关键词的消息（如"帮助"）

## API 端点

### POST /telegram/webhook

接收 Telegram 更新的主要端点。

- **由 Telegram 服务器调用**
- 自动验证 Secret Token（如果配置）
- 异步处理消息，立即返回 200 OK

### POST /telegram/setup-webhook

设置 Webhook URL。

**响应示例**：
```json
{
  "ok": true,
  "message": "Webhook 设置成功",
  "webhook_url": "https://your-domain.ngrok-free.app"
}
```

### POST /telegram/delete-webhook

删除 Webhook（用于清理或切换模式）。

### GET /telegram/status

获取机器人状态和配置信息。

**响应示例**：
```json
{
  "ok": true,
  "bot": {
    "id": 123456789,
    "username": "your_bot",
    "first_name": "Your Bot Name"
  },
  "config": {
    "webhook_url": "https://your-domain.ngrok-free.app",
    "group_monitoring": true,
    "reply_to_mentions": true,
    "keywords": ["帮助", "help"]
  }
}
```

## 架构设计

```
┌─────────────┐
│  Telegram   │
│   Server    │
└──────┬──────┘
       │ HTTPS Webhook
       ↓
┌─────────────┐
│    ngrok    │  内网穿透
│  Cloudflare │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────┐
│  FastAPI (Kobe/app.py)              │
│  ┌───────────────────────────────┐  │
│  │  /telegram/webhook            │  │
│  │  (webhook.py)                 │  │
│  └────────────┬──────────────────┘  │
│               ↓                      │
│  ┌───────────────────────────────┐  │
│  │  MessageHandler               │  │
│  │  - 速率限制                   │  │
│  │  - 消息过滤                   │  │
│  │  - 路由分发                   │  │
│  └────────────┬──────────────────┘  │
│               ↓                      │
│  ┌───────────────────────────────┐  │
│  │  ChatService (LangChain)      │  │
│  │  - 上下文管理                 │  │
│  │  - LLM 调用                   │  │
│  │  - 历史记录                   │  │
│  └────────────┬──────────────────┘  │
│               ↓                      │
│  ┌───────────────────────────────┐  │
│  │  TelegramService              │  │
│  │  - API 调用                   │  │
│  │  - 消息发送                   │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
       │
       ├──→ MongoDB (聊天历史)
       └──→ Redis (速率限制)
```

## 消息处理逻辑

### 私聊消息

```python
收到消息 → 检查速率限制 → 调用 ChatService
→ 生成回复 → 发送消息 → 保存历史
```

### 群组消息（被 @ 时）

```python
收到消息 → 检测到 @机器人 → 立即处理
→ 检查速率限制 → 调用 ChatService
→ 生成回复 → 发送消息 → 保存历史
```

### 群组消息（未被 @ 时 - 防抖模式）

```python
收到第1条消息 → 存入 Redis 队列 → 启动 15 秒倒计时

收到第2条消息（5秒后）→ 追加到 Redis → 取消旧倒计时 → 重新启动 15 秒

收到第3条消息（8秒后）→ 追加到 Redis → 取消旧倒计时 → 重新启动 15 秒

15 秒静默期 → 从 Redis 获取所有消息 → 聚合成一条
→ 调用 ChatService → 生成回复 → 发送消息 → 清理 Redis
```

## 数据存储（全部使用 Redis，重启清空）

### Redis 键（支持多机器人）

**速率限制**：
- `telegram:rate_limit:{bot_id}:{user_id}` - 计数器（TTL: 60秒）

**防抖队列**：
- `telegram:debounce:{bot_id}:{chat_id}:{user_id}` - 消息队列（TTL: 30秒）

**临时上下文**（新）：
- `telegram:context:{bot_id}:{chat_id}:{user_id}` - 对话历史（TTL: 1小时）
- 存储格式：List of JSON `[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]`
- 保留最近 10 轮对话（20条消息）
- 电脑重启或 Redis 重启后自动清空

**特点**：
- 所有数据都是临时的，不做持久化
- 多机器人通过 `bot_id` 完全隔离
- 轻量级，无需维护数据库

## 配置说明

### 群组回复模式

机器人在群组中的行为：

1. **被 @ 时**：
   - 立即回复（0延迟）
   - 适用于用户明确询问的场景
   
   ```bash
   用户: @bot 帮我查一下签证进度
   机器人: (立即回复) 好的，请提供您的申请编号...
   ```

2. **未被 @ 时**：
   - 15秒防抖机制
   - 聚合用户连续发送的多条消息
   - 避免用户"分段打字"导致机器人多次回复
   
   ```bash
   用户: 我想咨询一下
   用户: 关于13A签证的问题
   用户: 续签需要多久
   (等待15秒静默期)
   机器人: (聚合3条消息后回复) 关于13A签证续签...
   ```

3. **调整防抖时间**：
   ```bash
   # .env 中修改
   TELEGRAM_GROUP_DEBOUNCE_SECONDS=10  # 改为10秒
   ```

### 速率限制

- **用户级别**：`TELEGRAM_USER_RATE_LIMIT` 条/分钟
- **群组级别**：`TELEGRAM_GROUP_RATE_LIMIT` 条/分钟
- 超限时自动发送提醒消息

## 常见问题

### Q: 机器人在群组中收不到消息？

**A**: 有两种解决方案：

1. **关闭隐私模式**（推荐）：
   - 找到 @BotFather
   - 发送 `/mybots`
   - 选择你的机器人
   - Bot Settings → Group Privacy → Turn off

2. **设为管理员**：
   - 在群组中将机器人设为管理员

### Q: Webhook 设置失败？

**A**: 检查以下几点：

1. Webhook URL 必须是 HTTPS（ngrok 自动提供）
2. 确保 FastAPI 正在运行
3. 确保 ngrok 正在运行且地址正确
4. 检查 `.env` 中的 `TELEGRAM_WEBHOOK_URL` 配置

### Q: 如何查看当前 Webhook 状态？

**A**: 访问 Telegram API：

```bash
curl https://api.telegram.org/bot你的token/getWebhookInfo
```

### Q: 消息回复慢？

**A**: 检查以下几点：

1. OpenAI API 响应速度（国内可能较慢）
2. Redis 连接状态
3. 查看日志：`Kobe/SharedUtility/RichLogger/logs/`

### Q: 如何清除 Webhook？

**A**: 

```bash
curl -X POST http://localhost:8000/telegram/delete-webhook
```

## 开发路线图

### 当前版本 (v1.0)

- [x] Webhook 实时消息接收
- [x] 私聊自动回复
- [x] 群组监控（@提及 + 关键词）
- [x] 速率限制
- [x] 聊天历史记录

### 未来计划

- [ ] Function calling 工具调用
- [ ] 多轮对话状态管理（基于 LangGraph）
- [ ] 群组管理命令（/start, /help, /settings）
- [ ] 用户权限控制（白名单/黑名单）
- [ ] 支持多媒体消息（图片、文件）
- [ ] 定时任务和主动推送

## 日志查看

日志存储在：`Kobe/SharedUtility/RichLogger/logs/`

查看实时日志：

```bash
tail -f Kobe/SharedUtility/RichLogger/logs/app_YYYYMMDD.log
```

## 技术栈

- **FastAPI** - Web 框架
- **LangChain** - LLM 编排
- **OpenAI** - 大语言模型
- **Redis** - 临时存储、速率限制、防抖队列
- **httpx** - 异步 HTTP 客户端
- **Pydantic v2** - 数据验证

## 许可证

本模块遵循 Kobe 项目的整体许可证。

