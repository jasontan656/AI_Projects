"""
基于 LangChain 的 Chat API 实现
使用 Agent + stream_events 实现工具调用和流式输出
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.messages import HumanMessage, AIMessage, SystemMessage

from tools.langchain_tools import get_tools
from SharedUtility.RichLogger.trace import ensure_trace_id, get_progress_reporter

# logger removed during log conflict cleanup

# 从环境变量读取默认模型
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

router = APIRouter()


# ========== 请求/响应模型 ==========

class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    stream: bool = True
    tool_names: Optional[List[str]] = None  # 指定使用哪些工具，None=使用所有


class ChatResponse(BaseModel):
    """聊天响应（非流式）"""
    content: str
    usage: Dict[str, int]
    tool_calls_count: int


# ========== Agent 配置 ==========

def create_agent_executor(model: str = None, tool_names: List[str] = None) -> AgentExecutor:
    """
    创建 LangChain Agent Executor
    
    架构说明：
    - LangChain Agent 内部使用本地工具（性能最优，保留完整上下文管理）
    - MCP Server 独立运行，供其他框架（Claude Desktop等）调用
    - 两者共享同一套工具实现
    
    Args:
        model: OpenAI模型名称（可选，用于临时覆盖）
        tool_names: 要使用的工具名称列表
    
    Returns:
        AgentExecutor
    """
    # 初始化 LLM - 优先使用.env中的配置
    model_name = model or DEFAULT_MODEL
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.3,  # 降低temperature让模型更谨慎，减少激进的工具调用
        streaming=True,  # 启用流式输出
        stream_usage=True,  # 在流式模式下返回token统计信息
        # 显式启用并行工具调用，避免并发时遗漏tool结果
        model_kwargs={
            "parallel_tool_calls": True
        },
    )
    
    # log removed during cleanup
    
    # 使用本地工具（性能最优）
    # MCP Server 作为独立服务供外部框架使用
    tools = get_tools(tool_names)
    # log removed during cleanup
    
    # 创建 Prompt 模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个有能力的AI助手，可以使用工具帮助用户。

可用工具：
- web_search: 搜索互联网信息
- fetch_webpage: 访问网页获取详细内容
- list_directory: 列出目录内容
- search_files: 搜索文件（支持通配符如 *.py）
- read_file: 读取文件
- write_file: 写入文件
- execute_command: 执行Windows命令（PowerShell/CMD）

并发能力：
你可以在一次响应中同时发起多个工具调用来加速任务完成。例如：
- 同时搜索多个不同的关键词
- 同时访问多个网页
- 同时读取多个文件
这样可以大大提高效率，避免串行等待。

工具使用原则：
1. 如果工具返回的结果已经足够回答用户问题，立即向用户汇报，不要继续调用工具
2. 如果工具输出中包含"搜索质量自评提醒"或"已截断"等提示，认真考虑是否应该停止
3. 避免对同一个查询重复使用相同工具，除非用户明确要求更多信息
4. 在获得足够信息后，优先回答用户，而不是继续探索
5. 当需要获取多个独立信息时，一次性发起所有工具调用，而不是逐个串行执行

自然地与用户对话，高效地使用工具（包括并发调用），专注于快速帮助用户。
"""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # 创建 Agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # 创建 AgentExecutor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,  # 关闭 LangChain 自带控制台输出，改用统一结构化日志
        max_iterations=15,  # 最大迭代次数
        max_execution_time=180,  # 最大执行时间（秒）
        return_intermediate_steps=True,  # 返回中间步骤
        handle_parsing_errors=True,  # 处理解析错误
        early_stopping_method="generate",  # 让LLM自然生成结束语，而不是强制停止
        # 注意：开启并发工具调用时，裁剪中间步骤可能打乱工具调用-工具结果的成对顺序，导致OpenAI报错
        # 因此这里去掉 trim_intermediate_steps，以确保消息序列完整、成对
    )
    
    return agent_executor


# ========== 消息转换 ==========

def convert_messages(messages: List[Dict[str, Any]]) -> List:
    """将API消息格式转换为LangChain消息对象"""
    langchain_messages = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
    
    return langchain_messages


# ========== 流式事件处理 ==========

