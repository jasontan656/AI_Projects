"""
MCP Server HTTP 客户端测试脚本

验证 MCP 服务器的 JSON-RPC 2.0 协议实现与工具调用能力。
"""
from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用
import asyncio  # 使用标准库模块 asyncio 导入异步工具；随后执行异步请求
import json  # 使用标准库模块 json 导入序列化工具；随后格式化输出
from typing import Any  # 使用标准库模块 typing 导入类型标注；随后提升可读性

try:  # 尝试导入 httpx；若失败进入异常分支【异常处理（Exception Handling）】
    import httpx  # 使用依赖库模块 httpx 导入异步 HTTP 客户端；随后发送请求
except ImportError:  # 捕获导入异常；条件成立进入分支【异常处理（Exception Handling）】
    print("错误: 缺少 httpx 库，请执行: pip install httpx")  # 提示用户安装依赖
    exit(1)  # 退出程序；返回错误码

# 配置
SERVER_URL = "http://127.0.0.1:8000"  # MCP 服务器地址；默认本地
BEARER_TOKEN = None  # Bearer Token；如果启用鉴权需设置
AGENT_ID = "test_client"  # Agent 标识符；用于会话隔离


async def call_rpc(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:  # 定义异步函数 call_rpc；发送 JSON-RPC 请求【异步（Async）/ HTTP 客户端（HTTP Client）】
    """调用 JSON-RPC 方法
    
    Args:
        method: 方法名
        params: 方法参数
        
    Returns:
        响应数据
    """
    headers = {  # 构造请求头字典；包含必需头部
        "Content-Type": "application/json",
        "X-Agent-Id": AGENT_ID,
    }
    
    if BEARER_TOKEN:  # 判断是否配置 Token；条件成立进入分支【条件分支（Branch）】
        headers["Authorization"] = f"Bearer {BEARER_TOKEN}"  # 添加 Authorization 头；用于鉴权
    
    payload = {  # 构造 JSON-RPC 请求体；符合 2.0 规范
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {},
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:  # 创建异步 HTTP 客户端；设置超时【上下文管理（Context Manager）/ HTTP 客户端（HTTP Client）】
        response = await client.post(  # 调用 client.post 发送请求；await 等待响应
            f"{SERVER_URL}/mcp",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()  # 检查 HTTP 状态码；抛出异常如果失败
        return response.json()  # 返回响应 JSON；解析为字典


async def test_tools_list():  # 定义异步函数 test_tools_list；测试工具列表接口【异步（Async）/ 测试（Test）】
    """测试 tools/list 方法"""
    print("\n=== 测试 tools/list ===")
    try:  # 尝试调用方法；若失败进入异常分支【异常处理（Exception Handling）】
        response = await call_rpc("tools/list")  # 调用 call_rpc 发送请求；await 等待响应
        
        if "error" in response:  # 判断是否有错误；条件成立进入分支【条件分支（Branch）】
            print(f"错误: {response['error']}")  # 打印错误信息；提示调用失败
            return  # 提前返回；结束测试
        
        result = response.get("result", {})  # 提取 result 字段；缺省使用空字典
        tools = result.get("tools", [])  # 提取 tools 数组；缺省使用空列表
        
        print(f"成功: 获取到 {len(tools)} 个工具")  # 打印成功信息；显示工具数量
        for tool in tools:  # 遍历工具列表；逐个打印信息【循环（Loop）/ 迭代（Iteration）】
            print(f"  - {tool['name']}: {tool['description']}")  # 打印工具名称与描述
        
        return tools  # 返回工具列表；供后续测试使用
    except Exception as error:  # 捕获异常；条件成立进入分支【异常处理（Exception Handling）】
        print(f"异常: {type(error).__name__}: {error}")  # 打印异常信息；包含类型与消息


async def test_tools_call():  # 定义异步函数 test_tools_call；测试工具调用接口【异步（Async）/ 测试（Test）】
    """测试 tools/call 方法"""
    print("\n=== 测试 tools/call (web_search) ===")
    try:  # 尝试调用方法；若失败进入异常分支【异常处理（Exception Handling）】
        response = await call_rpc(  # 调用 call_rpc 发送请求；await 等待响应
            "tools/call",
            {
                "name": "web_search",
                "arguments": {
                    "query": "FastAPI MCP Server",
                    "num_results": 3,
                },
            },
        )
        
        if "error" in response:  # 判断是否有错误；条件成立进入分支【条件分支（Branch）】
            print(f"错误: {response['error']}")  # 打印错误信息；提示调用失败
            return  # 提前返回；结束测试
        
        result = response.get("result", {})  # 提取 result 字段；缺省使用空字典
        content = result.get("content", [])  # 提取 content 数组；缺省使用空列表
        
        print(f"成功: 工具执行完成")  # 打印成功信息
        if content:  # 判断是否有内容；条件成立进入分支【条件分支（Branch）】
            print(f"结果预览: {content[0].get('text', '')[:200]}...")  # 打印结果前 200 字符；避免过长
    except Exception as error:  # 捕获异常；条件成立进入分支【异常处理（Exception Handling）】
        print(f"异常: {type(error).__name__}: {error}")  # 打印异常信息；包含类型与消息


async def test_read_file():  # 定义异步函数 test_read_file；测试文件读取工具【异步（Async）/ 测试（Test）】
    """测试 read_file 工具"""
    print("\n=== 测试 tools/call (read_file) ===")
    try:  # 尝试调用方法；若失败进入异常分支【异常处理（Exception Handling）】
        response = await call_rpc(  # 调用 call_rpc 发送请求；await 等待响应
            "tools/call",
            {
                "name": "read_file",
                "arguments": {
                    "file_path": "mcpServer/models.py",
                },
            },
        )
        
        if "error" in response:  # 判断是否有错误；条件成立进入分支【条件分支（Branch）】
            print(f"错误: {response['error']}")  # 打印错误信息；提示调用失败
            return  # 提前返回；结束测试
        
        result = response.get("result", {})  # 提取 result 字段；缺省使用空字典
        content = result.get("content", [])  # 提取 content 数组；缺省使用空列表
        
        print(f"成功: 文件读取完成")  # 打印成功信息
        if content:  # 判断是否有内容；条件成立进入分支【条件分支（Branch）】
            text = content[0].get("text", "")  # 提取文本内容；缺省使用空字符串
            print(f"文件大小: {len(text)} 字符")  # 打印文件大小；显示字符数
            print(f"前 200 字符: {text[:200]}...")  # 打印文件前 200 字符；避免过长
    except Exception as error:  # 捕获异常；条件成立进入分支【异常处理（Exception Handling）】
        print(f"异常: {type(error).__name__}: {error}")  # 打印异常信息；包含类型与消息


async def test_health():  # 定义异步函数 test_health；测试健康检查接口【异步（Async）/ 测试（Test）】
    """测试健康检查接口"""
    print("\n=== 测试健康检查 ===")
    try:  # 尝试访问健康检查；若失败进入异常分支【异常处理（Exception Handling）】
        async with httpx.AsyncClient() as client:  # 创建异步 HTTP 客户端；默认超时【上下文管理（Context Manager）/ HTTP 客户端（HTTP Client）】
            response = await client.get(f"{SERVER_URL}/health")  # 调用 client.get 发送请求；await 等待响应
            response.raise_for_status()  # 检查 HTTP 状态码；抛出异常如果失败
            data = response.json()  # 解析响应 JSON；获取数据
            print(f"成功: {data}")  # 打印响应数据；显示健康状态
    except Exception as error:  # 捕获异常；条件成立进入分支【异常处理（Exception Handling）】
        print(f"异常: {type(error).__name__}: {error}")  # 打印异常信息；包含类型与消息


async def main():  # 定义异步函数 main；主测试流程【异步（Async）/ 入口（Entry）】
    """主测试流程"""
    print(f"MCP Server HTTP 客户端测试")
    print(f"服务器地址: {SERVER_URL}")
    print(f"Agent ID: {AGENT_ID}")
    print(f"鉴权: {'启用' if BEARER_TOKEN else '未启用'}")
    
    # 测试健康检查
    await test_health()  # 调用 test_health 测试健康接口；await 等待完成
    
    # 测试工具列表
    await test_tools_list()  # 调用 test_tools_list 测试工具列表；await 等待完成
    
    # 测试工具调用
    await test_tools_call()  # 调用 test_tools_call 测试工具调用；await 等待完成
    
    # 测试文件读取
    await test_read_file()  # 调用 test_read_file 测试文件读取；await 等待完成
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":  # 判断是否直接运行；条件成立进入分支【条件分支（Branch）/ 入口（Entry）】
    asyncio.run(main())  # 调用 asyncio.run 执行主函数；启动事件循环

