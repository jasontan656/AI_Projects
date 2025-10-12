"""维度2：数据多样性"""

from __future__ import annotations

import pytest

from test_data.generators.html_generator import TelegramHTMLGenerator


@pytest.mark.p2
def test_scenario_2_1__special_characters(random_seed):
    gen = TelegramHTMLGenerator(seed=random_seed)
    html = gen.generate_html(count=20, include_special=True)
    assert "<div class=\"history\">" in html
    # 包含emoji或标签
    assert any(x in html for x in ["😀", "<b>", "<code>"])

