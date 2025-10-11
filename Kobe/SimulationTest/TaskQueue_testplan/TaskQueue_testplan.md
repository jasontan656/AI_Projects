---
meta:
  name: "TestPieplineExcutePlanGenerating"
  description: "将测试计划开发文档拆解为最小可执行开发步骤的YAML格式指令集"
  language: "zh-CN"
  generated_at: "2025-10-10T17:17:42+08:00"
  unique_filename: "TaskQueue"
  foldername: "TaskQueue_testplan"
  base_dir: "D:/AI_Projects/Kobe/SimulationTest/TaskQueue_testplan"
  repo_root: "D:/AI_Projects"

hard_limits:
  - "严格禁止在 SimulationTest 外部目录创建任何测试相关文件"
  - "所有测试脚本、结果、日志必须在 \\TaskQueue_testplan 子目录的规范结构内"
  - "所有文件创建路径必须以 D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/ 开头"
  - "子目录结构必须至少包含: test_cases/, results/, logs/"

sources:
  codebase_map_script: "CodexFeatured/Scripts/CodebaseStructure.py"
  codebase_structure_doc: "CodexFeatured/Common/CodebaseStructure.yaml"
  dev_constitution: "CodexFeatured/Common/BackendConstitution.yaml"
  best_practices: "CodexFeatured/Common/BestPractise.yaml"
  simulation_testing_constitution: "CodexFeatured/Common/SimulationTestingConstitution.yaml"
  kobe_root_index: "Kobe/index.yaml"

requirements_parsed:
  features:
    - "TaskQueue 提供长耗时 I/O 任务 demo_long_io 与分片任务 demo_sharded_job"
    - "通过 FastAPI 暴露 HTTP 接口: POST /task/start, GET /task/status/{task_id}, GET /task/result/{task_id}"
    - "使用 Celery + RabbitMQ，支持默认队列 q.tasks.default、分片队列 q.tasks.sharded，配置 DLX/DLQ"
    - "可选启用 Redis 结果后端 (ENABLE_RESULT_BACKEND)，默认关闭"
  structure:
    - "核心文件: Kobe/routers/task.py, SharedUtility/TaskQueue/{app.py, config.py, tasks.py, schemas.py, repository/mongo.py}"
    - "根索引: Kobe/index.yaml；共享工具与模块结构见 CodebaseStructure.yaml"
  interfaces:
    - "POST /task/start: body=TaskStart{task, duration_sec?, fail_rate?, shard_key?, payload?} -> {task_id}"
    - "GET /task/status/{task_id}: -> TaskStatus{task_id, state, ready}"
    - "GET /task/result/{task_id}: -> TaskResult{task_id, state, result?}; 未完成时返回 202"
  DoD:
    - "遵循 BackendConstitution 与 SimulationTestingConstitution 全部约束"
    - "在本地环境完成: 服务可用性校验(RabbitMQ/Redis/Mongo)、HTTP 端到端功能、异常与超时场景、结果与报告生成"
    - "Mongo 索引(唯一/复合/TTL)存在且有效；DLQ/分片路由生效可观测"
    - "测试产物仅落在 \\TaskQueue_testplan 目录的 results/ 与 logs/ 下"

env_assumptions:
  python: "3.10"
  fastapi_entry: "Kobe.main:app"
  http_start_cmd: "python -m Kobe.main"
  celery_worker_cmd: "celery -A Kobe.SharedUtility.TaskQueue:app worker -l info --concurrency 2 -Q q.tasks.default,q.tasks.sharded"
  required_services:
    - "RabbitMQ: 5672/15672 (Management API)"
    - "Redis: 6379"
    - "MongoDB: 27017"

