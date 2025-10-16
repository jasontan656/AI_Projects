#!/bin/bash
# MCP Server HTTP 启动脚本（Linux/macOS）

echo "========================================"
echo "MCP Server HTTP 启动脚本"
echo "========================================"
echo

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查虚拟环境
if [ -f ".venv/bin/activate" ]; then
    echo "[1/3] 激活虚拟环境..."
    source .venv/bin/activate
else
    echo "警告: 未找到虚拟环境，使用系统 Python"
fi

# 检查环境变量
echo "[2/3] 检查环境变量..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "错误: 缺少 OPENAI_API_KEY 环境变量"
    echo "请在 .env 文件中配置或设置系统环境变量"
    exit 1
fi

# 启动服务器
echo "[3/3] 启动 Kobe Backend API (包含 MCP Server)..."
echo
echo "服务器地址: http://127.0.0.1:8000"
echo "健康检查: http://127.0.0.1:8000/health"
echo "MCP 端点: http://127.0.0.1:8000/mcp"
echo "MCP 事件流: http://127.0.0.1:8000/mcp/stream"
echo "文档地址: http://127.0.0.1:8000/docs"
echo
echo "按 Ctrl+C 停止服务器"
echo

uvicorn app:app --host 0.0.0.0 --port 8000 --reload