async def stream_agent_events(request: ChatRequest):
    """
    使用 astream_events 流式输出 Agent 执行过程
    
    这是 LangChain 推荐的最新流式API，可以捕获：
    - 工具调用事件
    - LLM 输出 token
    - 中间步骤
    """
    # 绑定 trace，并准备日志 reporter
    trace_id = ensure_trace_id()
    reporter = get_progress_reporter("chat")
    reporter.on_agent_start(str(request.messages[-1].get("content", "")) if request.messages else "")

    # 创建 Agent Executor
    agent_executor = create_agent_executor(
        model=request.model,
        tool_names=request.tool_names
    )
    
    # 转换消息格式
    messages = convert_messages(request.messages)
    
    # 提取最后一条用户消息作为input
    last_user_message = ""
    chat_history = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
        else:
            chat_history.append(msg)
    
    # log removed during cleanup
    
    # 统计信息
    iteration = 0
    tool_calls_count = 0
    current_tool = None
    total_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0
    }
    
    try:
        # 使用 astream_events 流式执行
        async for event in agent_executor.astream_events(
            {"input": last_user_message, "chat_history": chat_history},
            version="v1"
        ):
            kind = event["event"]
            
            # ===== 1. LLM 开始思考 =====
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                
                # 输出AI回复的token
                if hasattr(chunk, "content") and chunk.content:
                    content_chunk = {
                        "type": "content_chunk",
                        "content": chunk.content
                    }
                    yield f"data: {json.dumps(content_chunk, ensure_ascii=False)}\n\n"
                
                # 捕获token统计信息（在最后一个chunk中）
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    usage = chunk.usage_metadata
                    total_usage["input_tokens"] += usage.get("input_tokens", 0)
                    total_usage["output_tokens"] += usage.get("output_tokens", 0)
                    total_usage["total_tokens"] += usage.get("total_tokens", 0)
                    pass
            
            # ===== 2. 工具调用开始 =====
            elif kind == "on_tool_start":
                tool_calls_count += 1
                iteration += 1
                tool_name = event["name"]
                tool_input = event["data"].get("input", {})
                current_tool = tool_name
                reporter.on_tool_start(tool_name, tool_input)
                
                # 格式化工具参数显示
                if tool_name == "web_search":
                    display = f"搜索: {tool_input.get('query', '')}"
                elif tool_name == "fetch_webpage":
                    display = f"访问: {tool_input.get('url', '')}"
                elif tool_name in ["read_file", "write_file"]:
                    display = f"文件: {tool_input.get('file_path', '')}"
                else:
                    display = f"{tool_name}: {str(tool_input)[:50]}"
                
                progress_item = {
                    "type": "progress",
                    "round": iteration,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "action": "tool_call",
                    "tool_name": tool_name,
                    "description": f"🔧 第{iteration}轮：{display}",
                }
                yield f"data: {json.dumps(progress_item, ensure_ascii=False)}\n\n"
            
            # ===== 3. 工具调用结束 =====
            elif kind == "on_tool_end":
                tool_output = event["data"].get("output", "")
                try:
                    out_len = len(tool_output) if isinstance(tool_output, str) else 0
                except Exception:
                    out_len = 0
                reporter.on_tool_end(current_tool or "", out_len)
                
                progress_item = {
                    "type": "progress",
                    "round": iteration,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "action": "tool_completed",
                    "description": f"✅ {current_tool} 执行完成",
                }
                yield f"data: {json.dumps(progress_item, ensure_ascii=False)}\n\n"
            
            # ===== 3.5. 工具调用错误 =====
            elif kind == "on_tool_error":
                error = event["data"].get("error", "未知错误")
                reporter.on_error(str(error))
                
                progress_item = {
                    "type": "progress",
                    "round": iteration,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "action": "tool_error",
                    "description": f"❌ {current_tool} 执行失败: {str(error)[:100]}",
                }
                yield f"data: {json.dumps(progress_item, ensure_ascii=False)}\n\n"
            
            # ===== 4. Agent 链开始 =====
            elif kind == "on_chain_start":
                if event["name"] == "AgentExecutor":
                    progress_item = {
                        "type": "progress",
                        "round": 1,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "action": "thinking",
                        "description": "🤔 AI正在思考...",
                    }
                    yield f"data: {json.dumps(progress_item, ensure_ascii=False)}\n\n"
            
            # ===== 5. Agent 链结束 =====
            elif kind == "on_chain_end":
                if event["name"] == "AgentExecutor":
                    output = event["data"].get("output", {})
                    final_output = output.get("output", "")
                    reporter.on_agent_end(tool_calls_count, total_usage.get("total_tokens", 0))
                    
                    # 发送完成消息
                    progress_item = {
                        "type": "progress",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "action": "completed",
                        "description": f"✅ 任务完成！共{tool_calls_count}次工具调用",
                    }
                    yield f"data: {json.dumps(progress_item, ensure_ascii=False)}\n\n"
                    
                    pass
                    # 发送最终结果（包含真实的token统计）
                    final_result = {
                        "type": "final",
                        "content": final_output,
                        "usage": {
                            "prompt_tokens": total_usage["input_tokens"],
                            "completion_tokens": total_usage["output_tokens"],
                            "total_tokens": total_usage["total_tokens"]
                        },
                        "tool_calls_count": tool_calls_count
                    }
                    yield f"data: {json.dumps(final_result, ensure_ascii=False)}\n\n"
        
        pass
    
    except Exception as e:
        reporter.on_error(str(e))
        error_msg = {
            "type": "error",
            "error": str(e)
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


# ========== API 路由 ==========

@router.post("/chat_langchain")
async def chat_langchain(request: ChatRequest):
    """
    基于 LangChain 的聊天接口
    
    使用：
    - LangChain Agent 自动处理工具调用循环
    - astream_events 实现流式输出
    - 无需手写while循环和工具执行逻辑
    
    优势：
    - 代码更简洁（~200行 vs 原来的~500行）
    - 社区最佳实践
    - 自动错误处理
    - 易于扩展新工具
    """
    pass
    
    if request.stream:
        return StreamingResponse(
            stream_agent_events(request),
            media_type="text/event-stream"
        )
    else:
        # 非流式模式（简化版，实际项目中可能不需要）
        return {"error": "非流式模式暂未实现，请使用 stream=true"}

