#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量配置验证脚本

验证所有数据库工具需要的环境变量是否正确加载
"""
import os
import sys
from pathlib import Path

# Windows环境强制UTF-8输出
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载.env文件
env_path = project_root / ".env"
load_dotenv(env_path)

print("=" * 60)
print("环境变量配置验证")
print("=" * 60)
print(f"\n.env 文件路径: {env_path}")
print(f".env 文件存在: {'是' if env_path.exists() else '否'}\n")

# 定义需要检查的配置
configs = {
    "ChromaDB配置": [
        ("CHROMADB_MODE", "local", "ChromaDB运行模式"),
        ("CHROMADB_HOST", "localhost", "ChromaDB服务器地址"),
        ("CHROMADB_PORT", "8001", "ChromaDB服务器端口"),
        ("CHROMADB_DATA_PATH", "./chroma_data", "ChromaDB本地数据路径"),
    ],
    "MongoDB配置": [
        ("MONGODB_URI", "mongodb://localhost:27017", "MongoDB连接URI"),
        ("MONGODB_DATABASE", "kobe", "MongoDB数据库名"),
    ],
    "Redis配置": [
        ("REDIS_HOST", "localhost", "Redis服务器地址"),
        ("REDIS_PORT", "6379", "Redis服务器端口"),
        ("REDIS_DB", "0", "Redis数据库编号"),
        ("REDIS_PASSWORD", None, "Redis密码（可选）"),
        ("REDIS_URL", "redis://localhost:6379/0", "Redis连接URL"),
    ],
}

# 验证配置
all_ok = True

for section, items in configs.items():
    print(f"\n【{section}】")
    print("-" * 60)
    
    for key, expected_default, description in items:
        value = os.getenv(key)
        
        if value is None:
            status = "[X] 未设置（使用默认值）"
            display_value = expected_default or "(无)"
            if expected_default is None:
                status = "[OK] 未设置（可选）"
        else:
            status = "[OK] 已设置"
            display_value = value
        
        print(f"{status:25} {key:25} = {display_value}")
        print(f"{'':25} {description}")

print("\n" + "=" * 60)

# 测试工具导入
print("\n【工具模块导入测试】")
print("-" * 60)

try:
    from ChatTerminal.tools.vector_tools import chroma_ops
    print(f"[OK] ChromaDB工具导入成功")
    print(f"  - 模式: {chroma_ops.CHROMADB_MODE}")
    print(f"  - 地址: {chroma_ops.CHROMADB_HOST}:{chroma_ops.CHROMADB_PORT}")
    print(f"  - 数据路径: {chroma_ops.CHROMADB_DATA_PATH}")
except Exception as e:
    print(f"[FAIL] ChromaDB工具导入失败: {e}")
    all_ok = False

try:
    from ChatTerminal.tools.mongodb_tools import operations as mongo_ops
    print(f"\n[OK] MongoDB工具导入成功")
    print(f"  - URI: {mongo_ops.MONGODB_URI}")
    print(f"  - 数据库: {mongo_ops.MONGODB_DATABASE}")
except Exception as e:
    print(f"\n[FAIL] MongoDB工具导入失败: {e}")
    all_ok = False

try:
    from ChatTerminal.tools.redis_tools import cache_manager as redis_mgr
    print(f"\n[OK] Redis工具导入成功")
    print(f"  - 地址: {redis_mgr.REDIS_HOST}:{redis_mgr.REDIS_PORT}")
    print(f"  - 数据库: {redis_mgr.REDIS_DB}")
    print(f"  - 密码: {'已设置' if redis_mgr.REDIS_PASSWORD else '未设置'}")
except Exception as e:
    print(f"\n[FAIL] Redis工具导入失败: {e}")
    all_ok = False

print("\n" + "=" * 60)

if all_ok:
    print("\n[OK] 所有配置验证通过！")
else:
    print("\n[FAIL] 部分配置验证失败，请检查")

print("\n提示：")
print("1. ChromaDB默认使用本地持久化模式，无需启动服务器")
print("2. 如需使用HTTP模式，设置 CHROMADB_MODE=http")
print("3. 所有配置都支持通过.env文件或环境变量设置")
print("4. 未设置的可选配置将使用默认值")

print("\n" + "=" * 60)

