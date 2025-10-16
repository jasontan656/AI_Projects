"""
Redis工具 - AI调用入口

提供Redis缓存操作工具，供AI通过MCP协议调用。
用于缓存活跃会话的上下文数据，提升查询性能。
"""

from .redis_tools.cache_manager import (
    cache_data,
    get_cached,
    delete_cache,
    flush_to_mongodb,
)

__all__ = [
    'cache_data',
    'get_cached',
    'delete_cache',
    'flush_to_mongodb',
]

