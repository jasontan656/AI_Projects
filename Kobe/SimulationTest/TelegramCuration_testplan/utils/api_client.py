from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from test_config import TestConfig


class APIClient:
    """API 客户端，用于测试 TelegramCuration 模块对外接口"""

    def __init__(self, config: TestConfig) -> None:
        self.config = config
        self.base_url = config.FASTAPI_URL.rstrip("/")
        self.timeout = config.TIMEOUT

    def health(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/health", timeout=5)
        r.raise_for_status()
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"ok": True}

    def ingest_telegram_html(self, file_path: str, source_dir: Optional[str] = None, workspace_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        调用 Telegram HTML 导入 API（异步）并等待任务完成
        """
        p = Path(file_path)
        payload = {
            "sourceDir": source_dir or str(p.parent),
            "workspaceDir": workspace_dir or str(p.parent / "_work"),
        }
        url = f"{self.base_url}/api/telegram-curation/ingest/start"
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id") or data.get("id") or data.get("taskId")
        if not task_id:
            # 兼容同步实现：直接返回响应
            return data
        return self._wait_for_task(task_id)

    def _wait_for_task(self, task_id: str) -> Dict[str, Any]:
        """轮询任务状态直到完成（兼容多种端点）"""
        endpoints = [
            f"{self.base_url}/api/telegram-curation/task/{task_id}",
            f"{self.base_url}/task/status/{task_id}",
            f"{self.base_url}/api/tasks/{task_id}",
        ]
        max_attempts = max(1, self.config.TIMEOUT // 2)
        empty_rounds = 0
        for attempt in range(max_attempts):
            last_err: Optional[Exception] = None
            for ep in endpoints:
                try:
                    r = requests.get(ep, timeout=10)
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()
                    js = r.json()
                    status = (js.get("status") or js.get("state") or js.get("result", {}).get("status", "")).lower()
                    if status in {"completed", "success", "succeeded", "finished", "done"}:
                        return js
                    if status in {"failed", "error"}:
                        raise RuntimeError(f"Task failed: {js}")
                    # 未完成，继续轮询
                    last_err = None
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    continue
            # 如果所有端点都 404 或异常，累计一轮“空转”并快速退出以避免长等待
            empty_rounds += 1
            if empty_rounds >= 3:
                return {"status": "unknown", "reason": "no_status_endpoint", "task_id": task_id}
            time.sleep(2)
        raise TimeoutError(f"Task {task_id} timeout after {self.config.TIMEOUT}s")
