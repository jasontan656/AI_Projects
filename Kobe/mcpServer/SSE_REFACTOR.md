# MCP SSE 重构说明

## 变更概述

从自定义 SSE 实现迁移到官方 MCP SDK (`mcp.server.sse.SseServerTransport`)。

## 主要变更

### 1. 新文件
- `mcpServer/mcp_sse_server.py`: 使用官方 SDK 的 MCP 服务器实现

### 2. 修改文件
- `app.py`: 
  - 移除了自定义的 `/mcp` 和 `/mcp/stream` 端点
  - 添加了标准的 `/sse` (GET) 和 `/messages/` (POST) 端点
  - 使用官方 `SseServerTransport` 处理 SSE 连接

- `.codex/config.toml`:
  - 更新 URL 从 `http://127.0.0.1:8000/mcp/stream` 到 `http://127.0.0.1:8000/sse`

### 3. 端点变化

**旧端点（已移除）:**
- `POST /mcp` - JSON-RPC 请求
- `GET /mcp/stream` - SSE 事件流

**新端点（官方标准）:**
- `GET /sse` - SSE 连接端点（客户端订阅服务器事件）
- `POST /messages/` - JSON-RPC 消息端点（客户端发送请求）

## 为什么要重构？

1. **标准合规**: 官方 MCP SDK 确保完全符合协议规范
2. **减少维护**: 不需要自己维护 SSE transport 实现
3. **更好的兼容性**: 与 Codex CLI 和其他 MCP 客户端的兼容性更好
4. **问题修复**: 解决了握手和初始化流程的问题

## 测试

启动服务器：
```bash
cd D:\AI_Projects\Kobe
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

验证端点：
```bash
# 查看服务信息
curl http://127.0.0.1:8000/

# 测试 SSE 连接（应该保持打开状态）
curl -N http://127.0.0.1:8000/sse
```

使用 Codex CLI 测试：
```bash
# 在新终端中
codex
# 工具应该自动加载，可以使用 web_search, fetch_webpage 等工具
```

## 支持的工具

- `web_search` - DuckDuckGo 网络搜索
- `fetch_webpage` - 网页内容获取
- `read_file` - 读取本地文件
- `write_file` - 写入本地文件
- `list_directory` - 列出目录
- `search_files` - 搜索文件
- `execute_command` - 执行系统命令
- `exa_search` - Exa 向量搜索
- `playwright_capture` - 浏览器自动化
- `add_vectors` - 添加向量到 ChromaDB
- `semantic_search` - 语义搜索
- `delete_vectors` - 删除向量

## 参考

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [FastAPI MCP SSE 示例](https://github.com/panz2018/fastapi_mcp_sse)

