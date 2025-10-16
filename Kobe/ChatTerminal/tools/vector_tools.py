"""
Vector工具 - AI调用入口

提供ChromaDB向量数据库操作工具，供AI通过MCP协议调用。
用于聊天记录的语义检索和向量化存储。
"""

from ChatTerminal.tools.vector_tools.chroma_ops import (
    add_vectors,
    semantic_search,
    delete_vectors,
)

__all__ = [
    'add_vectors',
    'semantic_search',
    'delete_vectors',
]

