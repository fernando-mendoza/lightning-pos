"""Qué puede cobrar realmente un tenant, hoy.

Existe porque la app ofrecía cobro con bitcoin de forma incondicional. Cuando el proveedor
dejó de existir, el cajero recibía "Algo salió mal" en cada intento — y el comerciante no
tenía cómo saber que el problema no era la app. Un mensaje de error mejor no alcanza: lo
correcto es **no ofrecer lo que no se puede cumplir**.

La regla en sí es pura y vive en `domain.capabilities`; acá sólo se resuelve el estado.
El efectivo siempre está disponible: no depende de nadie externo.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from domain.capabilities import CASH, LIGHTNING, wallet_is_usable
from infrastructure.db.models import TenantWallet

__all__ = ["CASH", "LIGHTNING", "tenant_payment_methods", "lightning_available"]


async def tenant_payment_methods(session: AsyncSession, tenant_id: uuid.UUID) -> list[str]:
    methods = [CASH]
    if not settings.lightning_enabled:
        return methods
    tw = (
        await session.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if tw is not None and wallet_is_usable(
        tw.provider.value if tw.provider else None, tw.lnbits_wallet_id, tw.invoice_key_enc
    ):
        methods.append(LIGHTNING)
    return methods


async def lightning_available(session: AsyncSession, tenant_id: uuid.UUID) -> bool:
    return LIGHTNING in await tenant_payment_methods(session, tenant_id)
