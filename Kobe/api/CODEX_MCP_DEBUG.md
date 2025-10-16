# Codex MCP Server 调试报告

## 当前状态

### 配置
```toml
[mcp_servers.kobe-tools]
command = "D:/AI_Projects/Kobe/.venv/Scripts/python.exe"
args = ["D:/AI_Projects/Kobe/mcp_server_codex.py"]
env = { "PYTHONPATH" = "D:/AI_Projects/Kobe" }
```

### 观察到的行为

1. **配置识别**: ✅ `codex mcp list` 正确显示服务器
2. **进程启动**: ✅ 服务器进程被Codex启动（日志显示 server_starting/running）
3. **握手失败**: ❌ 从未收到 `list_tools` 调用
4. **Codex状态**: 显示 `Auth: Unsupported`, `aggregated 0 tools from 0 servers`

### 对比 Cursor 版本（工作正常）

**Cursor (kobe.mcp_stdio):**
- 服务器启动后立即收到 `list_tools` 调用
- 工具被正常调用

**Codex (kobe.mcp_stdio_codex):**
- 服务器启动但从未收到 `list_tools`
- Codex显示超时或 timeout

## 可能的问题

1. **协议版本不匹配**: Codex 可能期望不同的MCP协议版本
2. **初始化参数**: InitializationOptions 配置可能不兼容
3. **虚拟环境路径**: `.venv` 以点开头可能导致识别问题
4. **stdio 通信**: 握手阶段的 JSON-RPC 消息可能有问题

## 测试结果

### 手动 stdin 测试
```powershell
echo '{"jsonrpc":"2.0","method":"ping","id":1}' | python.exe mcp_server_codex.py
# 结果: 返回 {"jsonrpc":"2.0","id":1,"result":{}}
```
✅ 服务器能正确响应 JSON-RPC

### 从 D 盘启动 Codex
- 问题: 一直超时
- 原因: 可能读取了项目目录而非用户目录的配置

## 下一步尝试

1. 捕获 stdio 通信日志，查看实际的握手消息
2. 对比 Codex 和 Cursor 的 MCP 协议版本
3. 尝试最简化的 MCP 服务器（只有 ping）
4. 检查是否需要特定的环境变量或权限

---
生成时间: 2025-10-16 09:58


