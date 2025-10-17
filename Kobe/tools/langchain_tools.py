"""
LangChain Tools 包装层
将现有的工具函数包装为 LangChain Tool 对象
"""

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional
import sys
from pathlib import Path

# 导入原有的工具实现
sys.path.insert(0, str(Path(__file__).parent.parent))
from ChatTerminal.tools.file_operations import read_file as _read_file
from ChatTerminal.tools.file_operations import write_file as _write_file
from ChatTerminal.tools.file_operations import list_directory as _list_directory
from ChatTerminal.tools.file_operations import search_files as _search_files


# ========== 工具参数Schema定义 ==========

class ReadFileInput(BaseModel):
    """read_file工具的输入参数"""
    file_path: str = Field(description="要读取的文件路径")


class WriteFileInput(BaseModel):
    """write_file工具的输入参数"""
    file_path: str = Field(description="要写入的文件路径")
    content: str = Field(description="要写入的内容")
    mode: str = Field(default="w", description="写入模式：'w'覆盖，'a'追加，默认'w'")


class ListDirectoryInput(BaseModel):
    """list_directory工具的输入参数"""
    directory: str = Field(default=".", description="要列出的目录路径，默认为当前目录")


class SearchFilesInput(BaseModel):
    """search_files工具的输入参数"""
    pattern: str = Field(description="搜索模式，如 '*.py', '*.txt', '*config*'")
    directory: str = Field(default=".", description="搜索的目录路径，默认为当前目录")
    recursive: bool = Field(default=False, description="是否递归搜索子目录，默认False")


# ========== 工具包装函数 ==========

def read_file_wrapper(file_path: str) -> str:
    """包装read_file函数，带异常保护"""
    try:
        result = _read_file(file_path)
        return result if result else f"文件 '{file_path}' 读取失败或为空"
    except Exception as e:
        return f"读取文件失败 - {file_path}: {str(e)}"


def write_file_wrapper(file_path: str, content: str, mode: str = "w") -> str:
    """包装write_file函数，带异常保护"""
    try:
        result = _write_file(file_path, content, mode)
        return result if result else f"文件 '{file_path}' 写入失败"
    except Exception as e:
        return f"写入文件失败 - {file_path}: {str(e)}"


def list_directory_wrapper(directory: str = ".") -> str:
    """包装list_directory函数，带异常保护"""
    try:
        result = _list_directory(directory)
        return result if result else f"目录 '{directory}' 为空或不可访问"
    except Exception as e:
        return f"列出目录失败 - {directory}: {str(e)}"


def search_files_wrapper(pattern: str, directory: str = ".", recursive: bool = False) -> str:
    """包装search_files函数，带异常保护"""
    try:
        result = _search_files(pattern, directory, recursive)
        return result if result else f"搜索 '{pattern}' 在 '{directory}' 未找到匹配文件"
    except Exception as e:
        return f"搜索文件失败 - {pattern}: {str(e)}"


# ========== LangChain Tool 对象定义 ==========

read_file_tool = StructuredTool.from_function(
    func=read_file_wrapper,
    name="read_file",
    description=(
        "读取本地文件内容。"
        "适用场景：需要查看或分析本地文件。"
        "输入：文件路径（字符串）。"
        "输出：文件内容（文本）。"
    ),
    args_schema=ReadFileInput
)

write_file_tool = StructuredTool.from_function(
    func=write_file_wrapper,
    name="write_file",
    description=(
        "写入内容到本地文件。"
        "适用场景：需要保存生成的内容、创建文件。"
        "输入：文件路径（字符串）、内容（字符串）、写入模式（可选：'w'覆盖或'a'追加）。"
        "输出：操作结果。"
    ),
    args_schema=WriteFileInput
)

list_directory_tool = StructuredTool.from_function(
    func=list_directory_wrapper,
    name="list_directory",
    description=(
        "列出目录中的文件和子目录。"
        "适用场景：探索文件系统、查看文件夹内容、寻找文件。"
        "输入：目录路径（可选，默认当前目录）。"
        "输出：目录中的文件和文件夹列表，包含大小信息。"
        "示例：list_directory('D:/AI_Projects') 或 list_directory('.')"
    ),
    args_schema=ListDirectoryInput
)

search_files_tool = StructuredTool.from_function(
    func=search_files_wrapper,
    name="search_files",
    description=(
        "搜索匹配特定模式的文件。"
        "适用场景：查找特定类型的文件、搜索文件名包含特定文字的文件。"
        "输入：搜索模式（如'*.py', '*.txt', '*config*'）、目录路径（可选）、是否递归（可选）。"
        "输出：匹配的文件列表。"
        "示例：search_files('*.md', 'D:/AI_Projects', recursive=True)"
    ),
    args_schema=SearchFilesInput
)


# ========== 工具列表 ==========

ALL_TOOLS = [
    read_file_tool,
    write_file_tool,
    list_directory_tool,
    search_files_tool,
]


# ========== 获取工具函数 ==========

def get_tools(tool_names: Optional[list] = None) -> list:
    """
    获取工具列表
    
    Args:
        tool_names: 指定要使用的工具名称列表，None表示使用所有工具
    
    Returns:
        Tool对象列表
    """
    if tool_names is None:
        return ALL_TOOLS
    
    tools_dict = {tool.name: tool for tool in ALL_TOOLS}
    return [tools_dict[name] for name in tool_names if name in tools_dict]
