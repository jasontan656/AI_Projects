# MCP Server 整合说明

## 架构变更

**变更日期**：2025-10-15

**变更内容**：MCP Server 从独立 FastAPI 应用整合到主应用 `app.py`

### 变更前（独立架构）

```
mcpServer/
├── app.py              # 独立的 FastAPI 应用
├── main.py             # 独立的启动入口
└── ...                 # 其他功能模块

启动方式: uvicorn mcpServer.main:app --port 8000
```

### 变更后（集成架构）

```
Kobe/
├── app.py              # 主应用（包含 MCP Server 路由）
└── mcpServer/
    ├── protocol.py     # 功能模块
    ├── sse_manager.py  # 功能模块
    ├── tools_registry.py # 功能模块
    └── ...             # 其他功能模块

启动方式: uvicorn app:app --port 8000
```

## 整合优势

### 1. 统一管理
- ✅ 单一 FastAPI 应用实例
- ✅ 共享中间件、日志配置
- ✅ 统一的生命周期管理

### 2. 简化部署
- ✅ 单一启动入口
- ✅ 单一进程管理
- ✅ 减少端口占用

### 3. 功能共存
- ✅ 聊天 API（原有）
- ✅ MCP Server（新增）
- ✅ 其他 API（原有）

### 4. 资源共享
- ✅ 共享连接池
- ✅ 共享线程池
- ✅ 共享全局状态

## 端点映射

### 原有端点（保持不变）

- `GET /` - 根路径
- `GET /health` - 健康检查
- `POST /api/chat_langchain` - 聊天 API
- `GET /api/sse` - 原有 SSE

### 新增 MCP 端点

- `POST /mcp` - JSON-RPC 2.0 主入口
- `GET /mcp/stream` - SSE 事件流

## 启动方式

### Windows

```bash
# 方式 1: 使用启动脚本
cd D:\AI_Projects\Kobe
mcpServer\start_server.bat

# 方式 2: 直接使用 uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 方式 3: 使用 Python
python app.py
```

### Linux/macOS

```bash
# 方式 1: 使用启动脚本
cd /path/to/Kobe
./mcpServer/start_server.sh

# 方式 2: 直接使用 uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 方式 3: 使用 Python
python app.py
```

## 验证整合

### 1. 验证原有功能

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 根路径
curl http://127.0.0.1:8000/
```

### 2. 验证 MCP 功能

```bash
# 获取工具列表
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 订阅 SSE 事件流
curl -N http://127.0.0.1:8000/mcp/stream
```

### 3. 运行测试脚本

```bash
cd D:\AI_Projects\Kobe
python mcpServer/test_client.py
```

## 代码变更摘要

### 删除的文件

- `mcpServer/app.py` - 独立 FastAPI 应用（功能已迁移）
- `mcpServer/main.py` - 独立启动入口（不再需要）

### 修改的文件

- `app.py` - 新增 MCP 路由和组件初始化
- `mcpServer/start_server.bat` - 更新启动命令
- `mcpServer/start_server.sh` - 更新启动命令
- `mcpServer/README.md` - 更新文档说明
- `mcpServer/index.yaml` - 更新模块元数据

### 保留的文件（功能模块）

- `mcpServer/models.py` - 数据模型
- `mcpServer/protocol.py` - 协议处理器
- `mcpServer/sse_manager.py` - SSE 管理器
- `mcpServer/auth.py` - 鉴权模块
- `mcpServer/rate_limiter.py` - 速率限制
- `mcpServer/tools_registry.py` - 工具注册表

## 配置说明

### 环境变量（与之前相同）

```bash
# 鉴权配置
MCP_AUTH_ENABLED=false
MCP_BEARER_TOKEN=your_token

# OpenAI 配置
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini

# Exa 配置（可选）
EXA_API_KEY=sk-xxx
```

### 鉴权中间件

MCP 鉴权中间件已添加到主应用的中间件栈：

```python
# app.py
from mcpServer.auth import AuthMiddleware
app.add_middleware(AuthMiddleware)
```

### 会话管理

会话管理器通过 `X-Agent-Id` 请求头隔离不同客户端：

```bash
# 客户端 1
curl -H "X-Agent-Id: client1" http://127.0.0.1:8000/mcp/stream

# 客户端 2
curl -H "X-Agent-Id: client2" http://127.0.0.1:8000/mcp/stream
```

## 注意事项

### 1. 端口冲突

整合后只需要一个端口（默认 8000），如果原来有其他服务占用该端口，请更改配置。

### 2. 日志输出

MCP Server 日志现在输出到主应用的日志系统（RichLogger），格式统一。

### 3. 中间件顺序

MCP 鉴权中间件在 CORS 和性能监控中间件之后添加，确保正确的执行顺序。

### 4. SSE 心跳

SSE 心跳任务在模块加载时自动启动（每 30 秒一次）。

### 5. 工具注册

工具在模块加载时自动注册，无需手动调用。

## 迁移清单

如果您之前使用独立架构，需要：

- [x] 更新启动命令（从 `mcpServer.main:app` 改为 `app:app`）
- [x] 更新客户端配置中的 URL（端点路径不变，只是主机/端口可能变化）
- [x] 验证所有端点功能正常
- [x] 更新文档和脚本引用
- [ ] 更新 Docker 配置（如果使用）
- [ ] 更新 CI/CD 管道（如果使用）

## 回滚方案

如果需要回退到独立架构：

1. 恢复 `mcpServer/app.py` 和 `mcpServer/main.py`
2. 从主 `app.py` 中移除 MCP 相关代码
3. 恢复原启动脚本
4. 独立启动两个服务

## 技术支持

如有问题，请参考：
- `mcpServer/README.md` - 完整文档
- `mcpServer/test_client.py` - 测试示例
- `mcpServer/IMPLEMENTATION_SUMMARY.md` - 实施总结

