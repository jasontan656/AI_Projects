"""
LangChain Tools 包装层
将现有的工具函数包装为 LangChain Tool 对象
"""

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 导入原有的工具实现
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from ChatTerminal.tools.web_tools import web_search as _web_search
from ChatTerminal.tools.web_tools import fetch_webpage as _fetch_webpage
from ChatTerminal.tools.file_operations import read_file as _read_file
from ChatTerminal.tools.file_operations import write_file as _write_file
from ChatTerminal.tools.file_operations import list_directory as _list_directory
from ChatTerminal.tools.file_operations import search_files as _search_files
from ChatTerminal.tools.command_executor import execute_command as _execute_command
from ChatTerminal.tools.exa_tools import exa_search as _exa_search  # 使用模块导入语句引入 Exa 搜索函数；供 LangChain 包装
from ChatTerminal.tools.playwright_tools import playwright_capture as _playwright_capture  # 使用模块导入语句引入 Playwright 页面抓取函数；供 LangChain 包装

# 线程池懒加载，避免模块导入时立即创建（防止Windows下进程爆炸）
_thread_pool = None

def _get_thread_pool():
    """获取线程池（懒加载）"""
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool_worker")
    return _thread_pool


# ========== 工具参数Schema定义 ==========

class WebSearchInput(BaseModel):
    """web_search工具的输入参数"""
    query: str = Field(description="搜索关键词")
    num_results: int = Field(default=5, description="返回结果数量，默认5")


class FetchWebpageInput(BaseModel):
    """fetch_webpage工具的输入参数"""
    url: str = Field(description="要访问的网页URL")
    extract_text: bool = Field(default=True, description="是否提取纯文本，默认True")
    follow_links: bool = Field(default=False, description="是否跟随页面内链接继续爬取，默认False")
    max_depth: int = Field(default=1, description="最大爬取深度，默认1")
    max_links: int = Field(default=3, description="每个页面最多跟随多少个链接，默认3")


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


class ExecuteCommandInput(BaseModel):
    """execute_command工具的输入参数"""
    command: str = Field(description="要执行的命令，如 'Get-ChildItem' 或 'dir'")
    shell: str = Field(default="powershell", description="使用的shell类型：'powershell' 或 'cmd'，默认powershell")


class ExaSearchInput(BaseModel):  # 定义 Exa 搜索工具的输入模型；约束请求参数
    query: str = Field(description="要查询的关键词，建议包含上下文以提升相关性")  # 使用 Field 描述查询参数；强调上下文
    num_results: int = Field(default=5, ge=1, le=20, description="返回结果数量，范围1-20，默认5")  # 使用 Field 限制返回条数；遵循 Exa 限制
    search_type: str = Field(default="auto", description="搜索类型：auto/neural/keyword，对应 Exa API 的 type 参数")  # 使用 Field 描述搜索类型；提供取值提示
    include_contents: bool = Field(default=False, description="是否附带网页正文内容（True 时请求 search_and_contents）")  # 使用 Field 描述正文开关；提示影响


class PlaywrightCaptureInput(BaseModel):  # 定义 Playwright 捕获工具的输入模型；约束调用参数
    url: str = Field(description="需要访问的网页 URL，必须包含协议头如 https://")  # 使用 Field 描述 URL 参数；强调格式要求
    wait_selector: Optional[str] = Field(default=None, description="可选 CSS 选择器；如果提供将在渲染完成前等待该元素出现")  # 使用 Field 描述等待选择器；帮助稳定页面
    wait_ms: int = Field(default=5000, ge=1000, le=20000, description="等待超时时间（毫秒），范围 1000-20000，默认 5000")  # 使用 Field 限制等待时间；避免长时间阻塞
    screenshot: bool = Field(default=False, description="是否保存全页截图；截图将写入 ChatTerminal\\downloads 目录")  # 使用 Field 描述截图开关；提示输出位置
    screenshot_name: Optional[str] = Field(default=None, description="自定义截图文件名（无需扩展名）；未指定时使用 playwright_capture")  # 使用 Field 描述自定义文件名；避免冲突


# ========== 工具包装函数 ==========

async def web_search_wrapper(query: str, num_results: int = 5) -> str:
    """异步包装web_search函数 - 直接调用异步实现，带异常保护"""
    try:
        result = await _web_search(query, num_results)
        # 确保返回字符串，绝不返回None
        if result and isinstance(result, str):
            return result
        else:
            return f"搜索 '{query}' 未返回有效结果（返回类型: {type(result).__name__}）"
    except asyncio.CancelledError:
        return f"搜索 '{query}' 被取消"
    except TimeoutError:
        return f"搜索 '{query}' 超时"
    except Exception as e:
        return f"搜索失败 - {query}: {type(e).__name__}: {str(e)}"


