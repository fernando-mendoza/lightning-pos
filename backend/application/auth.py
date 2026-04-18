import hashlib
import time

import jwt

from config import settings
from infrastructure.db.connection import get_db

_JWT_ALGO = "HS256"


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def issue_token() -> str:
    now = int(time.time())
    payload = {
        "sub": "pos",
        "iat": now,
        "exp": now + settings.jwt_ttl_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGO)


def is_valid_token(token: str) -> bool:
    if not token:
        return False
    try:
        jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGO])
        return True
    except jwt.InvalidTokenError:
        return False


async def get_pin_hash() -> str | None:
    db = await get_db()
    cursor = await db.execute("SELECT value FROM settings WHERE key = 'pin_hash'")
    row = await cursor.fetchone()
    return row["value"] if row else None


async def set_pin(pin: str) -> None:
    db = await get_db()
    h = hash_pin(pin)
    await db.execute(
        """INSERT INTO settings (key, value) VALUES ('pin_hash', ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
        (h,),
    )
    await db.commit()


async def verify_pin(pin: str) -> str | None:
    stored = await get_pin_hash()
    if not stored:
        return None
    if hash_pin(pin) != stored:
        return None
    return issue_token()


async def is_pin_set() -> bool:
    return await get_pin_hash() is not None


async def check_pin_rate_limit() -> tuple[bool, int]:
    """Sliding window: rechaza si hubo demasiados intentos fallidos recientes.
    Devuelve (allowed, retry_after_seconds).
    """
    now = int(time.time())
    cutoff = now - settings.pin_lockout_window_seconds
    db = await get_db()
    await db.execute("DELETE FROM auth_attempts WHERE attempted_at < ?", (cutoff,))
    cursor = await db.execute(
        "SELECT COUNT(*) AS c, MIN(attempted_at) AS m FROM auth_attempts WHERE success = 0"
    )
    row = await cursor.fetchone()
    await db.commit()
    count = row["c"] if row else 0
    if count >= settings.max_pin_attempts:
        oldest = row["m"]
        retry_after = max(1, oldest + settings.pin_lockout_window_seconds - now)
        return False, retry_after
    return True, 0


async def record_pin_attempt(success: bool) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO auth_attempts (attempted_at, success) VALUES (?, ?)",
        (int(time.time()), 1 if success else 0),
    )
    if success:
        # Limpiar fallos previos al loguear con exito
        await db.execute("DELETE FROM auth_attempts WHERE success = 0")
    await db.commit()
