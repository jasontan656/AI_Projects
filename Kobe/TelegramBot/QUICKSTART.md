# Telegram Bot 快速启动指南

## 准备工作

### 1. 确保服务运行

```bash
# 检查 Redis 是否运行（必需）
redis-cli ping
# 应返回: PONG
```

如果 Redis 未运行，启动 Docker 容器：
```bash
# 启动 Redis
docker start svc-redis
```

### 2. 配置机器人 Token

编辑 `Kobe/.env`：

```bash
# 替换为你的实际 Token
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# 可选：调整防抖时间（默认15秒）
TELEGRAM_GROUP_DEBOUNCE_SECONDS=15
```

### 2. 关闭机器人隐私模式

在 Telegram 中找到 [@BotFather](https://t.me/botfather)：

```
1. 发送 /mybots
2. 选择你的机器人
3. Bot Settings → Group Privacy → Turn off
```

这样机器人才能接收群组中的所有消息。

---

## 启动流程

### 步骤 1：启动 FastAPI

**终端 1**：
```bash
cd D:\AI_Projects\Kobe
python app.py
```

看到以下输出表示成功：
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 2：启动 ngrok

**终端 2**：
```bash
ngrok http 8000
```

记下 HTTPS 地址（例如）：
```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:8000
```

### 步骤 3：配置 Webhook URL

更新 `Kobe/.env`：
```bash
TELEGRAM_WEBHOOK_URL=https://abc123.ngrok-free.app
```

### 步骤 4：设置 Webhook

**方式 A**：使用脚本（推荐）
```bash
cd D:\AI_Projects\Kobe
python TelegramBot/setup_webhook.py
```

**方式 B**：使用 API
```bash
curl -X POST http://localhost:8000/telegram/setup-webhook
```

**方式 C**：浏览器访问
- 打开 http://localhost:8000/docs
- 找到 `POST /telegram/setup-webhook`
- 点击 "Try it out" → "Execute"

---

## 测试机器人

### 私聊测试

1. 在 Telegram 中找到你的机器人
2. 发送消息：`你好`
3. 机器人应该立即回复

### 群组测试（被 @ 时）

1. 将机器人添加到群组
2. 发送：`@你的机器人 帮我查一下`
3. 机器人应该立即回复

### 群组测试（防抖模式）

1. 在群组中连续发送（不 @机器人）：
   ```
   我想咨询一下
   关于签证的问题
   需要多久
   ```
2. 等待 15 秒
3. 机器人会聚合 3 条消息后统一回复

---

## 查看状态

浏览器访问：http://localhost:8000/telegram/status

应该看到：
```json
{
  "ok": true,
  "bot": {
    "id": 123456789,
    "username": "your_bot",
    "first_name": "Your Bot"
  },
  "config": {
    "webhook_url": "https://abc123.ngrok-free.app",
    "group_debounce_seconds": 15,
    "mode": "私聊立即回复 | 群组被@立即回复 | 群组未@防抖回复"
  }
}
```

---

## 常见问题

### Q: 机器人不回复？

1. **检查 Webhook 是否设置**：
   ```bash
   curl https://api.telegram.org/bot你的token/getWebhookInfo
   ```

2. **检查日志**：
   ```bash
   # 查看实时日志
   tail -f Kobe/SharedUtility/RichLogger/logs/app_*.log
   ```

3. **检查 Redis**：
   ```bash
   redis-cli ping
   ```

### Q: 群组中收不到消息？

确认已关闭隐私模式（见上文"准备工作 → 3"）。

### Q: 防抖不生效？

1. 确认未被 @ 机器人（被 @ 时会立即回复）
2. 检查 Redis 连接是否正常
3. 查看日志中是否有 "群组防抖任务已创建" 的提示

### Q: 想调整防抖时间？

编辑 `.env`：
```bash
TELEGRAM_GROUP_DEBOUNCE_SECONDS=10  # 改为 10 秒
```

重启 FastAPI 即可生效。

---

## 停止服务

1. **停止 FastAPI**：在终端 1 按 `Ctrl+C`
2. **停止 ngrok**：在终端 2 按 `Ctrl+C`
3. **删除 Webhook**（可选）：
   ```bash
   curl -X POST http://localhost:8000/telegram/delete-webhook
   ```

---

## 下一步

- 查看完整文档：`Kobe/TelegramBot/README.md`
- 了解架构设计：`Kobe/TelegramBot/index.yaml`
- 添加 Function calling 能力（待开发）
- 自定义对话 Prompt（修改 `chat_service.py`）