async def fetch_webpage_wrapper(
    url: str, 
    extract_text: bool = True,
    follow_links: bool = False,
    max_depth: int = 1,
    max_links: int = 3
) -> str:
    """异步包装fetch_webpage函数 - 直接调用异步实现，带异常保护"""
    try:
        result = await _fetch_webpage(url, extract_text, follow_links, max_depth, max_links)
        # 确保返回字符串，绝不返回None
        if result and isinstance(result, str):
            return result
        else:
            return f"访问网页 '{url}' 未返回有效内容（返回类型: {type(result).__name__}）"
    except asyncio.CancelledError:
        return f"访问网页 '{url}' 被取消"
    except TimeoutError:
        return f"访问网页 '{url}' 超时"
    except Exception as e:
        return f"访问网页失败 - {url}: {type(e).__name__}: {str(e)}"


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


def execute_command_wrapper(command: str, shell: str = "powershell") -> str:
    """包装execute_command函数，带异常保护"""
    try:
        result = _execute_command(command, shell)
        return result if result else f"命令 '{command}' 执行无输出"
    except Exception as e:
        return f"执行命令失败 - {command}: {str(e)}"


async def exa_search_wrapper(  # 定义异步函数 exa_search_wrapper；封装 Exa 搜索调用
    query: str,
    num_results: int = 5,
    search_type: str = "auto",
    include_contents: bool = False,
) -> str:
    try:  # 尝试调用底层 Exa 搜索；若失败进入异常分支【条件分支（Branch）/ 异常处理（Exception）】
        return await _exa_search(  # 调用模块函数 _exa_search 执行实际查询；保持参数透传
            query,
            num_results=num_results,
            search_type=search_type,
            include_contents=include_contents,
        )
    except asyncio.CancelledError:  # 捕获协程取消异常；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
        raise  # 直接重新抛出取消异常；遵循异步最佳实践
    except Exception as error:  # 捕获其他异常；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
        return f"Exa 搜索失败 - {type(error).__name__}: {error}"  # 返回错误消息；保持输出一致性


async def playwright_capture_wrapper(  # 定义异步函数 playwright_capture_wrapper；封装 Playwright 页面采集调用
    url: str,
    wait_selector: Optional[str] = None,
    wait_ms: int = 5000,
    screenshot: bool = False,
    screenshot_name: Optional[str] = None,
) -> str:
    try:  # 尝试调用底层 playwright_capture；若失败进入异常分支【条件分支（Branch）/ 异常处理（Exception）】
        return await _playwright_capture(  # 调用模块函数 _playwright_capture 执行浏览器采集；保持参数透传
            url=url,
            wait_selector=wait_selector,
            wait_ms=wait_ms,
            screenshot=screenshot,
            screenshot_name=screenshot_name,
        )
    except asyncio.CancelledError:  # 捕获协程取消异常；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
        raise  # 重新抛出取消异常；保持协程语义
    except Exception as error:  # 捕获其他异常；条件成立进入分支【条件分支（Branch）/ 异常处理（Exception）】
        return f"Playwright 采集失败 - {type(error).__name__}: {error}"  # 返回格式化错误信息；帮助诊断


# ========== LangChain Tool 对象定义 ==========

web_search_tool = StructuredTool.from_function(
    func=web_search_wrapper,
    name="web_search",
    description=(
        "使用DuckDuckGo搜索引擎进行网络搜索。\n"
        "\n"
        "【适用场景】需要查找实时信息、新闻、价格、天气等\n"
        "【输入】搜索关键词（字符串）和结果数量（可选，默认5）\n"
        "【输出】搜索结果列表，包含标题、URL和摘要\n"
        "\n"
        "【重要使用原则】\n"
        "1. 搜索质量评估：每次搜索后判断结果质量，如果本次结果与之前类似或质量未提升，应停止继续搜索\n"
        "2. 及时汇报原则：获得足够信息后立即向用户汇报，不要为了追求完美而过度搜索\n"
        "3. 避免重复搜索：不要对相同或非常相似的关键词反复搜索，除非用户明确要求更多信息\n"
        "4. 信息实用性优先：优先考虑信息的实用性而非搜索的完美性，够用即可\n"
        "5. 并发搜索策略：如需多个不同角度的信息，可以一次性发起多个不同关键词的搜索，但避免串行重复\n"
        "\n"
        "【停止搜索的信号】\n"
        "- 已获得能够回答用户问题的足够信息\n"
        "- 多次搜索返回相似或重复的结果\n"
        "- 搜索结果质量没有提升\n"
        "- 用户未要求详尽调查，基础信息已足够\n"
    ),
    args_schema=WebSearchInput,
    coroutine=web_search_wrapper  # 标记为异步工具
)

