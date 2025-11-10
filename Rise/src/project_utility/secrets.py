from __future__ import annotations

"""Helpers for encrypting, decrypting, and masking sensitive values."""

import base64
import os
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

__all__ = [
    "SecretBox",
    "get_secret_box",
    "mask_secret",
]


class SecretBox:
    """Lightweight wrapper over Fernet for symmetric secret management."""

    def __init__(self, key_material: str) -> None:
        self._fernet = Fernet(self._derive_key(key_material))

    @staticmethod
    def _derive_key(raw: str) -> bytes:
        """Accept either Fernet-compatible base64 key or derive one from raw text."""

        try:
            decoded = base64.urlsafe_b64decode(raw)
        except Exception:
            from hashlib import sha256

            digest = sha256(raw.encode("utf-8")).digest()
            return base64.urlsafe_b64encode(digest)
        if len(decoded) == 32:
            return base64.urlsafe_b64encode(decoded)
        return base64.urlsafe_b64encode(decoded[:32].ljust(32, b"\0"))

    def encrypt(self, value: str) -> str:
        token = self._fernet.encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        try:
            decrypted = self._fernet.decrypt(token.encode("utf-8"))
        except InvalidToken as exc:
            raise ValueError("invalid secret token") from exc
        return decrypted.decode("utf-8")


@lru_cache(maxsize=4)
def get_secret_box(env_var: str) -> SecretBox:
    key = os.getenv(env_var)
    if not key:
        raise RuntimeError(f"missing required secret key environment variable '{env_var}'")
    return SecretBox(key)


def mask_secret(value: Optional[str], *, head: int = 6, tail: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= head + tail:
        return "*" * len(value)
    return f"{value[:head]}****{value[-tail:]}"
