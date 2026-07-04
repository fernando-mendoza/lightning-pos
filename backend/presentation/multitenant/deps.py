"""Dependencies FastAPI del API multi-tenant (/api/v2).

Dos modos de auth:
- **JWT de usuario** (dashboard/admin): `Authorization: Bearer <jwt>` + `X-Tenant-Id`.
- **Device token** (terminal/app): `Authorization: Bearer <device_token>`.
El `tenant_id` SIEMPRE se deriva del token/membership; el cliente nunca lo impone.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.base import get_session
from infrastructure.db.models import (
    DeviceToken,
    Membership,
    Role,
    Tenant,
    Terminal,
    TerminalRole,
    TerminalStatus,
    User,
)
from infrastructure.providers import wallet_provider
from infrastructure.security import jwt_tokens
from infrastructure.security.tokens import hash_token


def get_wallet():
    return wallet_provider


def _bearer(authorization: str | None) -> str:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing_token")
    return token


async def get_authenticated_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Solo valida el JWT de usuario (para /me y endpoints no ligados a un tenant)."""
    token = _bearer(authorization)
    try:
        payload = jwt_tokens.decode_token(token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid_token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="invalid_token_type")
    user = await session.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="user_not_found")
    return user


@dataclass
class CurrentUser:
    user: User
    membership: Membership
    tenant: Tenant


async def get_current_user(
    x_tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
    user: User = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="missing_tenant")
    try:
        tid = uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="bad_tenant_id")
    membership = (
        await session.execute(
            select(Membership).where(
                Membership.user_id == user.id, Membership.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="not_a_member")
    tenant = await session.get(Tenant, tid)
    return CurrentUser(user=user, membership=membership, tenant=tenant)


def require_manager(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if cu.membership.role not in (Role.owner, Role.manager):
        raise HTTPException(status_code=403, detail="requires_manager")
    return cu


@dataclass
class TerminalContext:
    terminal: Terminal
    tenant_id: uuid.UUID
    role: TerminalRole


async def get_terminal_context(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> TerminalContext:
    token = _bearer(authorization)
    dt = (
        await session.execute(
            select(DeviceToken).where(DeviceToken.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if dt is None or dt.revoked_at is not None or (dt.expires_at and dt.expires_at < now):
        raise HTTPException(status_code=401, detail="invalid_device_token")
    terminal = await session.get(Terminal, dt.terminal_id)
    if terminal is None or terminal.status != TerminalStatus.active:
        raise HTTPException(status_code=401, detail="terminal_revoked")
    return TerminalContext(
        terminal=terminal, tenant_id=terminal.tenant_id, role=terminal.role
    )
