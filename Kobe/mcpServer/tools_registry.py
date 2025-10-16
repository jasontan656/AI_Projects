"""
MCP 工具注册表

将现有的 LangChain 工具转换为 MCP 工具格式，并提供统一的调用接口。
"""
from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用
import asyncio  # 使用标准库模块 asyncio 导入异步工具；随后管理异步执行
import logging  # 使用标准库模块 logging 导入日志 API；随后记录工具调用
from typing import Any  # 使用标准库模块 typing 导入类型标注；随后提升可读性
from concurrent.futures import ThreadPoolExecutor  # 使用标准库模块 concurrent.futures 导入线程池；随后执行同步工具
import sys  # 使用标准库模块 sys 修改模块搜索路径；随后导入项目模块
from pathlib import Path  # 使用标准库模块 pathlib 导入 Path；随后构建路径
from .models import Tool, ToolListResult, ToolCallParams, ToolCallResult  # 使用同项目模块导入工具模型；随后校验数据

# 添加项目路径到 sys.path
project_root = Path(__file__).parent.parent  # 计算项目根目录路径；用于导入工具模块
if str(project_root) not in sys.path:  # 判断路径是否已添加；条件不成立进入分支【条件分支（Branch）】
    sys.path.insert(0, str(project_root))  # 在列表 sys.path 开头插入项目路径；优先搜索

# 导入工具实现
from ChatTerminal.tools.web_tools import web_search, fetch_webpage  # 使用项目模块导入网络工具；随后封装为 MCP 工具
from ChatTerminal.tools.file_operations import (  # 使用项目模块导入文件操作工具；随后封装为 MCP 工具
    read_file,
    write_file,
    list_directory,
    search_files,
)
from ChatTerminal.tools.command_executor import execute_command  # 使用项目模块导入命令执行工具；随后封装为 MCP 工具
from ChatTerminal.tools.exa_tools import exa_search  # 使用项目模块导入 Exa 搜索工具；随后封装为 MCP 工具
from ChatTerminal.tools.playwright_tools import playwright_capture  # 使用项目模块导入 Playwright 工具；随后封装为 MCP 工具

logger = logging.getLogger(__name__)  # 调用标准库函数 logging.getLogger 获取当前模块记录器；用于输出日志

# 线程池懒加载
_thread_pool: ThreadPoolExecutor | None = None  # 声明线程池变量；初始为空


def _get_thread_pool() -> ThreadPoolExecutor:  # 定义函数 _get_thread_pool；获取线程池实例【工厂（Factory）/ 单例（Singleton）】
    """获取线程池（懒加载）"""
    global _thread_pool  # 声明访问全局变量；用于单例模式
    if _thread_pool is None:  # 判断线程池是否已创建；条件成立进入分支【条件分支（Branch）】
        _thread_pool = ThreadPoolExecutor(  # 创建线程池实例；用于执行同步工具
            max_workers=4,  # 限制最大工作线程数；避免资源耗尽
            thread_name_prefix="mcp_tool_worker",  # 设置线程名称前缀；便于调试
        )
    return _thread_pool  # 返回线程池实例；供调用方使用


