# 多机器人快速启动指南

## 配置说明

### 单机器人配置（简单）

编辑 `Kobe/.env`：

```bash
TELEGRAM_BOT_TOKEN=你的token
TELEGRAM_WEBHOOK_URL=https://your-domain.ngrok-free.app
```

机器人将使用默认路径：`/telegram/webhook`

---

### 多机器人配置（推荐）

编辑 `Kobe/.env`：

```bash
# JSON 格式配置多个机器人
TELEGRAM_BOTS_JSON=[
  {
    "name": "fourwaysgroup",
    "token": "7645742612:AAEwIKz18d5KZvpkO36UXL4jE-HXlQ2B538",
    "webhook_path": "/telegram/webhook/fourwaysgroup"
  },
  {
    "name": "customer_service",
    "token": "另一个token",
    "webhook_path": "/telegram/webhook/customer_service"
  }
]

# 公网地址
TELEGRAM_WEBHOOK_URL=https://your-domain.ngrok-free.app
```

**配置字段说明**：
- `name`: 机器人标识名（用于API路径）
- `token`: Bot Token（从 @BotFather 获取）
- `webhook_path`: Webhook 路径（必须唯一）

---

## 启动步骤

### 1. 启动 FastAPI

```bash
cd D:\AI_Projects\Kobe
python app.py
```

### 2. 启动 ngrok

```bash
ngrok http 8000
```

记下 ngrok 地址（例如）：`https://abc123.ngrok-free.app`

### 3. 更新配置

编辑 `.env`，填入 ngrok 地址：

```bash
TELEGRAM_WEBHOOK_URL=https://abc123.ngrok-free.app
```

### 4. 查看已配置的机器人

```bash
curl http://localhost:8000/telegram/list-bots
```

返回：
```json
{
  "ok": true,
  "count": 2,
  "bots": [
    {
      "name": "fourwaysgroup",
      "webhook_path": "/telegram/webhook/fourwaysgroup",
      "token_preview": "7645742612..."
    },
    {
      "name": "customer_service",
      "webhook_path": "/telegram/webhook/customer_service",
      "token_preview": "98765432..."
    }
  ]
}
```

---

## 设置 Webhook

### 方式 A：批量设置（推荐）

一键设置所有机器人：

```bash
curl -X POST http://localhost:8000/telegram/setup-all-webhooks
```

返回：
```json
{
  "ok": true,
  "results": [
    {
      "bot_name": "fourwaysgroup",
      "success": true,
      "webhook_url": "https://abc123.ngrok-free.app/telegram/webhook/fourwaysgroup"
    },
    {
      "bot_name": "customer_service",
      "success": true,
      "webhook_url": "https://abc123.ngrok-free.app/telegram/webhook/customer_service"
    }
  ]
}
```

### 方式 B：单独设置

为单个机器人设置 Webhook：

```bash
curl -X POST http://localhost:8000/telegram/setup-webhook/fourwaysgroup
```

---

## 查看机器人状态

### 查看单个机器人

```bash
curl http://localhost:8000/telegram/status/fourwaysgroup
```

返回：
```json
{
  "ok": true,
  "bot": {
    "name": "fourwaysgroup",
    "id": 7645742612,
    "username": "fourwaysgroupbot",
    "first_name": "FourWays Group Bot"
  },
  "config": {
    "webhook_path": "/telegram/webhook/fourwaysgroup",
    "webhook_url": "https://abc123.ngrok-free.app/telegram/webhook/fourwaysgroup",
    "group_debounce_seconds": 15,
    "mode": "私聊立即回复 | 群组被@立即回复 | 群组未@防抖回复"
  }
}
```

---

## 测试机器人

### 测试机器人 A（fourwaysgroup）

1. 在 Telegram 中找到 @fourwaysgroupbot
2. 发送消息测试
3. 查看日志确认是哪个机器人在处理

### 测试机器人 B（customer_service）

1. 在 Telegram 中找到你的第二个机器人
2. 发送消息测试
3. 数据完全隔离，互不影响

---

## API 路由总结

### 多机器人端点

