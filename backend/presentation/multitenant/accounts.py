"""Rutas de cuentas (/api/v2): registro, login, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.multitenant.accounts import (
    AccountError,
    authenticate,
    list_memberships,
    register_account,
)
from infrastructure.db.base import get_session
from infrastructure.db.models import User
from infrastructure.security.jwt_tokens import create_access_token, create_refresh_token
from presentation.multitenant.deps import get_authenticated_user, get_wallet

router = APIRouter()


class MembershipOut(BaseModel):
    tenant_id: str
    tenant_name: str
    role: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None
    tenant_name: str = Field(min_length=1)


class AuthOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    tenant_id: str
    tenant_name: str
    role: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class LoginOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    memberships: list[MembershipOut]


class MeOut(BaseModel):
    user_id: str
    email: str
    name: str | None
    memberships: list[MembershipOut]


@router.post("/auth/register", response_model=AuthOut, status_code=201)
async def register(
    body: RegisterIn,
    session: AsyncSession = Depends(get_session),
    wallet=Depends(get_wallet),
):
    try:
        user, tenant = await register_account(
            session,
            wallet,
            email=body.email,
            password=body.password,
            name=body.name,
            tenant_name=body.tenant_name,
        )
    except AccountError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return AuthOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        role="owner",
    )


@router.post("/auth/login", response_model=LoginOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)):
    user = await authenticate(session, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    mems = await list_memberships(session, user.id)
    return LoginOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        memberships=[
            MembershipOut(tenant_id=str(t.id), tenant_name=t.name, role=m.role.value)
            for (m, t) in mems
        ],
    )


@router.get("/me", response_model=MeOut)
async def me(
    user: User = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_session),
):
    mems = await list_memberships(session, user.id)
    return MeOut(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        memberships=[
            MembershipOut(tenant_id=str(t.id), tenant_name=t.name, role=m.role.value)
            for (m, t) in mems
        ],
    )
