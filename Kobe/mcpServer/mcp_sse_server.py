#!/usr/bin/env python3
"""
MCP SSE Server - 官方 SDK 实现
使用 mcp.server.sse.SseServerTransport 提供标准的 MCP SSE transport
"""

import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.sse import SseServerTransport

# 配置日志
from SharedUtility.RichLogger.logger import RichLoggerManager
logger = RichLoggerManager.for_node("mcp_sse", level=logging.DEBUG)

# 导入现有工具
from ChatTerminal.tools.web_tools import web_search, fetch_webpage
from ChatTerminal.tools.file_operations import (
    read_file,
    write_file,
    list_directory,
    search_files,
)
from ChatTerminal.tools.command_executor import execute_command
from ChatTerminal.tools.exa_tools import exa_search
from ChatTerminal.tools.playwright_tools import playwright_capture
from ChatTerminal.tools.vector_tools import add_vectors, semantic_search, delete_vectors

# 创建 MCP 服务器实例
mcp_server = Server("kobe-tools")


@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    """列出所有可用的工具"""
    logger.debug("MCP SSE: list_tools 被调用")
    return [
        Tool(
            name="web_search",
            description=(
                "使用DuckDuckGo搜索引擎进行网络搜索。\n"
                "【适用场景】需要查找实时信息、新闻、价格、天气等\n"
                "【输入】搜索关键词（字符串）和结果数量（默认5）\n"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "num_results": {"type": "integer", "description": "返回结果数量", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="fetch_webpage",
            description=(
                "访问并获取网页内容，支持正文抽取与清理。\n"
                "参数：url、extract_text、follow_links、max_depth、max_links、readability、max_chars。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要访问的网页URL"},
                    "extract_text": {"type": "boolean", "default": True},
                    "follow_links": {"type": "boolean", "default": False},
                    "max_depth": {"type": "integer", "default": 1},
                    "max_links": {"type": "integer", "default": 3},
                    "readability": {"type": "boolean", "default": True},
                    "max_chars": {"type": "integer", "default": 5000},
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="read_file",
            description="读取本地文件内容",
            inputSchema={
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        ),
        Tool(
            name="write_file",
            description="写入内容到本地文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                    "mode": {"type": "string", "default": "w"},
                },
                "required": ["file_path", "content"],
            },
        ),
        Tool(
            name="list_directory",
            description="列出目录内容",
            inputSchema={
                "type": "object",
                "properties": {"directory": {"type": "string", "default": "."}},
            },
        ),
        Tool(
            name="search_files",
            description="根据模式搜索文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "directory": {"type": "string", "default": "."},
                    "recursive": {"type": "boolean", "default": False},
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="execute_command",
            description="执行 Windows PowerShell 或 CMD 命令（小心使用）",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "shell": {"type": "string", "default": "powershell"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="exa_search",
            description="调用 Exa 向量搜索引擎获取高质量结果",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                    "search_type": {"type": "string", "default": "auto"},
                    "include_contents": {"type": "boolean", "default": False},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="playwright_capture",
            description="使用 Playwright 访问网页并可选截图",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "wait_selector": {"type": "string"},
                    "wait_ms": {"type": "integer", "default": 5000, "minimum": 1000, "maximum": 20000},
                    "screenshot": {"type": "boolean", "default": False},
                    "screenshot_name": {"type": "string"},
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="add_vectors",
            description="添加文本向量到ChromaDB collection中",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "Collection名称"},
                    "texts": {"type": "array", "items": {"type": "string"}, "description": "文本列表"},
                    "metadatas": {"type": "array", "items": {"type": "object"}, "description": "元数据列表"},
                    "ids": {"type": "array", "items": {"type": "string"}, "description": "向量ID列表"},
                },
                "required": ["collection", "texts", "metadatas", "ids"],
            },
        ),
        Tool(
            name="semantic_search",
            description="语义搜索ChromaDB中的相似文本",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "Collection名称"},
                    "query": {"type": "string", "description": "搜索查询文本"},
                    "filters": {"type": "object", "description": "元数据过滤条件（可选）"},
                    "limit": {"type": "integer", "default": 5, "description": "返回结果数量"},
                },
                "required": ["collection", "query"],
            },
        ),
        Tool(
            name="delete_vectors",
            description="删除ChromaDB中的向量（管理员工具，AI禁止调用）",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "Collection名称"},
                    "ids": {"type": "array", "items": {"type": "string"}, "description": "要删除的向量ID列表"},
                },
                "required": ["collection", "ids"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """调用指定的工具"""
    try:
        logger.debug(f"MCP SSE: 调用工具 {name}, 参数={arguments}")
        
        if name == "web_search":
            result = await web_search(arguments.get("query"), arguments.get("num_results", 5))
        elif name == "fetch_webpage":
            result = await fetch_webpage(
                arguments.get("url"),
                extract_text=arguments.get("extract_text", True),
                follow_links=arguments.get("follow_links", False),
                max_depth=arguments.get("max_depth", 1),
                max_links=arguments.get("max_links", 3),
                readability=arguments.get("readability", True),
                max_chars=arguments.get("max_chars", 5000),
            )
        elif name == "read_file":
            result = read_file(arguments.get("file_path"))
        elif name == "write_file":
            result = write_file(arguments.get("file_path"), arguments.get("content"), arguments.get("mode", "w"))
        elif name == "list_directory":
            result = list_directory(arguments.get("directory", "."))
        elif name == "search_files":
            result = search_files(arguments.get("pattern"), arguments.get("directory", "."), arguments.get("recursive", False))
        elif name == "execute_command":
            result = execute_command(arguments.get("command"), arguments.get("shell", "powershell"))
        elif name == "exa_search":
            result = await exa_search(
                arguments.get("query", ""),
                num_results=arguments.get("num_results", 5),
                search_type=arguments.get("search_type", "auto"),
                include_contents=arguments.get("include_contents", False),
            )
        elif name == "playwright_capture":
            result = await playwright_capture(
                arguments.get("url", ""),
                wait_selector=arguments.get("wait_selector"),
                wait_ms=arguments.get("wait_ms", 5000),
                screenshot=arguments.get("screenshot", False),
                screenshot_name=arguments.get("screenshot_name"),
            )
        elif name == "add_vectors":
            result = await add_vectors(
                collection=arguments.get("collection", ""),
                texts=arguments.get("texts", []),
                metadatas=arguments.get("metadatas", []),
                ids=arguments.get("ids", []),
            )
        elif name == "semantic_search":
            result = await semantic_search(
                collection=arguments.get("collection", ""),
                query=arguments.get("query", ""),
                filters=arguments.get("filters"),
                limit=arguments.get("limit", 5),
            )
        elif name == "delete_vectors":
            result = await delete_vectors(
                collection=arguments.get("collection", ""),
                ids=arguments.get("ids", []),
            )
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]

        logger.debug(f"MCP SSE: 工具 {name} 执行成功")
        return [TextContent(type="text", text=str(result) if result else "")]
        
    except Exception as e:
        logger.error(f"MCP SSE: 工具 {name} 执行失败: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=f"工具执行失败 - {name}: {type(e).__name__}: {e}")]


# 创建 SSE transport：使用 /mcp/messages 作为消息端点（与 /mcp/stream endpoint 事件一致）
sse_transport = SseServerTransport("/mcp/messages")