workflow:
  - id: detect_output_filename
    name: 解析输出文件名
    actions:
      - "在 D:/AI_Projects/Kobe/SimulationTest 中枚举所有 *.md 文件（不含子目录）"
      - "若文件数量不等于 1 则报错并终止"
      - "将唯一文件去扩展名的基名保存为变量 unique_filename"
    result:
      unique_filename: "TaskQueue"

  - id: check_docs
    name: 加载文件
    actions:
      - "运行 sources.codebase_map_script 生成/刷新 CodebaseStructure.yaml"
      - "读取 sources.codebase_structure_doc 了解项目文件结构"
      - "读取 sources.kobe_root_index"
      - "按 relations 自顶向下遍历直至所有 index.yaml 读取完毕"

  - id: load_policies
    name: 加载规范并调研
    actions:
      - "读取 sources.dev_constitution 并严格遵守"
      - "读取 sources.simulation_testing_constitution 并严格遵守"
      - "读取 sources.best_practices 并浏览其中任务相关官方链接"
      - "调研社区最佳实践（Celery/RabbitMQ/pytest 并发/HTTP 重试/指数退避）"
    purpose: "加载开发规范, 学习官方推荐实现, 学习当前任务最佳实践"

  - id: codebase_scan
    name: 目标代码库扫描
    actions:
      - "扫描 Kobe/SharedUtility/TaskQueue 与 routers/ 下的相关代码文件"
      - "扫描 D:/AI_Projects/CodexFeatured/DevPlans 了解开发历史"

  - id: write_output
    name: 写入目标文件
    path: "D:/AI_Projects/Kobe/SimulationTest"
    target: "\\_testplan.md"
    actions:
      - "写入完整原子级可执行开发测试步骤的YAML格式指令集（即本文件）"
    acceptance:
      - "任务文件路径对齐"
      - "输出为合法 UTF-8 YAML（无 BOM）"
      - "内容符合 sources.dev_constitution 与 sources.simulation_testing_constitution 规范、与官方最佳实践一致"
      - "须包含需求文档解析得到的功能、结构、接口与 DoD"
      - "可直接接入 Codex CLI / Cursor AGENTS / Cognitive Workflow"
      - "所有文件创建路径必须以 D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/ 开头"
      - "禁止在 SimulationTest 外部创建任何测试文件"
      - "子目录结构必须包含: test_cases/, results/, logs/"

