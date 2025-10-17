# 多机器人支持说明

## 设计理念

本 Telegram Bot 模块从一开始就考虑了多机器人场景，所有数据存储和缓存都通过 `bot_id` 进行隔离。

## 核心隔离机制

### 1. MongoDB 数据隔离

**集合结构**：
```json
{
  "bot_id": 123456789,  // 机器人 ID（关键字段）
  "user_id": 987654,
  "chat_id": 112233,
  "message_text": "...",
  "bot_reply": "...",
  "timestamp": "...",
  "chat_type": "private"
}
```

**查询示例**：
```python
# 每个机器人查询自己的数据
collection.find({"bot_id": bot_id, "chat_id": chat_id, "user_id": user_id})
```

**索引建议**：
```javascript
// 为多机器人查询优化
db.telegram_chat_history.createIndex({ "bot_id": 1, "chat_id": 1, "user_id": 1, "timestamp": -1 })
```

---

### 2. Redis 键隔离

**键命名规范**：
```
telegram:rate_limit:{bot_id}:{user_id}          # 速率限制
telegram:debounce:{bot_id}:{chat_id}:{user_id}  # 防抖队列
telegram:context:{bot_id}:{chat_id}:{user_id}   # 临时上下文
```

**示例**：
```bash
# Bot A (ID: 123456789)
telegram:rate_limit:123456789:987654
telegram:debounce:123456789:112233:987654

# Bot B (ID: 987654321)
telegram:rate_limit:987654321:987654
telegram:debounce:987654321:112233:987654
```

---

## 部署多个机器人

### 方式一：同一 FastAPI 实例（推荐）

**优点**：
- 资源共享（数据库连接池、Redis 连接）
- 统一管理
- 降低运维成本

**配置方式**：
```python
# 方式 A：通过路由前缀区分
app.include_router(bot1_router, prefix="/telegram/bot1", tags=["Bot1"])
app.include_router(bot2_router, prefix="/telegram/bot2", tags=["Bot2"])

# 方式 B：通过 URL 参数区分（未来实现）
app.include_router(telegram_router, prefix="/telegram/{bot_id}", tags=["Telegram"])
```

**Webhook 设置**：
```bash
# Bot A
curl -X POST https://api.telegram.org/bot{TOKEN_A}/setWebhook \
  -d "url=https://your-domain.com/telegram/bot1/webhook"

# Bot B
curl -X POST https://api.telegram.org/bot{TOKEN_B}/setWebhook \
  -d "url=https://your-domain.com/telegram/bot2/webhook"
```

---

### 方式二：独立 FastAPI 实例

**优点**：
- 完全隔离
- 便于独立扩容
- 故障隔离

**配置方式**：
```bash
# 实例 A（端口 8000）
TELEGRAM_BOT_TOKEN=token_a
uvicorn app:app --port 8000

# 实例 B（端口 8001）
TELEGRAM_BOT_TOKEN=token_b
uvicorn app:app --port 8001
```

**注意事项**：
- 每个实例需要独立的 ngrok 隧道
- 或使用同一域名的不同路径

---

## 数据查询和分析

### 按机器人统计

```bash
# 查看某个机器人的所有键
redis-cli KEYS "telegram:*:123456789:*"

# 查看上下文数据
redis-cli GET "telegram:context:123456789:chat_id:user_id"

# 查看防抖队列
redis-cli LRANGE "telegram:debounce:123456789:chat_id:user_id" 0 -1
```

---

## 配置管理

### 环境变量设计

**当前单机器人配置**：
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_URL=https://your-domain.com
```

**未来多机器人配置（可选方案）**：
```bash
# 方案 A：前缀区分
BOT1_TELEGRAM_TOKEN=...
BOT1_WEBHOOK_URL=...

BOT2_TELEGRAM_TOKEN=...
BOT2_WEBHOOK_URL=...