class ToolsRegistry:  # 定义类 ToolsRegistry；管理 MCP 工具注册与调用【注册表（Registry）/ 管理器（Manager）】
    """MCP 工具注册表"""
    
    def __init__(self):  # 定义初始化方法；构造注册表实例【初始化（Init）】
        self._tools: dict[str, dict[str, Any]] = {}  # 使用字典存储工具元数据；键为工具名
        self._handlers: dict[str, Any] = {}  # 使用字典存储工具处理函数；键为工具名
        self._register_builtin_tools()  # 调用内部方法注册内置工具；初始化工具列表
    
    def _register_builtin_tools(self):  # 定义方法 _register_builtin_tools；注册所有内置工具【注册（Registration）/ 初始化（Init）】
        """注册所有内置工具"""
        # 注册 web_search 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="web_search",
            description="使用 DuckDuckGo 搜索引擎搜索网页，返回标题、链接与摘要",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "num_results": {"type": "integer", "description": "返回结果数量", "default": 5},
                },
                "required": ["query"],
            },
            handler=self._wrap_sync(web_search),  # 包装同步函数为异步；统一调用接口
        )
        
        # 注册 fetch_webpage 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="fetch_webpage",
            description="访问并获取网页内容，支持纯文本提取与链接跟随",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要访问的网页 URL"},
                    "extract_text": {"type": "boolean", "description": "是否提取纯文本", "default": True},
                    "follow_links": {"type": "boolean", "description": "是否跟随链接", "default": False},
                    "max_depth": {"type": "integer", "description": "最大爬取深度", "default": 1},
                    "max_links": {"type": "integer", "description": "每页最多跟随链接数", "default": 3},
                },
                "required": ["url"],
            },
            handler=self._wrap_async(fetch_webpage),  # 包装异步函数；保持异步特性
        )
        
        # 注册 read_file 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="read_file",
            description="读取本地文件内容",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                },
                "required": ["file_path"],
            },
            handler=self._wrap_sync(read_file),  # 包装同步函数为异步；统一调用接口
        )
        
        # 注册 write_file 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="write_file",
            description="写入内容到本地文件",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "mode": {"type": "string", "description": "写入模式（w/a）", "default": "w"},
                },
                "required": ["file_path", "content"],
            },
            handler=self._wrap_sync(write_file),  # 包装同步函数为异步；统一调用接口
        )
        
        # 注册 list_directory 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="list_directory",
            description="列出目录内容",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "目录路径", "default": "."},
                },
            },
            handler=self._wrap_sync(list_directory),  # 包装同步函数为异步；统一调用接口
        )
        
        # 注册 search_files 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="search_files",
            description="根据模式搜索文件",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "搜索模式（如 *.py）"},
                    "directory": {"type": "string", "description": "搜索目录", "default": "."},
                    "recursive": {"type": "boolean", "description": "是否递归", "default": False},
                },
                "required": ["pattern"],
            },
            handler=self._wrap_sync(search_files),  # 包装同步函数为异步；统一调用接口
        )
        
        # 注册 execute_command 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="execute_command",
            description="执行本地系统命令（PowerShell 或 CMD）",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "shell": {"type": "string", "description": "Shell 类型（powershell/cmd）", "default": "powershell"},
                },
                "required": ["command"],
            },
            handler=self._wrap_sync(execute_command),  # 包装同步函数为异步；统一调用接口
        )
        
        # 注册 exa_search 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="exa_search",
            description="使用 Exa 向量搜索引擎获取高质量网页结果",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询关键词"},
                    "num_results": {"type": "integer", "description": "返回结果数量", "default": 5, "minimum": 1, "maximum": 20},
                    "search_type": {"type": "string", "description": "搜索类型（auto/neural/keyword）", "default": "auto"},
                    "include_contents": {"type": "boolean", "description": "是否包含正文", "default": False},
                },
                "required": ["query"],
            },
            handler=self._wrap_async(exa_search),  # 包装异步函数；保持异步特性
        )
        
        # 注册 playwright_capture 工具
        self.register_tool(  # 调用 register_tool 方法注册工具；提供元数据与处理函数
            name="playwright_capture",
            description="使用 Playwright 无头浏览器访问网页并截图",
            input_schema={  # 定义输入参数 JSON Schema；符合 MCP 规范
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "目标网页 URL"},
                    "wait_selector": {"type": "string", "description": "等待的 CSS 选择器"},
                    "wait_ms": {"type": "integer", "description": "等待超时（毫秒）", "default": 5000, "minimum": 1000, "maximum": 20000},
                    "screenshot": {"type": "boolean", "description": "是否截图", "default": False},
                    "screenshot_name": {"type": "string", "description": "截图文件名"},
                },
                "required": ["url"],
            },
            handler=self._wrap_async(playwright_capture),  # 包装异步函数；保持异步特性
        )
        
        logger.info(f"已注册 {len(self._tools)} 个 MCP 工具")  # 在 logger 上调用 info 记录注册数量；便于监控
    
    def register_tool(  # 定义方法 register_tool；注册单个工具【注册（Registration）/ 公开 API（Public API）】
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Any,
    ) -> None:
        """注册工具
        
        Args:
            name: 工具名称
            description: 工具描述
            input_schema: 输入参数 JSON Schema
            handler: 异步处理函数
        """
        self._tools[name] = {  # 在字典 _tools 添加工具元数据；键为工具名
            "name": name,
            "description": description,
            "input_schema": input_schema,
        }
        self._handlers[name] = handler  # 在字典 _handlers 添加处理函数；键为工具名
        logger.debug(f"注册工具: {name}")  # 在 logger 上调用 debug 记录注册事件；便于调试
    
    def list_tools(self) -> ToolListResult:  # 定义方法 list_tools；返回工具列表【公开 API（Public API）/ 查询（Query）】
        """列出所有可用工具"""
        tools = [  # 使用列表推导构建工具对象列表；遍历所有工具
            Tool(**tool_meta)  # 使用 Pydantic 模型构造工具对象；解包元数据字典
            for tool_meta in self._tools.values()  # 遍历字典 _tools 的所有值；提取工具元数据【循环（Loop）/ 迭代（Iteration）】
        ]
        return ToolListResult(tools=tools)  # 返回工具列表结果对象；符合 MCP 规范
    
    async def call_tool(self, params: ToolCallParams) -> ToolCallResult:  # 定义异步方法 call_tool；执行工具调用【公开 API（Public API）/ 异步（Async）】
        """调用工具
        
        Args:
            params: 工具调用参数
            
        Returns:
            工具执行结果
        """
        tool_name = params.name  # 从参数对象提取工具名；用于查找处理函数
        if tool_name not in self._handlers:  # 判断工具是否已注册；条件不成立进入分支【条件分支（Branch）/ 校验（Validation）】
            error_msg = f"工具未找到: {tool_name}"  # 构造错误信息；描述未知工具
            logger.warning(error_msg)  # 在 logger 上调用 warning 记录警告；提示调用方
            return ToolCallResult(  # 返回错误结果对象；标记执行失败
                content=[{"type": "text", "text": error_msg}],
                is_error=True,
            )
        
        handler = self._handlers[tool_name]  # 从字典 _handlers 提取处理函数；根据工具名查找
        try:  # 尝试执行处理函数；若失败进入异常分支【异常处理（Exception Handling）】
            result = await handler(**params.arguments)  # 调用异步处理函数；展开参数字典并 await 等待结果
            logger.info(f"工具执行成功: {tool_name}")  # 在 logger 上调用 info 记录成功；包含工具名
            return ToolCallResult(  # 返回成功结果对象；包含执行结果
                content=[{"type": "text", "text": str(result)}],
                is_error=False,
            )
        except Exception as error:  # 捕获执行异常；条件成立进入分支【异常处理（Exception Handling）】
            error_msg = f"工具执行失败 [{tool_name}]: {type(error).__name__}: {error}"  # 构造错误信息；包含异常类型与消息
            logger.exception(error_msg)  # 在 logger 上调用 exception 记录堆栈；保留完整上下文
            return ToolCallResult(  # 返回错误结果对象；标记执行失败
                content=[{"type": "text", "text": error_msg}],
                is_error=True,
            )
    
    def _wrap_sync(self, func: Any) -> Any:  # 定义方法 _wrap_sync；包装同步函数为异步【包装（Wrapper）/ 适配器（Adapter）】
        """包装同步函数为异步"""
        async def wrapper(**kwargs):  # 定义异步包装函数；接收关键字参数【异步（Async）/ 闭包（Closure）】
            loop = asyncio.get_running_loop()  # 调用 asyncio.get_running_loop 获取当前事件循环；用于提交线程任务
            return await loop.run_in_executor(  # 调用 loop.run_in_executor 在线程池执行同步函数；await 等待结果
                _get_thread_pool(),  # 获取线程池实例；作为执行器
                lambda: func(**kwargs),  # 使用 lambda 包装函数调用；展开关键字参数
            )
        return wrapper  # 返回包装后的异步函数；供注册使用
    
    def _wrap_async(self, func: Any) -> Any:  # 定义方法 _wrap_async；包装异步函数（恒等）【包装（Wrapper）/ 恒等（Identity）】
        """包装异步函数（直接返回）"""
        return func  # 直接返回原函数；保持异步特性