fetch_webpage_tool = StructuredTool.from_function(
    func=fetch_webpage_wrapper,
    name="fetch_webpage",
    description=(
        "访问并获取网页内容。"
        "适用场景：需要查看搜索结果中某个具体页面的详细内容。"
        "输入：网页URL（必须）、是否提取纯文本（可选）、是否跟随链接（可选）。"
        "输出：网页的文本内容或HTML。"
    ),
    args_schema=FetchWebpageInput,
    coroutine=fetch_webpage_wrapper  # 标记为异步工具
)

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

execute_command_tool = StructuredTool.from_function(
    func=execute_command_wrapper,
    name="execute_command",
    description=(
        "执行Windows PowerShell或CMD命令。\n"
        "\n"
        "【重要使用原则】\n"
        "1. 从精准小范围开始：优先使用限定路径、过滤条件的命令，避免大范围搜索\n"
        "2. 逐步扩大范围：如果小范围没找到，再考虑扩大搜索范围\n"
        "3. 预估命令影响：执行前思考命令可能返回多少数据，避免全盘搜索、列出所有文件等操作\n"
        "4. 使用过滤和限制：善用 -Filter、Select-Object -First、Where-Object 等参数控制输出\n"
        "\n"
        "【适用场景】运行系统命令、查看系统信息、执行脚本、管理进程等\n"
        "\n"
        "【输入】命令字符串、shell类型（可选：'powershell' 或 'cmd'，默认powershell）\n"
        "【输出】命令执行结果（输出限制8000字符，超出会截断并提示）\n"
        "\n"
        "【推荐命令示例】\n"
        "✅ 好的做法（精准、有限制）：\n"
        "  - Get-ChildItem D:/AI_Projects -Filter '*.py' | Select-Object -First 20\n"
        "  - Get-Process | Where-Object {$_.CPU -gt 100} | Select-Object -First 10\n"
        "  - Get-ChildItem D:/AI_Projects/Kobe -Recurse -Filter 'config.py'\n"
        "\n"
        "❌ 避免的做法（范围太大）：\n"
        "  - Get-ChildItem C:\\ -Recurse  # 全盘递归搜索\n"
        "  - Get-Process  # 返回所有进程的所有信息\n"
        "  - Get-Content huge_file.log  # 读取超大文件全部内容\n"
        "\n"
        "【常用命令】Get-Location（当前目录）、Get-ChildItem（列出目录）、Get-Process（进程）"
    ),
    args_schema=ExecuteCommandInput
)

exa_search_tool = StructuredTool.from_function(  # 使用 StructuredTool 构建 Exa 搜索工具；集成到 LangChain
    func=exa_search_wrapper,  # 指定包装函数；负责调用 Exa API
    name="exa_search",  # 为工具命名；以 slug 形式供模型调用
    description=(
        "调用 Exa 向量搜索引擎获取高质量网页结果。\n"
        "【优势】结合语义检索与实时索引，适合深度研究与最新资讯。\n"
        "【参数】query 查询语句；num_results 返回条数（默认5，最大20）；"
        "search_type 可选 auto/neural/keyword；include_contents=True 时返回正文片段。\n"
        "【使用建议】当 DuckDuckGo 搜索结果质量不佳、需要最新技术博客、论文、公司资讯时优先考虑。"
    ),
    args_schema=ExaSearchInput,  # 绑定参数模型；确保调用参数经过校验
    coroutine=exa_search_wrapper,  # 指定协程实现；支持异步执行
)

playwright_capture_tool = StructuredTool.from_function(  # 使用 StructuredTool 构建 Playwright 页面采集工具；集成到 LangChain
    func=playwright_capture_wrapper,  # 指定包装函数；负责调用 Playwright 自动化
    name="playwright_capture",  # 为工具命名；以 slug 形式供模型调用
    description=(
        "使用 Playwright 无头浏览器访问网页，可等待指定元素并保存全页截图。\n"
        "【适用场景】渲染型网站、需要执行前端脚本的页面、截图取证。\n"
        "【参数】url 目标链接；wait_selector 可选 CSS 选择器；wait_ms 超时时间（毫秒）；"
        "screenshot 控制是否保存截图；screenshot_name 自定义文件名。\n"
        "执行成功会返回页面标题、HTML 片段与截图路径（若启用）。"
    ),
    args_schema=PlaywrightCaptureInput,  # 绑定参数模型；确保调用参数校验通过
    coroutine=playwright_capture_wrapper,  # 指定协程实现；支持异步运行
)


# ========== 工具列表 ==========

ALL_TOOLS = [
    web_search_tool,
    fetch_webpage_tool,
    read_file_tool,
    write_file_tool,
    list_directory_tool,
    search_files_tool,
    execute_command_tool,
    exa_search_tool,  # 新增 Exa 搜索工具；提供向量检索补充
    playwright_capture_tool,  # 新增 Playwright 页面采集工具；提供浏览器自动化能力
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