# 方案 B：JSON 配置
TELEGRAM_BOTS='[
  {"name": "bot1", "token": "...", "webhook": "..."},
  {"name": "bot2", "token": "...", "webhook": "..."}
]'
```

---

## 性能考虑

### 1. 数据库索引

**必需索引**：
```javascript
// 主查询索引
db.telegram_chat_history.createIndex({ 
  "bot_id": 1, 
  "chat_id": 1, 
  "user_id": 1, 
  "timestamp": -1 
})

// 统计索引
db.telegram_chat_history.createIndex({ "bot_id": 1, "timestamp": -1 })
```

### 2. Redis 内存管理

**键过期策略**：
- 速率限制：60 秒 TTL
- 防抖队列：30 秒 TTL
- 自动清理，无需手动维护

**内存估算**：
```
单个防抖队列：~1KB（假设10条消息）
1000个活跃用户：~1MB
10个机器人：~10MB
```

### 3. 连接池共享

**当前实现**：
- MongoDB：单例连接池，所有机器人共享
- Redis：单例连接，所有机器人共享
- 无额外连接开销

---

## 安全隔离

### 1. 数据访问控制

**代码层面**：
- 所有查询强制包含 `bot_id`
- 无法跨机器人访问数据

**示例**：
```python
# ✓ 正确：包含 bot_id
await collection.find({"bot_id": bot_id, "user_id": user_id})

# ✗ 错误：缺少 bot_id（永远不会出现）
await collection.find({"user_id": user_id})
```

### 2. Webhook 验证

**建议配置**：
```bash
# 每个机器人使用不同的密钥
BOT1_WEBHOOK_SECRET=random-secret-1
BOT2_WEBHOOK_SECRET=random-secret-2
```

---

## 迁移和扩展

### 从单机器人迁移到多机器人

**步骤**：

1. **数据迁移**（如果已有数据）：
```javascript
// 为旧数据添加 bot_id
db.telegram_chat_history.updateMany(
  { bot_id: { $exists: false } },
  { $set: { bot_id: 123456789 } }  // 你的旧机器人 ID
)
```

2. **创建索引**：
```javascript
db.telegram_chat_history.createIndex({ 
  "bot_id": 1, 
  "chat_id": 1, 
  "user_id": 1, 
  "timestamp": -1 
})
```

3. **部署新机器人**：
   - 添加新的路由或实例
   - 配置新的 Token 和 Webhook
   - 自动获取新的 `bot_id`

---

## 监控和调试

### 查看机器人 ID

```bash
curl http://localhost:8000/telegram/status
```

返回：
```json
{
  "bot": {
    "id": 123456789,  // 这是 bot_id
    "username": "your_bot",
    "first_name": "Your Bot"
  }
}
```

### Redis 调试

```bash
# 查看某个机器人的所有键
redis-cli KEYS "telegram:*:123456789:*"

# 查看防抖队列
redis-cli LRANGE "telegram:debounce:123456789:112233:987654" 0 -1
```

### MongoDB 调试

```javascript
// 查看机器人列表
db.telegram_chat_history.distinct("bot_id")

// 查看每个机器人的消息数
db.telegram_chat_history.aggregate([
  { $group: { _id: "$bot_id", count: { $sum: 1 } } }
])
```

---

## 最佳实践

1. **命名规范**：
   - 机器人名称使用清晰的标识（如 `customer_service_bot`、`sales_bot`）
   - 避免使用相同的 Token（显然）

2. **日志隔离**：
   - 日志中始终包含 `bot_id`
   - 便于问题排查和审计

3. **配置管理**：
   - 使用环境变量或配置文件
   - 敏感信息不要硬编码

4. **资源共享**：
   - 同一 FastAPI 实例运行多个机器人
   - 共享数据库连接池和 Redis 连接

5. **独立扩容**：
   - 高负载机器人可独立部署
   - 通过负载均衡分发流量

---

## 总结

本模块的多机器人支持通过 `bot_id` 实现了完整的数据隔离：

- ✅ MongoDB 数据隔离
- ✅ Redis 键隔离
- ✅ 速率限制隔离
- ✅ 防抖队列隔离
- ✅ 聊天历史隔离

无需修改代码，即可支持无限数量的机器人实例！

