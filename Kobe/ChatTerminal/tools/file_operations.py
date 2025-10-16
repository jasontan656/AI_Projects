"""
文件操作模块
提供文件读写、目录浏览、文件搜索等功能
"""

import os
from pathlib import Path
from typing import Optional


def read_file(file_path: str) -> str:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件内容或错误信息
    """
    try:
        path = Path(file_path).expanduser().resolve()
        
        if not path.exists():
            return f"错误: 文件不存在 - {file_path}"
        
        if not path.is_file():
            return f"错误: 不是一个文件 - {file_path}"
        
        # 检查文件大小（限制为10MB）
        file_size = path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            return f"错误: 文件过大 ({file_size / 1024 / 1024:.2f}MB)，请使用其他方式读取"
        
        # 尝试读取文件
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试其他编码
            try:
                content = path.read_text(encoding='gbk')
            except Exception:
                return "错误: 无法解码文件内容（可能是二进制文件）"
        
        return f"文件内容 ({path}):\n\n{content}"
    
    except Exception as e:
        return f"错误: 读取文件时出错 - {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """
    写入文件
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
    
    Returns:
        操作结果
    """
    try:
        path = Path(file_path).expanduser().resolve()
        
        # 创建父目录（如果不存在）
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        path.write_text(content, encoding='utf-8')
        
        return f"成功: 文件已写入 - {path}"
    
    except Exception as e:
        return f"错误: 写入文件时出错 - {str(e)}"


def list_directory(directory: str = ".") -> str:
    """
    列出目录内容
    
    Args:
        directory: 目录路径，默认为当前目录
    
    Returns:
        目录内容列表
    """
    try:
        path = Path(directory).expanduser().resolve()
        
        if not path.exists():
            return f"错误: 目录不存在 - {directory}"
        
        if not path.is_dir():
            return f"错误: 不是一个目录 - {directory}"
        
        # 获取目录内容
        items = []
        for item in sorted(path.iterdir()):
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                size_str = _format_size(size)
                items.append(f"📄 {item.name} ({size_str})")
        
        if not items:
            return f"目录为空: {path}"
        
        return f"目录内容 ({path}):\n\n" + "\n".join(items)
    
    except Exception as e:
        return f"错误: 列出目录时出错 - {str(e)}"


def search_files(pattern: str, directory: str = ".", recursive: bool = False) -> str:
    """
    搜索文件
    
    Args:
        pattern: 搜索模式（如 *.py, *.txt）
        directory: 搜索目录
        recursive: 是否递归搜索
    
    Returns:
        匹配的文件列表
    """
    try:
        path = Path(directory).expanduser().resolve()
        
        if not path.exists():
            return f"错误: 目录不存在 - {directory}"
        
        if not path.is_dir():
            return f"错误: 不是一个目录 - {directory}"
        
        # 搜索文件
        if recursive:
            matches = list(path.rglob(pattern))
        else:
            matches = list(path.glob(pattern))
        
        if not matches:
            return f"未找到匹配 '{pattern}' 的文件"
        
        # 格式化结果
        results = []
        for match in sorted(matches):
            if match.is_file():
                relative_path = match.relative_to(path)
                size = match.stat().st_size
                size_str = _format_size(size)
                results.append(f"📄 {relative_path} ({size_str})")
        
        count = len(results)
        return f"找到 {count} 个文件:\n\n" + "\n".join(results)
    
    except Exception as e:
        return f"错误: 搜索文件时出错 - {str(e)}"


def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"


if __name__ == "__main__":
    # 测试
    print(list_directory("."))
    print(search_files("*.py", ".", recursive=False))

