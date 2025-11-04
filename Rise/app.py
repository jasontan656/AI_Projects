from __future__ import annotations

import argparse

from interface_entry.bootstrap.app import app, CLI_DESCRIPTION, configure_arg_parser, handle_cli


def main() -> None:
    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)
    configure_arg_parser(parser)
    args = parser.parse_args()
    handle_cli(args)


if __name__ == "__main__":
    main()
