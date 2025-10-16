#!/usr/bin/env python3
"""
清理测试用的ChromaDB collections

警告：此脚本会删除数据，仅用于测试环境清理！
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings


# 从环境变量读取配置
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))


def get_chroma_client():
    """获取ChromaDB客户端"""
    return chromadb.HttpClient(
        host=CHROMADB_HOST,
        port=CHROMADB_PORT,
        settings=Settings(anonymized_telemetry=False)
    )


def drop_test_collection():
    """删除测试collection"""
    client = get_chroma_client()
    
    collection_name = "cursor_test_chat"
    
    try:
        client.delete_collection(collection_name)
        print(f"✓ Collection '{collection_name}' 已删除")
    except Exception as e:
        print(f"✗ 删除失败: {e}")


if __name__ == "__main__":
    print(f"连接到ChromaDB: {CHROMADB_HOST}:{CHROMADB_PORT}\n")
    
    # 二次确认
    confirm = input("确定要删除测试collection吗？(yes/no): ")
    if confirm.lower() != "yes":
        print("已取消")
        sys.exit(0)
    
    try:
        drop_test_collection()
        print("\n清理完成!")
    except Exception as e:
        print(f"\n清理失败: {e}")
        sys.exit(1)

