from __future__ import annotations

from importlib import import_module

_module = import_module("src.one_off.__main__")


def main() -> None:
    _module.main()


if __name__ == "__main__":
    main()
