"""Compatibility shim exposing python_multipart for Starlette."""

from multipart import __all__  # type: ignore[attr-defined]
from multipart import *  # type: ignore  # noqa: F401,F403
from multipart.multipart import parse_options_header  # noqa: F401

