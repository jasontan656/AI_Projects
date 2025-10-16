"""
ChromaDB向量数据库操作实现
"""
import os
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings


# 从环境变量读取配置
CHROMADB_MODE = os.getenv("CHROMADB_MODE", "local")  # "local" 或 "http"
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8001"))
CHROMADB_DATA_PATH = os.getenv("CHROMADB_DATA_PATH", str(Path(__file__).parent.parent.parent.parent / "chroma_data"))

# 初始化ChromaDB客户端
def get_chroma_client():
    """获取ChromaDB客户端"""
    if CHROMADB_MODE == "http":
        return chromadb.HttpClient(
            host=CHROMADB_HOST,
            port=CHROMADB_PORT,
            settings=Settings(anonymized_telemetry=False)
        )
    else:
        # 本地持久化模式（默认）
        return chromadb.PersistentClient(
            path=CHROMADB_DATA_PATH,
            settings=Settings(anonymized_telemetry=False)
        )


async def add_vectors(
    collection: str,
    texts: List[str],
    metadatas: List[dict],
    ids: List[str]
) -> str:
    """
    添加向量到ChromaDB
    
    Args:
        collection: Collection名称（如 "telegram_individual_chat"）
        texts: 文本列表
        metadatas: 元数据列表（每个文本对应一个metadata）
        ids: 向量ID列表
        
    Returns:
        添加结果描述
    """
    try:
        client = get_chroma_client()
        coll = client.get_collection(name=collection)
        
        # 添加文档（ChromaDB会自动向量化）
        coll.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        return f"成功添加 {len(texts)} 条向量到collection '{collection}'"
    except Exception as e:
        return f"添加向量失败: {str(e)}"


async def semantic_search(
    collection: str,
    query: str,
    filters: dict = None,
    limit: int = 5
) -> List[dict]:
    """
    语义搜索向量
    
    Args:
        collection: Collection名称
        query: 搜索查询文本
        filters: 元数据过滤条件（如 {"user_id": 123}）
        limit: 返回结果数量
        
    Returns:
        搜索结果列表，按相似度排序
    """
    try:
        client = get_chroma_client()
        coll = client.get_collection(name=collection)
        
        # 构建where条件
        where = None
        if filters:
            # 转换为ChromaDB的where格式
            where = filters
        
        # 执行查询
        results = coll.query(
            query_texts=[query],
            where=where,
            n_results=limit
        )
        
        # 格式化返回结果
        formatted_results = []
        if results and results['documents'] and len(results['documents']) > 0:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            distances = results['distances'][0] if results['distances'] else []
            ids = results['ids'][0] if results['ids'] else []
            
            for i in range(len(documents)):
                formatted_results.append({
                    'id': ids[i] if i < len(ids) else None,
                    'text': documents[i],
                    'metadata': metadatas[i] if i < len(metadatas) else {},
                    'distance': distances[i] if i < len(distances) else None,
                })
        
        return formatted_results
    except Exception as e:
        return [{"error": f"搜索失败: {str(e)}"}]


async def delete_vectors(
    collection: str,
    ids: List[str]
) -> str:
    """
    删除向量
    
    Args:
        collection: Collection名称
        ids: 要删除的向量ID列表
        
    Returns:
        删除结果描述
    """
    try:
        client = get_chroma_client()
        coll = client.get_collection(name=collection)
        
        # 删除指定ID的向量
        coll.delete(ids=ids)
        
        return f"成功从collection '{collection}' 删除 {len(ids)} 条向量"
    except Exception as e:
        return f"删除向量失败: {str(e)}"

