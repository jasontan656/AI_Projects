"""
Validation helper for pricing aggregator configuration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import yaml

from OpenaiAgents.UnifiedCS.aggregators.pricing import PricingAggregator, PricingAggregatorError

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "KnowledgeBase" / "pricing" / "pricing_expression.yaml"


def _load_config(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "aggregator" not in data:
        raise PricingAggregatorError("pricing_expression.yaml missing 'aggregator' section")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate pricing aggregator configuration.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to pricing expression YAML.")
    args = parser.parse_args()

    config_path = args.config.resolve()
    if not config_path.exists():
        raise SystemExit(f"configuration file not found: {config_path}")

    payload = _load_config(config_path)
    aggregator = PricingAggregator(payload["aggregator"])

    samples = payload.get("samples", {})
    summary = {"config": str(config_path), "aggregator_version": aggregator.VERSION, "samples_evaluated": []}

    for name, sample in samples.items():
        inputs = sample.get("pricing_inputs", {})
        result = aggregator.calculate(inputs)
        summary["samples_evaluated"].append(
            {"name": name, "currency": result["currency"], "total": result["total"]}
        )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
