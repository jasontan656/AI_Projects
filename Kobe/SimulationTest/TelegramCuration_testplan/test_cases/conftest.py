import os
import random
import sys
from pathlib import Path

import pytest
from faker import Faker

# 允许从上层目录导入 test_config 与 utils
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_config import TestConfig
from utils.api_client import APIClient
from utils.db_client import DBClient
from utils.performance_monitor import PerformanceMonitor
from utils.service_checker import ServiceChecker


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    return TestConfig()


@pytest.fixture(scope="session")
def services_status(test_config: TestConfig) -> dict:
    checker = ServiceChecker(test_config)
    status = checker.check_all()
    print("\nServices:")
    for k, v in status.items():
        print(f"  - {k}: {'OK' if v else 'DOWN'}")
    return status


@pytest.fixture(scope="session", autouse=True)
def ensure_fastapi_up(services_status: dict):
    if not services_status.get("fastapi", False):
        pytest.exit("FastAPI is not running. Start with: uvicorn Kobe.main:app --host 0.0.0.0 --port 8000")


@pytest.fixture(scope="session")
def performance_monitor() -> PerformanceMonitor:
    return PerformanceMonitor()


@pytest.fixture(scope="session")
def api_client(test_config: TestConfig) -> APIClient:
    return APIClient(test_config)


@pytest.fixture(scope="session")
def db_client(test_config: TestConfig) -> DBClient:
    return DBClient(test_config)


@pytest.fixture(scope="session")
def random_seed() -> int:
    seed = int(os.getenv("TEST_RANDOM_SEED", random.randint(1, 1_000_000)))
    random.seed(seed)
    faker = Faker("zh_CN")
    faker.seed_instance(seed)
    print(f"\n=== Random Seed: {seed} ===\nTo reproduce: TEST_RANDOM_SEED={seed} pytest\n")
    return seed


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "test_data"
    d.mkdir()
    return d


def pytest_configure(config):  # noqa: D401
    print("\n" + "=" * 60)
    print("Starting Test Execution")
    print("=" * 60 + "\n")


def pytest_unconfigure(config):  # noqa: D401
    print("\n" + "=" * 60)
    print("Test Execution Completed")
    print("=" * 60 + "\n")

