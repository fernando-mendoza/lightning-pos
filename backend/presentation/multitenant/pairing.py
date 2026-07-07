"""Rutas de pairing y terminales (/api/v2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from application.multitenant.pairing import (
    create_pairing_code,
    list_terminals,
    redeem_pairing,
    revoke_terminal,
)
from config import settings
from infrastructure.db.base import get_session
from infrastructure.security.rate_limit import rate_limit
from infrastructure.db.models import TerminalRole
from presentation.multitenant.deps import (
    CurrentUser,
    TerminalContext,
    get_terminal_context,
    require_manager,
)

router = APIRouter()


class PairingCodeIn(BaseModel):
    name: str
    role: Literal["manager", "cashier"] = "cashier"


class PairingPayload(BaseModel):
    server_url: str
    code: str


class PairingCodeOut(BaseModel):
    code: str
    expires_at: datetime
    # Contenido a codificar en el QR (la app lo escanea).
    pairing_payload: PairingPayload


class RedeemIn(BaseModel):
    code: str
    device_name: str | None = None


class TerminalInfo(BaseModel):
    id: str
    name: str
    role: str


class TenantInfo(BaseModel):
    id: str
    name: str


class RedeemOut(BaseModel):
    device_token: str
    terminal: TerminalInfo
    tenant: TenantInfo


class TerminalOut(BaseModel):
    id: str
    name: str
    role: str
    status: str
    created_at: datetime


# ---- admin (JWT usuario + X-Tenant-Id, requiere manager/owner) ----
@router.post("/pairing-codes", response_model=PairingCodeOut, status_code=201)
async def create_code(
    body: PairingCodeIn,
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    code, pc = await create_pairing_code(
        session,
        tenant_id=cu.tenant.id,
        name=body.name,
        role=TerminalRole(body.role),
        created_by=cu.user.id,
        ttl_seconds=settings.pairing_code_ttl_seconds,
    )
    return PairingCodeOut(
        code=code,
        expires_at=pc.expires_at,
        pairing_payload=PairingPayload(server_url=settings.public_base_url, code=code),
    )


@router.get("/terminals", response_model=list[TerminalOut])
async def terminals(
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    ts = await list_terminals(session, tenant_id=cu.tenant.id)
    return [
        TerminalOut(
            id=str(t.id),
            name=t.name,
            role=t.role.value,
            status=t.status.value,
            created_at=t.created_at,
        )
        for t in ts
    ]


@router.post("/terminals/{terminal_id}/revoke")
async def revoke(
    terminal_id: uuid.UUID,
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    ok = await revoke_terminal(session, tenant_id=cu.tenant.id, terminal_id=terminal_id)
    if not ok:
        raise HTTPException(status_code=404, detail="terminal_not_found")
    return {"status": "revoked"}


# ---- público (la app canjea el código del QR) ----
@router.post(
    "/pairing/redeem",
    response_model=RedeemOut,
    dependencies=[Depends(rate_limit("redeem", settings.rate_limit_redeem))],
)
async def redeem(body: RedeemIn, session: AsyncSession = Depends(get_session)):
    res = await redeem_pairing(session, code=body.code, device_name=body.device_name)
    if res is None:
        raise HTTPException(status_code=400, detail="pairing_invalid_or_expired")
    token, terminal, tenant = res
    return RedeemOut(
        device_token=token,
        terminal=TerminalInfo(id=str(terminal.id), name=terminal.name, role=terminal.role.value),
        tenant=TenantInfo(id=str(tenant.id), name=tenant.name),
    )


# ---- terminal (device token) ----
@router.get("/terminal/me")
async def terminal_me(tc: TerminalContext = Depends(get_terminal_context)):
    return {
        "terminal_id": str(tc.terminal.id),
        "name": tc.terminal.name,
        "role": tc.role.value,
        "tenant_id": str(tc.tenant_id),
    }
