"""Generación y hashing de tokens opacos (device tokens, pairing codes).

Los tokens/códigos se guardan SIEMPRE hasheados (sha256) en la DB; el valor en claro
solo se devuelve una vez al cliente.
"""

from __future__ import annotations

import hashlib
import secrets


def generate_device_token() -> str:
    return secrets.token_urlsafe(48)


def generate_pairing_code() -> str:
    return secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
