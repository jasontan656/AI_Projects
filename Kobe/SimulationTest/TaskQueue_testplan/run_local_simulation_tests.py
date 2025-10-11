# -*- coding: utf-8 -*-
import subprocess
import sys
import time
from pathlib import Path

import click


BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
TESTS = BASE / "test_cases"


def _run_pytest(select: str | None):
    RESULTS.mkdir(parents=True, exist_ok=True)
    args = [
        sys.executable,
        "-m",
        "pytest",
        str(TESTS),
        "-q",
        "--disable-warnings",
        "--maxfail=1",
        "--timeout=30",
        "-n",
        "auto",
        "--json-report",
        "--json-report-file",
        str(RESULTS / "report.json"),
        "--html",
        str(RESULTS / "report.html"),
        "--self-contained-html",
    ]
    if select:
        args.extend(["-k", select])
    return subprocess.call(args)


@click.command()
@click.option("--scenario", "scenario", default=None, help="pytest -k 过滤表达式")
@click.option("--all", "run_all", is_flag=True, help="运行全部测试（忽略 -k）")
def main(scenario: str | None, run_all: bool):
    click.echo("即将运行模拟测试… 可在5秒内按回车提前开始")
    start = time.time()
    while time.time() - start < 5:
        try:
            if click.getchar(echo=False):
                break
        except Exception:
            # 非交互终端时直接继续
            break
        time.sleep(0.2)
    code = _run_pytest(None if run_all else scenario)
    sys.exit(code)


if __name__ == "__main__":
    main()

