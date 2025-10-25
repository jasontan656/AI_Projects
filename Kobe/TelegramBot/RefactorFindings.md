# Refactor Findings

## 背景
- 项目：`ChatGPT-Telegram-Bot`
- 当前目标：记录未来对接 OpenAI Agents SDK 的重构路径，暂不执行改动。

## 现状梳理
- **统一请求出口**：`aient/core/request.py` 中的 `prepare_request_payload` 是所有 LLM 请求的唯一入口，生产 `(url, headers, payload, engine)`，除测试外仅被 `aient/models/chatgpt.py` 使用。
- **请求转义层**：`prepare_request_payload` 返回的基础结构会传给 `get_payload`，再由 `get_gpt_payload` / `get_gemini_payload` 等函数生成各厂商 API 的真实请求体。
- **响应转义层**：`aient/core/response.py` 的 `fetch_response`、`fetch_response_stream` 根据 `engine` 解析 HTTP 响应，将其转成 Telegram 侧复用的统一事件/文本格式。


