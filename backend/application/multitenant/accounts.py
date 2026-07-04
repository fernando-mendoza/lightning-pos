"""Use cases de cuentas: registro (usuario + tenant + wallet), login, memberships."""

from __future__ import annotations

import re
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ports.wallet_provider import WalletProvider
from infrastructure.db.models import (
    Membership,
    Role,
    Tenant,
    TenantWallet,
    User,
    WalletProviderKind,
)
from infrastructure.security import crypto
from infrastructure.security.passwords import hash_password, verify_password


class AccountError(Exception):
    """Error de negocio (ej. email_exists)."""


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "tenant"


async def _unique_slug(session: AsyncSession, base: str) -> str:
    slug = base
    while (await session.execute(select(Tenant.id).where(Tenant.slug == slug))).first():
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


async def register_account(
    session: AsyncSession,
    wallet: WalletProvider,
    *,
    email: str,
    password: str,
    name: str | None,
    tenant_name: str,
) -> tuple[User, Tenant]:
    """Crea usuario + tenant (owner) + provisiona wallet LNbits. Atómico."""
    email = email.strip().lower()
    if (await session.execute(select(User.id).where(User.email == email))).first():
        raise AccountError("email_exists")

    user = User(email=email, password_hash=hash_password(password), name=name)
    session.add(user)
    await session.flush()

    tenant = Tenant(name=tenant_name, slug=await _unique_slug(session, _slugify(tenant_name)))
    session.add(tenant)
    await session.flush()

    session.add(Membership(tenant_id=tenant.id, user_id=user.id, role=Role.owner))

    # Provisiona wallet del tenant (LNbits o fake) y guarda las llaves encriptadas.
    provisioned = await wallet.provision_wallet(name=tenant.slug)
    session.add(
        TenantWallet(
            tenant_id=tenant.id,
            provider=WalletProviderKind.lnbits,
            lnbits_user_id=provisioned.provider_user_id,
            lnbits_wallet_id=provisioned.wallet_id,
            invoice_key_enc=crypto.encrypt(provisioned.invoice_key),
            admin_key_enc=(
                crypto.encrypt(provisioned.admin_key) if provisioned.admin_key else None
            ),
        )
    )
    await session.commit()
    return user, tenant


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    email = email.strip().lower()
    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        return None
    return user


async def list_memberships(session: AsyncSession, user_id) -> list[tuple[Membership, Tenant]]:
    rows = (
        await session.execute(
            select(Membership, Tenant)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .where(Membership.user_id == user_id)
        )
    ).all()
    return [(m, t) for (m, t) in rows]
