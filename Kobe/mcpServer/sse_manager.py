"""
SSE 事件流管理器

管理一对多客户端的 Server-Sent Events 连接，支持按 Agent ID 隔离推送。
"""
from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用
import asyncio  # 使用标准库模块 asyncio 导入异步工具；随后管理事件队列与并发
import logging  # 使用标准库模块 logging 导入日志 API；随后记录 SSE 事件
import time  # 使用标准库模块 time 获取时间戳；随后标注事件时间
from typing import Any, AsyncIterator  # 使用标准库模块 typing 导入类型标注；随后提升可读性
from collections import defaultdict  # 使用标准库模块 collections 导入 defaultdict；随后存储多客户端队列

logger = logging.getLogger(__name__)  # 调用标准库函数 logging.getLogger 获取当前模块记录器；用于输出日志


class SSEEvent:  # 定义类 SSEEvent；封装单个 SSE 事件数据【事件（Event）/ 数据（Data）】
    """SSE 事件对象"""
    
    def __init__(  # 定义初始化方法；构造事件实例【初始化（Init）】
        self,
        data: str,
        event: str | None = None,
        id: str | None = None,
        retry: int | None = None,
    ):
        self.data = data  # 使用赋值把事件数据绑定给实例属性 data；必填字段
        self.event = event  # 使用赋值把事件类型绑定给实例属性 event；可选字段
        self.id = id  # 使用赋值把事件 ID 绑定给实例属性 id；可选字段
        self.retry = retry  # 使用赋值把重连时间绑定给实例属性 retry；可选字段
    
    def format(self) -> str:  # 定义方法 format；格式化为 SSE 协议文本【格式化（Formatting）/ 协议（Protocol）】
        """格式化为 SSE 协议格式"""
        lines = []  # 创建空列表；收集各字段文本行
        if self.id:  # 判断是否有事件 ID；条件成立进入分支【条件分支（Branch）】
            lines.append(f"id: {self.id}")  # 在列表 lines 上调用 append 追加 ID 行；符合 SSE 格式
        if self.event:  # 判断是否有事件类型；条件成立进入分支【条件分支（Branch）】
            lines.append(f"event: {self.event}")  # 在列表 lines 上调用 append 追加事件类型行；符合 SSE 格式
        if self.retry:  # 判断是否有重连时间；条件成立进入分支【条件分支（Branch）】
            lines.append(f"retry: {self.retry}")  # 在列表 lines 上调用 append 追加重连行；符合 SSE 格式
        # 处理多行 data
        for line in self.data.split("\n"):  # 在字符串 data 上调用 split 分割多行；遍历每行【循环（Loop）/ 迭代（Iteration）】
            lines.append(f"data: {line}")  # 在列表 lines 上调用 append 追加 data 行；支持多行数据
        lines.append("")  # 在列表 lines 上调用 append 追加空行；符合 SSE 结束标记
        return "\n".join(lines) + "\n"  # 使用 join 拼接所有行；返回完整 SSE 文本


