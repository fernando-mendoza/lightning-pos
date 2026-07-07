"""Use cases de pairing y terminales (device authorization por QR)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    DeviceToken,
    PairingCode,
    Tenant,
    Terminal,
    TerminalRole,
    TerminalStatus,
)
from infrastructure.security.tokens import (
    generate_device_token,
    generate_pairing_code,
    hash_token,
)


async def create_pairing_code(
    session: AsyncSession,
    *,
    tenant_id,
    name: str,
    role: TerminalRole,
    created_by,
    ttl_seconds: int,
) -> tuple[str, PairingCode]:
    """Devuelve (código en claro, registro). El código solo se guarda hasheado."""
    code = generate_pairing_code()
    pc = PairingCode(
        tenant_id=tenant_id,
        code_hash=hash_token(code),
        role=role,
        name=name,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        created_by=created_by,
    )
    session.add(pc)
    await session.commit()
    return code, pc


async def redeem_pairing(
    session: AsyncSession, *, code: str, device_name: str | None = None
) -> tuple[str, Terminal, Tenant] | None:
    """Canjea un código válido → crea Terminal + DeviceToken. Devuelve (token, terminal, tenant)."""
    pc = (
        await session.execute(
            select(PairingCode).where(PairingCode.code_hash == hash_token(code))
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if pc is None or pc.consumed_at is not None or pc.expires_at < now:
        return None

    terminal = Terminal(
        tenant_id=pc.tenant_id,
        # El nombre lo decide el manager al crear el pairing code; device_name
        # (p.ej. "ios") es solo fallback si el código se creó sin nombre.
        name=pc.name or device_name or "Terminal",
        role=pc.role,
        status=TerminalStatus.active,
        created_by=pc.created_by,
        last_seen_at=now,
    )
    session.add(terminal)
    await session.flush()

    token = generate_device_token()
    session.add(DeviceToken(terminal_id=terminal.id, token_hash=hash_token(token)))

    pc.consumed_at = now
    pc.terminal_id = terminal.id
    await session.commit()

    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == pc.tenant_id))
    ).scalar_one()
    return token, terminal, tenant


async def list_terminals(session: AsyncSession, *, tenant_id) -> list[Terminal]:
    return list(
        (
            await session.execute(
                select(Terminal)
                .where(Terminal.tenant_id == tenant_id)
                .order_by(Terminal.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def revoke_terminal(session: AsyncSession, *, tenant_id, terminal_id) -> bool:
    terminal = (
        await session.execute(
            select(Terminal).where(
                Terminal.id == terminal_id, Terminal.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if terminal is None:
        return False
    terminal.status = TerminalStatus.revoked
    await session.execute(
        update(DeviceToken)
        .where(DeviceToken.terminal_id == terminal_id, DeviceToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return True
