"""维度7：真实场景（端到端轻量路径）"""

from __future__ import annotations

from pathlib import Path

import pytest

from test_data.generators.html_generator import TelegramHTMLGenerator


@pytest.mark.p2
@pytest.mark.timeout(180)
def test_scenario_7_1__mini_e2e(api_client, tmp_path, random_seed):
    gen = TelegramHTMLGenerator(seed=random_seed)
    f = Path(tmp_path) / "mini.html"
    f.write_text(gen.generate_html(count=12, include_special=True), encoding="utf-8")
    result = api_client.ingest_telegram_html(str(f))
    assert isinstance(result, dict)

