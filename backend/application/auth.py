import hashlib
import secrets

from infrastructure.db.connection import get_db

# In-memory token store (MVP — tokens survive until server restart)
_active_tokens: set[str] = set()


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def is_valid_token(token: str) -> bool:
    return token in _active_tokens


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
    token = secrets.token_hex(32)
    _active_tokens.add(token)
    return token


async def is_pin_set() -> bool:
    return await get_pin_hash() is not None