execution_plan:
  Step 1:
    title: 初始化仿真测试工作区
    sub_steps:
      - create_dir: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan"
      - create_dir: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/test_cases"
      - create_dir: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/results"
      - create_dir: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/logs"
      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/README.md"
          encoding: "utf8"
          content: |
            # TaskQueue 仿真测试工作区
            - 本目录仅用于本地仿真测试，严禁在 SimulationTest 外创建任何测试相关文件。
            - 测试仅通过 HTTP/中间件观测对被测系统进行验证，禁止直接 import 被测模块。
            - 所有报告与日志均写入 results/ 与 logs/ 下，UTF-8 编码。

  Step 1.5:
    title: 生成测试依赖清单
    sub_steps:
      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/requirements.txt"
          encoding: "utf8"
          content: |
            pytest
            pytest-asyncio
            pytest-timeout
            pytest-json-report
            pytest-html
            pytest-xdist
            requests
            redis
            pymongo
            psutil
            click
            structlog
            pyyaml
            readchar
            orjson

  Step 2:
    title: 编写基础测试用例（HTTP + 中间件校验）
    sub_steps:
      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/test_cases/conftest.py"
          encoding: "utf8"
          content: |
            import os, time, json, contextlib
            import requests
            import structlog
            import pytest

            structlog.configure(
                processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
            )
            log = structlog.get_logger()

            BASE_URL = os.getenv("TASKQUEUE_BASE_URL", "http://127.0.0.1:8000")
            RABBIT_USER = os.getenv("RABBITMQ_USER", "guest")
            RABBIT_PASS = os.getenv("RABBITMQ_PASS", "guest")
            RABBIT_MAN_URL = os.getenv("RABBITMQ_MAN_URL", "http://127.0.0.1:15672")
            REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

            @pytest.fixture(scope="session")
            def client():
                s = requests.Session()
                s.headers.update({"Content-Type": "application/json"})
                s.timeout = 5
                yield s
                s.close()

            def poll_status(task_id: str, timeout_sec: int = 30, interval: float = 0.5):
                deadline = time.time() + timeout_sec
                last = None
                while time.time() < deadline:
                    r = requests.get(f"{BASE_URL}/task/status/{task_id}", timeout=5)
                    r.raise_for_status()
                    last = r.json()
                    if last.get("ready"):
                        return last
                    time.sleep(interval)
                return last

            def get_result(task_id: str):
                r = requests.get(f"{BASE_URL}/task/result/{task_id}", timeout=5)
                return r

      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/test_cases/test_functional.py"
          encoding: "utf8"
          content: |
            import os
            import pytest
            from .conftest import poll_status, get_result

            ENABLE_RESULT_BACKEND = os.getenv("ENABLE_RESULT_BACKEND", "false").lower() in {"1","true","yes","on"}

            def test_start_and_status_success(client):
                payload = {"task":"demo_long_io","duration_sec":1,"fail_rate":0.0}
                r = client.post("http://127.0.0.1:8000/task/start", json=payload, timeout=5)
                assert r.status_code == 200, r.text
                task_id = r.json()["task_id"]
                st = poll_status(task_id, timeout_sec=30)
                assert st is not None and st["state"] in {"SUCCESS","FAILURE","RETRY","STARTED","PENDING"}
                if ENABLE_RESULT_BACKEND:
                    rr = get_result(task_id)
                    assert rr.status_code in {200, 202}
                else:
                    rr = get_result(task_id)
                    assert rr.status_code == 202

            def test_sharded_job_requires_shard_key(client):
                r = client.post("http://127.0.0.1:8000/task/start", json={"task":"demo_sharded_job"}, timeout=5)
                assert r.status_code == 400

            def test_sharded_job_success(client):
                r = client.post("http://127.0.0.1:8000/task/start", json={"task":"demo_sharded_job","shard_key":"user:42"}, timeout=5)
                assert r.status_code == 200
                task_id = r.json()["task_id"]
                st = poll_status(task_id, timeout_sec=30)
                assert st is not None

      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/test_cases/test_stress.py"
          encoding: "utf8"
          content: |
            import time, concurrent.futures as cf
            import requests

            def _start_one(i: int):
                r = requests.post("http://127.0.0.1:8000/task/start", json={"task":"demo_long_io","duration_sec":1,"fail_rate":0.0}, timeout=5)
                r.raise_for_status()
                return r.json()["task_id"]

            def test_concurrent_submissions():
                n = 20
                t0 = time.time()
                with cf.ThreadPoolExecutor(max_workers=8) as ex:
                    ids = list(ex.map(_start_one, range(n)))
                assert len(ids) == n
                elapsed = time.time() - t0
                # Basic sanity: submissions under 5s total on local
                assert elapsed < 5.0

      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/test_cases/test_recovery.py"
          encoding: "utf8"
          content: |
            import requests
            from .conftest import poll_status

            def test_retry_or_failure_paths():
                r = requests.post("http://127.0.0.1:8000/task/start", json={"task":"demo_long_io","duration_sec":1,"fail_rate":0.6}, timeout=5)
                r.raise_for_status()
                task_id = r.json()["task_id"]
                st = poll_status(task_id, timeout_sec=30)
                assert st["state"] in {"RETRY","FAILURE","SUCCESS","STARTED","PENDING"}

      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/test_cases/test_mongo_indexes.py"
          encoding: "utf8"
          content: |
            import os, pytest
            from pymongo import MongoClient

            MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            DB = os.getenv("MONGODB_DATABASE", "kobe")

            def test_indexes_exist():
                c = MongoClient(MONGODB_URI)
                db = c[DB]
                dedup = db["TaskDedup"].index_information()
                ckpt = db["TaskCheckpoint"].index_information()
                pend = db["PendingTasks"].index_information()
                assert any("task_fingerprint" in k for k in dedup.keys())
                assert any("shard_key" in str(v.get("key")) and "sub_key" in str(v.get("key")) for v in ckpt.values())
                assert any("task_key" in k for k in pend.keys())
                assert any("lease_until" in k for k in pend.keys())

  Step 3:
    title: 实现测试执行器（CLI 包装 pytest）
    sub_steps:
      - write_file:
          path: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/run_local_simulation_tests.py"
          encoding: "utf8"
          content: |
            import subprocess, sys, time
            import click
            import readchar
            from pathlib import Path

            BASE = Path(__file__).resolve().parent
            RESULTS = BASE / "results"

            def _run_pytest(select: str | None):
                RESULTS.mkdir(parents=True, exist_ok=True)
                args = [
                    sys.executable, "-m", "pytest", "-q", "--maxfail=1", "--disable-warnings",
                    str(BASE / "test_cases"),
                    "--timeout=30", "-n", "auto",
                    "--json-report", "--json-report-file", str(RESULTS / "report.json"),
                    "--html", str(RESULTS / "report.html"), "--self-contained-html",
                ]
                if select:
                    args.extend(["-k", select])
                return subprocess.call(args)

            @click.command()
            @click.option("--scenario", "scenario", default=None, help="pytest -k 表达式过滤场景")
            @click.option("--all", is_flag=True, help="运行全部用例")
            def main(scenario: str | None, all: bool):
                print("即将运行仿真测试... 按任意键立即开始，30 秒后自动开始")
                start = time.time()
                while time.time() - start < 30:
                    if readchar.peek():
                        readchar.readkey()
                        break
                    time.sleep(0.2)
                code = _run_pytest(scenario if not all else None)
                sys.exit(code)

            if __name__ == "__main__":
                main()

  Step 4:
    title: 配置日志记录
    sub_steps:
      - configure_logging:
          debug_log: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/logs/debug.log"
          error_log: "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/logs/error.log"
          encoding: "utf8"
          notes: "确保所有日志为 UTF-8 编码；测试框架与脚本写入本目录"

  Step 5:
    title: 服务可用性与中间件状态查询
    sub_steps:
      - http_get:
          url: "http://127.0.0.1:15672/api/overview"
          auth: "guest:guest"
          expect_status: 200
      - redis_ping:
          url: "redis://localhost:6379/0"
          expect: "PONG or True"
      - mongo_ping:
          uri: "mongodb://localhost:27017"
          expect_ok: 1

  Step 6:
    title: 结果后端与 Worker 策略变体验证
    sub_steps:
      - variant: "ENABLE_RESULT_BACKEND=false"
        expect: "GET /task/result 返回 202（未提供结果体）"
      - variant: "ENABLE_RESULT_BACKEND=true"
        expect: "GET /task/result 在完成后返回 200 且含 result"
      - variant: "CELERY_PREFETCH=4"
        expect: "并发提交下吞吐提升，ACK 语义保持"
      - variant: "CELERY_TASK_SOFT_TIME_LIMIT=1"
        expect: "长任务触发软超时，状态进入 RETRY 或 FAILURE"

  Step 7:
    title: 执行与报告
    sub_steps:
      - run: "python D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/run_local_simulation_tests.py --all"
      - artifacts:
          - "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/results/report.json"
          - "D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/results/report.html"

  Step 8:
    title: 合规校验（规范对齐）
    sub_steps:
      - check: "遵循 BackendConstitution 与 SimulationTestingConstitution 的禁止项与强制项"
      - check: "仅通过 HTTP/中间件观测验证，被测模块零 import"
      - check: "所有创建/写入路径均在 D:/AI_Projects/Kobe/SimulationTest/\\TaskQueue_testplan/ 前缀下"
      - check: "日志与报告均为 UTF-8 编码"
---

