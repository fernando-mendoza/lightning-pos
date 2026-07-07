"""Rutas admin (/api/v2): change-password, miembros, tenant, rename de terminal, reportes."""

from __future__ import annotations

import uuid
from datetime import date, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.multitenant.accounts import AccountError
from application.multitenant.admin import (
    add_member,
    change_password,
    list_members,
    remove_member,
    rename_tenant,
    rename_terminal,
    sales_summary,
)
from infrastructure.db.models import Role, User
from infrastructure.db.base import get_session
from presentation.multitenant.deps import (
    CurrentUser,
    get_authenticated_user,
    get_current_user,
    require_manager,
)

router = APIRouter()


def _require_owner(cu: CurrentUser) -> None:
    if cu.membership.role != Role.owner:
        raise HTTPException(status_code=403, detail="requires_owner")


# ---- password ----
class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.post("/auth/change-password", status_code=204)
async def change_password_route(
    body: ChangePasswordIn,
    user: User = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
):
    ok = await change_password(
        session,
        user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="invalid_current_password")


# ---- miembros ----
class MemberOut(BaseModel):
    user_id: str
    email: str
    name: str | None
    role: str


class MemberIn(BaseModel):
    email: EmailStr
    # Requerido solo si el email no existe aún como usuario.
    password: str | None = Field(default=None, min_length=8)
    name: str | None = None
    role: Literal["manager", "cashier"] = "cashier"


@router.get("/members", response_model=list[MemberOut])
async def members_list(
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    rows = await list_members(session, tenant_id=cu.tenant.id)
    return [
        MemberOut(user_id=str(u.id), email=u.email, name=u.name, role=m.role.value)
        for (m, u) in rows
    ]


@router.post("/members", response_model=MemberOut, status_code=201)
async def members_add(
    body: MemberIn,
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    # Solo el owner puede crear managers; un manager puede crear cashiers.
    if body.role == "manager":
        _require_owner(cu)
    try:
        membership, user, _created = await add_member(
            session,
            tenant_id=cu.tenant.id,
            email=body.email,
            password=body.password,
            name=body.name,
            role=Role(body.role),
        )
    except AccountError as e:
        code = 409 if str(e) == "already_member" else 400
        raise HTTPException(status_code=code, detail=str(e))
    return MemberOut(
        user_id=str(user.id), email=user.email, name=user.name, role=membership.role.value
    )


@router.delete("/members/{user_id}", status_code=204)
async def members_remove(
    user_id: uuid.UUID,
    cu: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_owner(cu)
    try:
        ok = await remove_member(session, tenant_id=cu.tenant.id, user_id=user_id)
    except AccountError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="member_not_found")


# ---- tenant ----
class TenantPatch(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TenantOut(BaseModel):
    id: str
    name: str


@router.patch("/tenants/me", response_model=TenantOut)
async def tenant_update(
    body: TenantPatch,
    cu: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_owner(cu)
    tenant = await rename_tenant(session, tenant_id=cu.tenant.id, name=body.name)
    return TenantOut(id=str(tenant.id), name=tenant.name)


# ---- terminales ----
class TerminalPatch(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@router.patch("/terminals/{terminal_id}")
async def terminal_update(
    terminal_id: uuid.UUID,
    body: TerminalPatch,
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    terminal = await rename_terminal(
        session, tenant_id=cu.tenant.id, terminal_id=terminal_id, name=body.name
    )
    if terminal is None:
        raise HTTPException(status_code=404, detail="terminal_not_found")
    return {"id": str(terminal.id), "name": terminal.name, "role": terminal.role.value}


# ---- reportes ----
@router.get("/reports/summary")
async def reports_summary(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    """Ventas pagadas agregadas por día (UTC) y por terminal. Default: últimos 30 días."""
    from datetime import datetime

    today = datetime.now(timezone.utc).date()
    date_to = date_to or today
    date_from = date_from or (date_to - timedelta(days=29))
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="invalid_range")
    return await sales_summary(
        session, tenant_id=cu.tenant.id, date_from=date_from, date_to=date_to
    )
