"""
MCP Server 速率限制与配额管理

基于内存的简单速率限制实现，按 Agent ID 隔离。
"""
from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用
import time  # 使用标准库模块 time 获取时间戳；随后计算速率
import logging  # 使用标准库模块 logging 导入日志 API；随后记录限流事件
from collections import defaultdict, deque  # 使用标准库模块 collections 导入数据结构；随后存储请求历史
from typing import Deque  # 使用标准库模块 typing 导入类型标注；随后提升可读性

logger = logging.getLogger(__name__)  # 调用标准库函数 logging.getLogger 获取当前模块记录器；用于输出日志


class RateLimiter:  # 定义类 RateLimiter；实现滑动窗口速率限制【限流（Rate Limiting）/ 管理器（Manager）】
    """滑动窗口速率限制器"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):  # 定义初始化方法；构造限流器实例【初始化（Init）】
        """初始化速率限制器
        
        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests  # 使用赋值存储最大请求数；用于判断是否超限
        self.window_seconds = window_seconds  # 使用赋值存储时间窗口；用于清理过期记录
        self._requests: dict[str, Deque[float]] = defaultdict(deque)  # 使用 defaultdict 存储请求时间戳队列；键为 Agent ID
    
    def is_allowed(self, agent_id: str) -> bool:  # 定义方法 is_allowed；检查是否允许请求【限流（Rate Limiting）/ 校验（Validation）】
        """检查是否允许请求
        
        Args:
            agent_id: Agent 标识符
            
        Returns:
            是否允许
        """
        now = time.time()  # 调用 time.time 获取当前时间戳；用于计算窗口
        queue = self._requests[agent_id]  # 从字典 _requests 获取请求队列；按 Agent ID 查找
        
        # 步骤 1: 清理过期请求
        cutoff = now - self.window_seconds  # 计算截止时间戳；窗口外的请求应清理
        while queue and queue[0] < cutoff:  # 循环检查队首；若过期则移除【循环（Loop）/ 清理（Cleanup）】
            queue.popleft()  # 从队列左端移除过期时间戳；释放内存
        
        # 步骤 2: 检查是否超限
        if len(queue) >= self.max_requests:  # 判断队列长度是否达到上限；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
            logger.warning(f"速率限制触发: agent_id={agent_id}, requests={len(queue)}/{self.max_requests}")  # 在 logger 上调用 warning 记录限流；包含统计信息
            return False  # 返回不允许；拒绝请求
        
        # 步骤 3: 记录本次请求
        queue.append(now)  # 在队列右端追加当前时间戳；记录请求
        return True  # 返回允许；接受请求
    
    def reset(self, agent_id: str):  # 定义方法 reset；重置指定 Agent 的速率限制【限流（Rate Limiting）/ 清理（Cleanup）】
        """重置指定 Agent 的速率限制
        
        Args:
            agent_id: Agent 标识符
        """
        if agent_id in self._requests:  # 判断 Agent 是否存在；条件成立进入分支【条件分支（Branch）】
            del self._requests[agent_id]  # 从字典删除请求队列；释放内存
            logger.info(f"重置速率限制: agent_id={agent_id}")  # 在 logger 上调用 info 记录重置事件；包含 Agent ID
    
    def get_stats(self, agent_id: str) -> dict:  # 定义方法 get_stats；获取速率统计信息【限流（Rate Limiting）/ 查询（Query）】
        """获取速率统计信息
        
        Args:
            agent_id: Agent 标识符
            
        Returns:
            统计信息字典
        """
        now = time.time()  # 调用 time.time 获取当前时间戳；用于计算窗口
        queue = self._requests[agent_id]  # 从字典 _requests 获取请求队列；按 Agent ID 查找
        
        # 清理过期请求
        cutoff = now - self.window_seconds  # 计算截止时间戳；窗口外的请求应清理
        while queue and queue[0] < cutoff:  # 循环检查队首；若过期则移除【循环（Loop）/ 清理（Cleanup）】
            queue.popleft()  # 从队列左端移除过期时间戳；释放内存
        
        return {  # 返回统计信息字典；包含当前状态
            "agent_id": agent_id,
            "requests_in_window": len(queue),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining": max(0, self.max_requests - len(queue)),
        }


# 全局速率限制器实例
# 默认：每个 Agent 每分钟最多 60 次请求
rate_limiter = RateLimiter(max_requests=60, window_seconds=60)  # 实例化速率限制器；全局单例

