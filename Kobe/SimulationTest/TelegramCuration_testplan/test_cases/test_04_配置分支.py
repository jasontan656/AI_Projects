"""维度4：配置分支"""

from __future__ import annotations

import os

import pytest


@pytest.mark.p2
def test_scenario_4_1__mock_llm_flag(test_config):
    os.environ.setdefault("TEST_MOCK_LLM", "True")
    cfg = test_config
    assert isinstance(cfg.MOCK_LLM, bool)

