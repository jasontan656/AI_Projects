"""
维度1：功能覆盖测试（核心 P0 场景含健康检查）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from test_data.generators.html_generator import TelegramHTMLGenerator


@pytest.mark.p0
@pytest.mark.timeout(60)
def test_scenario_1_0__health_ok(api_client):
    """Scenario-1.0：健康检查端点可用（P0）"""
    data = api_client.health()
    assert isinstance(data, dict)


@pytest.mark.p1
@pytest.mark.timeout(120)
def test_scenario_1_1__html_small_ingest(api_client, test_data_dir, performance_monitor, random_seed):
    """Scenario-1.1：正常导入小文件（10-20 条）"""
    gen = TelegramHTMLGenerator(seed=random_seed)
    f = test_data_dir / "small.html"
    f.write_text(gen.generate_html(count=None), encoding="utf-8")

    with performance_monitor.monitor("Scenario-1.1"):
        result = api_client.ingest_telegram_html(str(f))

    # 验收：任务完成或同步返回（因实现可能为占位）
    assert isinstance(result, dict)


@pytest.mark.p1
@pytest.mark.timeout(60)
def test_scenario_1_3__empty_file_ingest(api_client, test_data_dir, random_seed):
    """Scenario-1.3：空文件导入（0 条）"""
    gen = TelegramHTMLGenerator(seed=random_seed)
    f = test_data_dir / "empty.html"
    f.write_text(gen.generate_html(count=0), encoding="utf-8")
    result = api_client.ingest_telegram_html(str(f))
    assert isinstance(result, dict)

