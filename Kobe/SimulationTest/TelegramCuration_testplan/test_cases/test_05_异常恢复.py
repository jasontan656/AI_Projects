"""维度5：异常恢复（网络/超时/失败注入）"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests


@pytest.mark.p2
def test_scenario_5_1__health_timeout(api_client):
    """模拟 /health 请求超时并验证处理"""
    def _timeout(method, url, *a, **k):  # type: ignore[no-untyped-def]
        raise requests.Timeout("Simulated timeout")

    # requests.get -> requests.api.request -> Session.request
    # 直接打补丁到 Session.request 更可靠
    with patch("requests.sessions.Session.request", side_effect=_timeout):
        with pytest.raises(requests.Timeout):
            api_client.health()
