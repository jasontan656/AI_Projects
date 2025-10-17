#!/usr/bin/env python3
"""
Kobe MCP stdio server
Launch a MCP Server over stdio so that Cursor can discover and call tools.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Ensure UTF-8 and import path
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except Exception:
        pass

# Add project root to sys.path for imports when launched from Cursor
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
except Exception:
    pass

# Reuse existing tools
from ChatTerminal.tools.file_operations import (
    read_file,
    write_file,
    list_directory,
    search_files,
)
from ChatTerminal.tools.vector_tools import add_vectors, semantic_search, delete_vectors


# Configure logger to write ONLY to files (no console output to avoid polluting stdout)
from SharedUtility.RichLogger.file_handler import build_app_file_handler, build_error_file_handler
logger = logging.getLogger("kobe.mcp_stdio")
logger.handlers.clear()
logger.setLevel(logging.DEBUG)
logger.addHandler(build_app_file_handler(level=logging.DEBUG))
logger.addHandler(build_error_file_handler())
logger.propagate = False

server = Server("kobe-tools")


@server.list_tools()
async def list_tools() -> List[Tool]:
    try:
        logger.debug("list_tools called")
    except Exception:
        pass
    return [
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


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        try:
            logger.debug(f"call_tool start: {name} args={arguments}")
        except Exception:
            pass
        if name == "read_file":
            result = read_file(arguments.get("file_path"))
        elif name == "write_file":
            result = write_file(arguments.get("file_path"), arguments.get("content"), arguments.get("mode", "w"))
        elif name == "list_directory":
            result = list_directory(arguments.get("directory", "."))
        elif name == "search_files":
            result = search_files(arguments.get("pattern"), arguments.get("directory", "."), arguments.get("recursive", False))
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

        try:
            logger.debug(f"call_tool end: {name} len={len(str(result))}")
        except Exception:
            pass
        return [TextContent(type="text", text=str(result) if result else "")] 
    except Exception as e:
        try:
            logger.error(f"call_tool error: {name} {type(e).__name__}: {e}")
        except Exception:
            pass
        return [TextContent(type="text", text=f"工具执行失败 - {name}: {type(e).__name__}: {e}")]


async def main() -> None:
    try:
        logger.info("server_starting")
    except Exception:
        pass
    async with stdio_server() as (read_stream, write_stream):
        from mcp.server import InitializationOptions
        initialization_options = InitializationOptions(
            server_name="kobe-tools",
            server_version="1.0.0",
            capabilities={"tools": {}}
        )
        try:
            logger.info("server_running")
        except Exception:
            pass
        await server.run(read_stream, write_stream, initialization_options)


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    asyncio.run(main())


