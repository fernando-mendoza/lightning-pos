"""JWT de cuentas de usuario (distinto del JWT de sesión PIN legacy)."""

from __future__ import annotations

import time

import jwt

from config import settings

ALGO = "HS256"


def create_access_token(user_id: str, ttl_seconds: int = 3600) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "type": "access", "iat": now, "exp": now + ttl_seconds}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def create_refresh_token(user_id: str, ttl_seconds: int = 60 * 60 * 24 * 30) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "type": "refresh", "iat": now, "exp": now + ttl_seconds}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_token(token: str) -> dict:
    """Lanza jwt.InvalidTokenError (o subclases) si es inválido/expirado."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
