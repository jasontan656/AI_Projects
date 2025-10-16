# MCP Server HTTP

基于 **Streamable HTTP** 传输的 **Model Context Protocol** 服务器，提供统一的工具发现与调用能力，支持一对多客户端并发连接。

## 特性

- **JSON-RPC 2.0 协议**：完整实现 MCP 规范的请求与响应格式
- **SSE 事件流**：支持服务器推送事件（进度、心跳、通知）
- **工具注册表**：自动注册现有 LangChain 工具，支持动态扩展
- **鉴权与会话管理**：Bearer Token 鉴权，基于 X-Agent-Id 的会话隔离
- **生产就绪**：结构化日志、错误处理、CORS 跨域支持
- **集成架构**：集成到主应用 app.py，与现有聊天 API 共存

## 快速开始

### 1. 安装依赖

```bash
cd D:\AI_Projects\Kobe
pip install -r Requirements.txt
```

### 2. 配置环境变量（可选）

创建 `.env` 文件或设置环境变量：

```bash
# 鉴权配置（可选）
MCP_AUTH_ENABLED=false          # 是否启用鉴权，默认 false
MCP_BEARER_TOKEN=your_token     # Bearer Token，启用鉴权时必需

# Exa 搜索 API Key（可选）
EXA_API_KEY=sk-your-exa-key
```

### 3. 启动服务器

```bash
# 方式 1: 使用启动脚本（Windows）
cd D:\AI_Projects\Kobe
mcpServer\start_server.bat

# 方式 2: 使用启动脚本（Linux/macOS）
cd /path/to/Kobe
./mcpServer/start_server.sh

# 方式 3: 使用 uvicorn 直接启动
cd D:\AI_Projects\Kobe
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 方式 4: 使用 Python __main__
python app.py
```

服务器将在 `http://127.0.0.1:8000` 启动，包含原有的聊天 API 和新增的 MCP Server 功能。

### 4. 验证服务

访问根端点查看服务信息：

```bash
curl http://127.0.0.1:8000/
```

或运行客户端测试脚本：

```bash
cd D:\AI_Projects\Kobe
python mcpServer/test_client.py
```

## API 端点

### POST /mcp

JSON-RPC 2.0 主入口，处理所有 MCP 方法调用。

**请求示例**：

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Agent-Id: my_agent" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

**响应示例**：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "web_search",
        "description": "使用 DuckDuckGo 搜索引擎搜索网页",
        "input_schema": {
          "type": "object",
          "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "num_results": {"type": "integer", "description": "返回结果数量", "default": 5}
          },
          "required": ["query"]
        }
      }
    ]
  }
}
```

### GET /mcp/stream

SSE 事件流端点，客户端订阅以接收服务器推送的事件。

**请求示例**：

```bash
curl -N -H "X-Agent-Id: my_agent" http://127.0.0.1:8000/mcp/stream
```

**事件格式**：

```
id: 1634567890
event: heartbeat
data: heartbeat

event: progress
data: {"tool": "web_search", "status": "running"}
```

### GET /health

健康检查端点。

```bash
curl http://127.0.0.1:8000/health
# 响应: {"status": "ok"}
```

## 支持的 MCP 方法

### tools/list

列出所有可用工具。

**请求参数**：无

**响应**：`{"tools": [...]}`

### tools/call

调用指定工具。

**请求参数**：
- `name` (string): 工具名称
- `arguments` (object): 工具参数

**响应**：`{"content": [...], "is_error": false}`

## 内置工具

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `web_search` | DuckDuckGo 搜索 | `query`, `num_results` |
| `fetch_webpage` | 访问网页并提取内容 | `url`, `extract_text`, `follow_links`, `max_depth`, `max_links` |
| `read_file` | 读取本地文件 | `file_path` |
| `write_file` | 写入本地文件 | `file_path`, `content`, `mode` |
| `list_directory` | 列出目录内容 | `directory` |
| `search_files` | 搜索文件 | `pattern`, `directory`, `recursive` |
| `execute_command` | 执行系统命令 | `command`, `shell` |
| `exa_search` | Exa 向量搜索 | `query`, `num_results`, `search_type`, `include_contents` |
| `playwright_capture` | 无头浏览器截图 | `url`, `wait_selector`, `wait_ms`, `screenshot`, `screenshot_name` |

## 鉴权与会话

### Bearer Token 鉴权

启用鉴权后，所有请求（除 `/`, `/health`, `/docs`）必须携带 `Authorization` 头：

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
```

