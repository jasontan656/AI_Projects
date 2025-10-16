# Codex MCP 配置最终版本

## 完整配置（已应用）

### 配置文件位置
- 主配置：`C:\Users\HP\.codex\config.toml`
- 项目配置：`D:\AI_Projects\.codex\config.toml` （已同步）

### 配置内容
```toml
[mcp_servers.kobe-tools]
type = "stdio"
command = "cmd"
args = ["/c", "D:\\AI_Projects\\Kobe\\.venv\\Scripts\\python.exe", "D:\\AI_Projects\\Kobe\\mcp_server_codex.py"]
startup_timeout_ms = 180000

[mcp_servers.kobe-tools.env]
APPDATA = "C:\\Users\\HP\\AppData\\Roaming"
LOCALAPPDATA = "C:\\Users\\HP\\AppData\\Local"
HOME = "C:\\Users\\HP"
SystemRoot = "C:\\Windows"
PYTHONPATH = "D:\\AI_Projects\\Kobe"
```

## 验证测试

### 1. 配置识别
```
codex mcp list
```
✅ 结果：服务器已正确识别，显示为 `kobe-tools`

### 2. 手动测试
```powershell
echo '{"jsonrpc":"2.0","method":"ping","id":1}' | D:\AI_Projects\Kobe\.venv\Scripts\python.exe D:\AI_Projects\Kobe\mcp_server_codex.py
```
✅ 结果：返回 `{"jsonrpc":"2.0","id":1,"result":{}}`

### 3. 服务器日志
- 文件：`D:\AI_Projects\Kobe\SharedUtility\RichLogger\logs\app.log`
- 最后启动：2025-10-16 10:31:36
- 状态：server_starting → server_running
- ❌ 问题：从未收到 `list_tools` 调用

### 4. Codex 日志  
- 文件：`C:\Users\HP\.codex\log\codex-tui.log` (或 `D:\AI_Projects\.codex\log\codex-tui.log`)
- 最后更新：2025-10-16 10:04:06
- ❌ 状态：`aggregated 0 tools from 0 servers`
- ❌ 错误：`request timed out`

## 问题分析

### 症状
1. Codex 能识别配置
2. Codex 能启动服务器进程（日志显示 server_running）
3. 服务器从未收到 `list_tools` 调用
4. Codex 报告超时

### 可能原因
1. **协议握手失败**：Codex 和服务器的 MCP 协议版本可能不兼容
2. **stdio 通信问题**：虽然手动测试工作，但在 Codex 子进程中可能有问题
3. **认证问题**：显示 `Auth: Unsupported`，可能导致连接被拒绝
4. **Codex 版本**：当前版本 `codex-cli 0.46.0` 对自定义 stdio 服务器支持可能有限

## 对比：Cursor vs Codex

| 项目 | Cursor (工作) | Codex (不工作) |
|------|--------------|----------------|
| 配置文件 | `Kobe/.cursor/mcp.json` | `~/.codex/config.toml` |
| 服务器启动 | ✅ | ✅ |
| list_tools 调用 | ✅ | ❌ |
| 工具聚合 | ✅ 12 tools | ❌ 0 tools |
| 日志标识 | kobe.mcp_stdio | kobe.mcp_stdio_codex |

## 最终解决方案

### 问题根源
`Server.run()` 缺少必需的 `initialization_options` 参数，导致服务器启动后立即崩溃。

### 修复代码
```python
from mcp.server import InitializationOptions
from mcp.types import ServerCapabilities

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="kobe-mcp-codex",
            server_version="1.0.0",
            capabilities=ServerCapabilities()
        )
        await server.run(read_stream, write_stream, init_options)
```

### 成功验证 (2025-10-16 10:47)
- 服务器成功启动并接收 `list_tools` 调用
- Codex 成功聚合 **12 个工具**
- 所有工具正常可用：
  - add_vectors, exa_search, execute_command
  - fetch_webpage, list_directory, playwright_capture
  - read_file, search_files, semantic_search
  - web_search, write_file

## 文件清单

已创建的文件：
- `D:\AI_Projects\Kobe\mcp_server_codex.py` - Codex 专用 MCP 服务器
- `D:\AI_Projects\Kobe\start-mcp-codex.bat` - 启动脚本
- `D:\AI_Projects\Kobe\setup.py` - Python 包配置
- `D:\AI_Projects\.codex\config.toml` - Codex 配置
- 本文档

---
最后更新：2025-10-16 10:36

