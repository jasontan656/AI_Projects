from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, List
import re
from datetime import datetime


def _json_dump(data: Any, path: Path, ensure_ascii: bool = False) -> None:
    try:
        import orjson  # type: ignore

        def _default(obj: Any) -> Any:
            # pydantic models have model_dump
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            raise TypeError

        payload = orjson.dumps(data, default=_default, option=orjson.OPT_INDENT_2)
        path.write_bytes(payload)
        return
    except Exception:
        pass

    def _default(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return str(obj)

    text = json.dumps(data, default=_default, ensure_ascii=ensure_ascii, indent=2)
    path.write_text(text, encoding="utf-8")


DEFAULT_INPUT_DIR = Path(r"D:\AI_Projects\TelegramChatHistory\Original")
DEFAULT_OUTPUT_DIR = Path(r"D:\AI_Projects\TelegramChatHistory\Workspace")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m Kobe.TelegramCuration",
        description="TelegramCuration CLI：解析 Telegram 导出（HTML/JSON/目录）为结构化消息",
    )
    p.add_argument(
        "--path",
        "-p",
        required=False,
        help=(
            "导出文件路径或目录；留空则使用固定默认目录: "
            f"{DEFAULT_INPUT_DIR}（支持 result.json / messages*.json / .html）"
        ),
    )
    p.add_argument("--chat-id", "-c", required=True, help="频道/群标识，如 @channel1")
    p.add_argument("--since", help="起始日期 YYYY-MM-DD，可选")
    p.add_argument("--until", help="结束日期 YYYY-MM-DD，可选")
    p.add_argument(
        "--save-json",
        help=(
            "将解析结果保存为 JSON 文件路径；留空则保存到固定默认目录: "
            f"{DEFAULT_OUTPUT_DIR} 下，以 chat_id 和时间戳命名"
        ),
    )
    p.add_argument("--limit", "-n", type=int, default=3, help="控制台预览前 N 条，默认 3")
    p.add_argument("--quiet", "-q", action="store_true", help="安静模式，仅输出必要信息")
    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        from .services import parse_telegram_export
    except Exception as e:  # noqa: BLE001
        print(f"导入失败：{e}", file=sys.stderr)
        return 1

    async def _run() -> int:
        # 计算实际输入/输出路径
        in_path = Path(args.path) if args.path else DEFAULT_INPUT_DIR
        if not in_path.exists():
            print(f"[ERROR] 输入路径不存在：{in_path}", file=sys.stderr)
            return 2

        if args.save_json:
            out_path = Path(args.save_json)
        else:
            # 默认输出到固定目录（Workspace）
            DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            safe_chat = re.sub(r"[^A-Za-z0-9_.-]+", "_", args.chat_id.lstrip("@")) or "chat"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = DEFAULT_OUTPUT_DIR / f"{safe_chat}_{ts}.json"

        msgs = await parse_telegram_export(str(in_path), chat_id=args.chat_id, since=args.since, until=args.until)
        if not args.quiet:
            print(f"解析完成：{len(msgs)} 条消息")
            print(f"输入：{in_path}")
            for i, m in enumerate(msgs[: max(0, args.limit) ]):
                print(f"[样本 {i+1}]", getattr(m, "model_dump", lambda: m)())
        # 保存输出
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _json_dump(msgs, out_path)
        if not args.quiet:
            print(f"已保存：{out_path}")
        return 0

    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"运行失败：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