class SSEManager:  # 定义类 SSEManager；管理多客户端 SSE 连接与事件推送【管理器（Manager）/ 并发（Concurrency）】
    """SSE 事件流管理器，支持按 Agent ID 隔离"""
    
    def __init__(self):  # 定义初始化方法；构造管理器实例【初始化（Init）】
        self._queues: dict[str, asyncio.Queue[SSEEvent | None]] = defaultdict(  # 使用 defaultdict 存储客户端队列；键为 Agent ID
            lambda: asyncio.Queue(maxsize=100)  # 使用 lambda 创建异步队列工厂；限制队列长度避免内存溢出
        )
        self._heartbeat_task: asyncio.Task[None] | None = None  # 声明心跳任务属性；初始为空
    
    def start_heartbeat(self, interval: int = 30):  # 定义方法 start_heartbeat；启动心跳任务【并发（Concurrency）/ 心跳（Heartbeat）】
        """启动心跳任务，定期向所有客户端发送保活消息"""
        if self._heartbeat_task and not self._heartbeat_task.done():  # 判断心跳任务是否已运行；条件成立进入分支【条件分支（Branch）】
            return  # 直接返回；避免重复启动
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))  # 调用 asyncio.create_task 创建心跳协程任务；后台运行
    
    async def _heartbeat_loop(self, interval: int):  # 定义异步方法 _heartbeat_loop；心跳循环逻辑【并发（Concurrency）/ 循环（Loop）】
        """心跳循环，定期发送心跳事件"""
        while True:  # 无限循环；持续发送心跳【循环（Loop）/ 无限（Infinite）】
            await asyncio.sleep(interval)  # 调用 asyncio.sleep 暂停指定秒数；控制心跳频率
            heartbeat_event = SSEEvent(  # 构造心跳事件对象；包含时间戳
                data="heartbeat",
                event="heartbeat",
                id=str(int(time.time())),  # 调用 time.time 获取时间戳；转为整数后再转字符串
            )
            await self.broadcast(heartbeat_event)  # 调用 broadcast 方法广播心跳；向所有客户端推送
    
    async def subscribe(self, agent_id: str) -> AsyncIterator[str]:  # 定义异步方法 subscribe；客户端订阅事件流【订阅（Subscribe）/ 异步（Async）】
        """客户端订阅事件流
        
        Args:
            agent_id: Agent 标识符，用于隔离不同客户端
            
        Yields:
            格式化的 SSE 事件文本
        """
        queue = self._queues[agent_id]  # 从字典 _queues 获取客户端队列；按 Agent ID 隔离
        logger.info(f"客户端订阅 SSE: agent_id={agent_id}")  # 在 logger 上调用 info 记录订阅事件；包含 Agent ID
        try:  # 尝试循环推送事件；若失败进入异常分支【异常处理（Exception Handling）】
            while True:  # 无限循环；持续推送事件【循环（Loop）/ 无限（Infinite）】
                event = await queue.get()  # 调用 asyncio.Queue.get 等待事件；阻塞直到有新事件
                if event is None:  # 判断是否收到结束信号；条件成立进入分支【条件分支（Branch）/ 信号（Signal）】
                    break  # 跳出循环；结束订阅
                yield event.format()  # 在事件对象上调用 format 格式化为 SSE 文本；返回给客户端
        finally:  # finally 分支无论成功与否都会执行；清理资源【资源清理（Resource Cleanup）】
            logger.info(f"客户端断开 SSE: agent_id={agent_id}")  # 在 logger 上调用 info 记录断开事件；包含 Agent ID
            if agent_id in self._queues:  # 判断队列是否仍存在；条件成立进入分支【条件分支（Branch）】
                del self._queues[agent_id]  # 从字典 _queues 删除客户端队列；释放内存
    
    async def publish(self, agent_id: str, event: SSEEvent):  # 定义异步方法 publish；向指定客户端推送事件【发布（Publish）/ 异步（Async）】
        """向指定客户端推送事件
        
        Args:
            agent_id: 目标 Agent 标识符
            event: SSE 事件对象
        """
        if agent_id not in self._queues:  # 判断客户端是否在线；条件不成立进入分支【条件分支（Branch）/ 校验（Validation）】
            logger.warning(f"客户端不在线，跳过推送: agent_id={agent_id}")  # 在 logger 上调用 warning 记录跳过事件；提示调用方
            return  # 直接返回；不推送
        queue = self._queues[agent_id]  # 从字典 _queues 获取客户端队列；按 Agent ID 查找
        try:  # 尝试推送事件；若失败进入异常分支【异常处理（Exception Handling）】
            queue.put_nowait(event)  # 调用 asyncio.Queue.put_nowait 立即推送事件；不阻塞
        except asyncio.QueueFull:  # 捕获队列满异常；条件成立进入分支【异常处理（Exception Handling）】
            logger.error(f"客户端队列已满，丢弃事件: agent_id={agent_id}")  # 在 logger 上调用 error 记录丢弃事件；提醒队列溢出
    
    async def broadcast(self, event: SSEEvent):  # 定义异步方法 broadcast；向所有客户端广播事件【广播（Broadcast）/ 异步（Async）】
        """向所有在线客户端广播事件
        
        Args:
            event: SSE 事件对象
        """
        for agent_id in list(self._queues.keys()):  # 在字典 _queues 上调用 keys 获取所有 Agent ID；转为列表避免迭代冲突【循环（Loop）/ 迭代（Iteration）】
            await self.publish(agent_id, event)  # 调用 publish 方法推送事件；逐个客户端发送
    
    async def disconnect(self, agent_id: str):  # 定义异步方法 disconnect；断开指定客户端连接【断开（Disconnect）/ 异步（Async）】
        """断开指定客户端连接
        
        Args:
            agent_id: 目标 Agent 标识符
        """
        if agent_id in self._queues:  # 判断客户端是否在线；条件成立进入分支【条件分支（Branch）】
            await self._queues[agent_id].put(None)  # 调用 asyncio.Queue.put 推送结束信号；通知订阅方退出
            logger.info(f"主动断开客户端: agent_id={agent_id}")  # 在 logger 上调用 info 记录断开事件；包含 Agent ID