### Agent ID 会话隔离

通过 `X-Agent-Id` 请求头隔离不同客户端的会话与 SSE 事件流：

```bash
curl -H "X-Agent-Id: agent_1" http://127.0.0.1:8000/mcp/stream
```

每个 Agent ID 维护独立的事件队列，互不干扰。

## 客户端集成

### Codex CLI / IDE 扩展

在 `.codex/config.toml` 中配置：

```toml
[mcp.servers.kobe]
transport = "sse"
url = "http://127.0.0.1:8000/mcp/stream"
headers = { "X-Agent-Id" = "codex", "Authorization" = "Bearer your_token" }
```

### OpenAI Agents SDK

```python
from openai import OpenAI

client = OpenAI()
client.beta.mcp.connect(
    url="http://127.0.0.1:8000/mcp",
    headers={"X-Agent-Id": "agent_1"}
)
```

### Vercel AI SDK

```typescript
import { experimental_createMCPClient } from 'ai';

const mcp = experimental_createMCPClient({
  url: 'http://127.0.0.1:8000/mcp',
  headers: { 'X-Agent-Id': 'vercel' }
});
```

### LangChain / LangGraph

```python
from langchain_mcp import MCPClient

mcp_client = MCPClient(
    base_url="http://127.0.0.1:8000/mcp",
    headers={"X-Agent-Id": "langchain"}
)
tools = mcp_client.list_tools()
```

## 开发与扩展

### 注册自定义工具

在 `mcpServer/tools_registry.py` 中添加工具注册：

```python
self.register_tool(
    name="my_custom_tool",
    description="自定义工具描述",
    input_schema={
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数描述"}
        },
        "required": ["param"]
    },
    handler=self._wrap_async(my_custom_handler)
)
```

### 目录结构

```
Kobe/
├── app.py                # 主应用（集成 MCP Server 路由）
└── mcpServer/
    ├── __init__.py       # 模块入口
    ├── models.py         # JSON-RPC 2.0 数据模型
    ├── protocol.py       # JSON-RPC 协议处理器
    ├── sse_manager.py    # SSE 事件流管理器
    ├── auth.py           # 鉴权与会话管理
    ├── rate_limiter.py   # 速率限制器
    ├── tools_registry.py # 工具注册表
    ├── test_client.py    # 客户端测试脚本
    ├── start_server.bat  # Windows 启动脚本
    ├── start_server.sh   # Linux/macOS 启动脚本
    └── README.md         # 本文档
```

**注意**：MCP Server 功能已整合到根目录 `app.py`，不再作为独立应用。

## 日志与监控

服务器日志输出到控制台，格式：

```
2025-10-15 10:30:00 | INFO | mcpServer.app | MCP Server HTTP 启动
2025-10-15 10:30:05 | INFO | mcpServer.auth | 鉴权成功: agent_id=test_client, path=/mcp
2025-10-15 10:30:06 | INFO | mcpServer.tools_registry | 工具执行成功: web_search
```

## 故障排查

### 问题：启动失败，提示端口被占用

**解决方案**：更换端口或杀死占用进程

```bash
# 更换端口
uvicorn mcpServer.main:app --port 8001

# Windows 查看占用进程
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F
```

### 问题：工具调用失败，提示 "工具未找到"

**解决方案**：检查工具名称拼写，确认工具已注册

```bash
# 查看已注册工具
curl http://127.0.0.1:8000/mcp -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### 问题：鉴权失败，返回 401/403

**解决方案**：检查环境变量与请求头

```bash
# 检查环境变量
echo $MCP_AUTH_ENABLED
echo $MCP_BEARER_TOKEN

# 确认请求携带 Authorization 头
curl -H "Authorization: Bearer your_token" ...
```

## 参考资料

- [Model Context Protocol 规范](https://modelcontextprotocol.io/)
- [Streamable HTTP 传输定义](https://modelcontextprotocol.io/docs/concepts/transports#streamable-http)
- [JSON-RPC 2.0 规范](https://www.jsonrpc.org/specification)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Server-Sent Events 规范](https://html.spec.whatwg.org/multipage/server-sent-events.html)

## 许可证

遵循项目根目录的许可证声明。

