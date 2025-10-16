#!/usr/bin/env python3
"""
ChromaDB Collection初始化脚本

用于创建必要的ChromaDB collections，供AI工具使用。
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
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8001"))


def get_chroma_client():
    """获取ChromaDB客户端"""
    return chromadb.HttpClient(
        host=CHROMADB_HOST,
        port=CHROMADB_PORT,
        settings=Settings(anonymized_telemetry=False)
    )


def init_test_collection():
    """初始化测试用collection"""
    client = get_chroma_client()
    
    collection_name = "cursor_test_chat"
    
    try:
        # 尝试获取collection
        client.get_collection(collection_name)
        print(f"✓ Collection '{collection_name}' 已存在")
    except:
        # 不存在则创建
        client.create_collection(
            name=collection_name,
            metadata={"description": "Cursor AI测试用聊天记录向量"}
        )
        print(f"✓ Collection '{collection_name}' 创建成功")


def init_telegram_collections():
    """初始化Telegram相关collections"""
    client = get_chroma_client()
    
    collections = [
        ("telegram_individual_chat", "Telegram个人聊天记录向量"),
        ("telegram_group_chat", "Telegram群组聊天记录向量"),
    ]
    
    for name, description in collections:
        try:
            client.get_collection(name)
            print(f"✓ Collection '{name}' 已存在")
        except:
            client.create_collection(
                name=name,
                metadata={"description": description}
            )
            print(f"✓ Collection '{name}' 创建成功")


def list_collections():
    """列出所有collections"""
    client = get_chroma_client()
    collections = client.list_collections()
    
    print("\n当前ChromaDB中的Collections:")
    if collections:
        for coll in collections:
            print(f"  - {coll.name}")
    else:
        print("  (无)")


if __name__ == "__main__":
    print(f"连接到ChromaDB: {CHROMADB_HOST}:{CHROMADB_PORT}\n")
    
    try:
        # 初始化测试collection
        init_test_collection()
        
        # 初始化Telegram collections（可选）
        # init_telegram_collections()
        
        # 列出所有collections
        list_collections()
        
        print("\n初始化完成!")
    except Exception as e:
        print(f"\n初始化失败: {e}")
        sys.exit(1)

