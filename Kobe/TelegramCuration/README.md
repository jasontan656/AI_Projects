# TelegramCuration

## 功能说明
- 解析 Telegram 导出（HTML/JSON）为结构化 `ChatMessage`。
- 规整与线程聚合，按主题生成 `KnowledgeSlice`。
- 提供基础 API（/api/telegram-curation/*）与 Celery 后台任务入口。

## 使用方式（服务层）

支持 HTML 或 JSON 导出，两种入口：

1) 直接传入文件路径（HTML 或 JSON）
```python
import asyncio
from Kobe.TelegramCuration.services import parse_telegram_export

async def main():
    messages = await parse_telegram_export(
        r"D:/AI_Projects/TelegramChatHistory/Original/result.json",  # 也可换成 .html
        chat_id="@channel1",
    )
    print("消息数:", len(messages))

asyncio.run(main())
```

2) 传入“导出目录”自动识别（优先选择 result.json / messages*.json）
```python
import asyncio
from Kobe.TelegramCuration.services import parse_telegram_export

async def main():
    messages = await parse_telegram_export(
        r"D:/AI_Projects/TelegramChatHistory/Original/",  # 目录
        chat_id="@channel1",
    )
    print("消息数:", len(messages))

asyncio.run(main())
```

注意：
- Telegram Desktop 的 JSON 导出顶层通常是一个对象，包含 `messages` 数组；本模块已兼容该结构。
- JSON 的 `text` 字段可能是字符串或数组（富文本片段），本模块会自动拼接为纯文本。
- 如果使用 HTML 导出，需安装 `beautifulsoup4` 与 `lxml`。

## 配置说明（见 Tech_Decisions.md §5）
必须在 `Kobe/.env` 中设置以下键：
- `OPENAI_API_KEY`（如需调用 LLM）
- `MONGODB_URI`、`REDIS_URL`、`RABBITMQ_URL`、`CHROMADB_URL`
- `APP_ENV`、`DEBUG`、`LOG_LEVEL`、`API_HOST`、`API_PORT`

## API 文档
参考 Tech_Decisions.md §3.2：
- POST `/api/telegram-curation/ingest/start`
- GET `/api/telegram-curation/task/{task_id}`
- POST `/api/telegram-curation/slices/query`
