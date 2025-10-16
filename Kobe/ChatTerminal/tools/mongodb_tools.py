"""
MongoDB工具 - AI调用入口

提供MongoDB数据库操作工具，供AI通过MCP协议调用。
支持保存、查询、更新聊天记录、用户画像等数据。
"""

from .mongodb_tools.operations import (
    save_document,
    query_documents,
    update_document,
    batch_insert,
)

__all__ = [
    'save_document',
    'query_documents',
    'update_document',
    'batch_insert',
]

