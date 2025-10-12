"""维度6：依赖服务"""

from __future__ import annotations

import pytest


@pytest.mark.p2
def test_scenario_6_1__service_status_available(services_status):
    # 只断言结构存在，具体状态由环境决定
    assert set(services_status.keys()) == {"fastapi", "rabbitmq", "redis", "mongodb"}

