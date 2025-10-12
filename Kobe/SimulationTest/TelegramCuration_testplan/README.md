# 测试组件：TelegramCuration

本目录包含 TelegramCuration 模块的完整测试组件。

## 目录结构

```
Kobe/SimulationTest/TelegramCuration_testplan/
├── test_cases/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_01_功能覆盖.py
│   ├── test_02_数据多样性.py
│   ├── test_03_并发性能.py
│   ├── test_04_配置分支.py
│   ├── test_05_异常恢复.py
│   ├── test_06_依赖服务.py
│   └── test_07_真实场景.py
├── test_data/
│   ├── __init__.py
│   └── generators/
│       ├── __init__.py
│       ├── random_utils.py
│       ├── message_generator.py
│       └── html_generator.py
├── utils/
│   ├── __init__.py
│   ├── api_client.py
│   ├── db_client.py
│   ├── service_checker.py
│   └── performance_monitor.py
├── results/
│   ├── .gitkeep
│   └── README.md
├── logs/
│   ├── .gitkeep
│   ├── README.md
│   └── by_scenario/.gitkeep
├── requirements.txt
├── pytest.ini
├── test_config.py
├── .env.test
└── run_tests.py
```

## 快速开始

1) 安装依赖

```
pip install -r requirements.txt
```

2) 检查环境

```
python run_tests.py --check-only
```

3) 运行测试

```
# 运行 P0 场景
python run_tests.py --priority p0

# 并行运行
python run_tests.py --parallel 4
```

4) 查看报告

- HTML：results/report.html
- JSON：results/report.json
- 日志：logs/

## 复现随机化

运行时会打印随机种子；使用相同种子可复现：

```
TEST_RANDOM_SEED=123456 pytest test_cases/
```

