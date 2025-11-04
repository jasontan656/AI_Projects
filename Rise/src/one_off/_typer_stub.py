from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


class BadParameter(Exception):
    """Raised when CLI arguments are invalid."""


@dataclass
class Argument:
    default: Optional[Any] = None
    nargs: Optional[int] = None
    help: str | None = None


class Typer:
    def __init__(self, *, help: str | None = None) -> None:
        self._commands: Dict[str, Callable[..., Any]] = {}
        self._help = help or "One-off CLI"

    def command(self, name: str | None = None, *, help: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            command_name = name or func.__name__.replace("_", "-")
            self._commands[command_name] = func
            return func

        return decorator

    def __call__(self, args: Optional[List[str]] = None, *, prog_name: str | None = None) -> None:
        argv = list(sys.argv[1:] if args is None else args)
        if not argv or argv[0] in {"-h", "--help"}:
            self._print_help(prog_name)
            return
        command = argv.pop(0)
        func = self._commands.get(command)
        if func is None:
            raise BadParameter(f"Unknown command '{command}'")
        self._invoke(func, argv)

    def _invoke(self, func: Callable[..., Any], argv: List[str]) -> None:
        signature = inspect.signature(func)
        params = list(signature.parameters.values())
        if not params:
            func()
            return
        param = params[0]
        default = param.default
        if isinstance(default, Argument) and default.nargs == -1:
            func(argv)
            return
        if len(params) == 1:
            if isinstance(default, Argument):
                if not argv and default.default is None:
                    raise BadParameter("Missing argument")
                value = argv if default.nargs == -1 else (argv[0] if argv else default.default)
                func(value)
            else:
                if not argv:
                    raise BadParameter("Missing argument")
                func(argv[0])
            return
        raise RuntimeError("Unsupported command signature for stub Typer")

    def _print_help(self, prog_name: str | None) -> None:
        prog = prog_name or "one_off"
        print(f"Usage: {prog} <command> [ARGS]\n")
        print(self._help)
        print("\nAvailable commands:")
        for name, func in self._commands.items():
            doc = (func.__doc__ or "").strip()
            print(f"  {name:<25} {doc}")


def echo(message: str) -> None:
    print(message)


__all__ = ["Typer", "Argument", "BadParameter", "echo"]
