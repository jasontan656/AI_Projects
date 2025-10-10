"""Celery TaskQueue package.

Exports the Celery application object as `app` for worker CLI usage:
    celery -A Kobe.SharedUtility.TaskQueue:app worker -l info
"""

from .app import app  # 从同包模块导入 app；统一对外暴露 Celery 应用对象（使用模块导入 from .app）

__all__ = ["app"]  # 使用赋值把列表 ["app"] 绑定给变量 __all__，限定包的公开导出