```
# Webhook（Telegram 调用）
POST /telegram/webhook/{bot_name}

# 设置 Webhook
POST /telegram/setup-webhook/{bot_name}
POST /telegram/setup-all-webhooks          # 批量设置

# 删除 Webhook
POST /telegram/delete-webhook/{bot_name}

# 查询状态
GET /telegram/status/{bot_name}
GET /telegram/list-bots                     # 列出所有机器人
```

### 示例

```bash
# fourwaysgroup 机器人
POST /telegram/webhook/fourwaysgroup
GET  /telegram/status/fourwaysgroup

# customer_service 机器人
POST /telegram/webhook/customer_service
GET  /telegram/status/customer_service
```

---

## 数据隔离

### MongoDB 自动隔离

```javascript
// fourwaysgroup 的数据
{
  "bot_id": 7645742612,
  "user_id": 123456,
  "message_text": "...",
  ...
}

// customer_service 的数据
{
  "bot_id": 987654321,
  "user_id": 123456,  // 同一个用户
  "message_text": "...",
  ...
}
```

即使是同一个用户，在不同机器人中的数据也完全独立。

### Redis 自动隔离

```
# fourwaysgroup 的防抖队列
telegram:debounce:7645742612:chat_id:user_id

# customer_service 的防抖队列
telegram:debounce:987654321:chat_id:user_id
```

---

## 添加新机器人

### 步骤

1. **创建新机器人**：
   - 找 @BotFather
   - `/newbot` 创建
   - 获取 Token

2. **更新配置**：
   ```bash
   # 编辑 .env，在 TELEGRAM_BOTS_JSON 中添加
   TELEGRAM_BOTS_JSON=[
     {...现有机器人...},
     {
       "name": "new_bot",
       "token": "新的token",
       "webhook_path": "/telegram/webhook/new_bot"
     }
   ]
   ```

3. **重启服务**：
   ```bash
   # Ctrl+C 停止
   python app.py
   ```

4. **设置 Webhook**：
   ```bash
   curl -X POST http://localhost:8000/telegram/setup-webhook/new_bot
   ```

5. **测试**：
   ```bash
   curl http://localhost:8000/telegram/status/new_bot
   ```

---

## 故障排查

### Q: 机器人收不到消息？

1. **检查 Webhook 设置**：
   ```bash
   curl https://api.telegram.org/bot你的token/getWebhookInfo
   ```

2. **检查路径是否正确**：
   ```bash
   # 应该看到你配置的路径
   curl http://localhost:8000/telegram/list-bots
   ```

3. **查看日志**：
   ```bash
   tail -f Kobe/SharedUtility/RichLogger/logs/app_*.log
   ```

### Q: 如何验证数据隔离？

```bash
# 查询 MongoDB
mongosh kobe
db.telegram_chat_history.distinct("bot_id")

# 查询 Redis
redis-cli KEYS "telegram:*"
```

### Q: 机器人太多，如何优化？

- 所有机器人共享同一个 MongoDB 连接池
- 所有机器人共享同一个 Redis 连接
- 无额外资源开销

---

## 高级配置

### 自定义 Webhook 路径

```json
{
  "name": "sales_bot",
  "token": "token",
  "webhook_path": "/api/telegram/sales"  // 自定义路径
}
```

### 使用环境变量

```bash
# 如果不想在 .env 中暴露 token
export TELEGRAM_BOTS_JSON='[...]'
```

### 配置 Webhook 密钥

```bash
TELEGRAM_WEBHOOK_SECRET=your-random-secret
```

Telegram 会在请求头中发送此密钥，增加安全性。

---

## 生产部署建议

### 负载均衡

如果某个机器人流量很大：

```
nginx
  ├─> Instance A (端口 8000) - bot1, bot2
  └─> Instance B (端口 8001) - bot3 (高流量)
```

### 监控

查看每个机器人的消息量：

```javascript
db.telegram_chat_history.aggregate([
  {
    $group: {
      _id: "$bot_id",
      total_messages: { $sum: 1 },
      unique_users: { $addToSet: "$user_id" }
    }
  }
])
```

---

## 总结

多机器人配置的优势：

- ✅ 一套代码，多个机器人
- ✅ 数据自动隔离（MongoDB + Redis）
- ✅ 资源共享（连接池）
- ✅ 灵活扩展（随时添加新机器人）
- ✅ 独立管理（每个机器人可单独设置 Webhook）

开始使用吧！

