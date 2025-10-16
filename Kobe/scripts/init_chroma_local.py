#!/usr/bin/env python3
"""
ChromaDB Collection初始化脚本（本地持久化模式）

使用本地文件系统存储，不需要单独的服务器
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb


# 数据存储路径
CHROMA_DATA_PATH = str(project_root / "chroma_data")


def get_chroma_client():
    """获取ChromaDB客户端（本地持久化）"""
    return chromadb.PersistentClient(path=CHROMA_DATA_PATH)


def init_test_collection():
    """初始化测试用collection"""
    client = get_chroma_client()
    
    collection_name = "cursor_test_chat"
    
    try:
        # 尝试获取collection
        client.get_collection(collection_name)
        print(f"[OK] Collection '{collection_name}' 已存在")
    except:
        # 不存在则创建
        client.create_collection(
            name=collection_name,
            metadata={"description": "Cursor AI测试用聊天记录向量"}
        )
        print(f"[OK] Collection '{collection_name}' 创建成功")


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
            print(f"[OK] Collection '{name}' 已存在")
        except:
            client.create_collection(
                name=name,
                metadata={"description": description}
            )
            print(f"[OK] Collection '{name}' 创建成功")


def list_collections():
    """列出所有collections"""
    client = get_chroma_client()
    collections = client.list_collections()
    
    print("\n当前ChromaDB中的Collections:")
    if collections:
        for coll in collections:
            count = coll.count()
            print(f"  - {coll.name} ({count} 条记录)")
    else:
        print("  (无)")


if __name__ == "__main__":
    print(f"使用本地ChromaDB: {CHROMA_DATA_PATH}\n")
    
    try:
        # 初始化测试collection
        init_test_collection()
        
        # 初始化Telegram collections（可选，测试时不需要）
        print("\n创建Telegram collections...")
        init_telegram_collections()
        
        # 列出所有collections
        list_collections()
        
        print("\n[OK] 初始化完成!")
        print(f"\n数据存储在: {CHROMA_DATA_PATH}")
    except Exception as e:
        print(f"\n[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

