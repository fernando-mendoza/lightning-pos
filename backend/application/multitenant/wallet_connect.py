"""Alta de wallet BYO vía NWC: el comercio trae su cadena, nosotros nunca los fondos.

Reemplaza a la provisión para estos tenants. No hay "cuenta creada en un proveedor": hay una
credencial revocable que el comercio corta desde SU wallet cuando quiera. El upsert pisa la
wallet anterior a propósito — conectar una wallet nueva ES el gesto de reemplazo, y guardar
dos credenciales activas sería mentirle al comercio sobre por dónde entra su dinero.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from infrastructure.db.models import TenantWallet, WalletProviderKind
from infrastructure.nwc.uri import NWCUriError, parse_nwc_uri
from infrastructure.security import crypto


class WalletConnectError(Exception):
    """Cadena inválida; el mensaje es mostrable al usuario."""


# Marcador que guarda el tenant cuando cobra por el sidecar de Lexe. NO es un secreto: la
# credencial vive en el entorno del sidecar (config de proceso), no en nuestra base. Eso
# hace explícita la limitación: TODOS los tenants `lexe` cobran contra ESA wallet.
LEXE_MARKER = "lexe-sidecar:default"


async def connect_lexe_wallet(session: AsyncSession, *, tenant_id: uuid.UUID) -> TenantWallet:
    if not settings.lexe_sidecar_url:
        raise WalletConnectError("no hay sidecar de Lexe configurado en este backend")
    tw = (
        await session.execute(select(TenantWallet).where(TenantWallet.tenant_id == tenant_id))
    ).scalar_one_or_none()
    enc = crypto.encrypt(LEXE_MARKER)
    if tw is None:
        tw = TenantWallet(
            tenant_id=tenant_id, provider=WalletProviderKind.lexe, invoice_key_enc=enc
        )
        session.add(tw)
    else:
        tw.provider = WalletProviderKind.lexe
        tw.invoice_key_enc = enc
        # Se limpian los restos de LNbits: dejarlos haría que un diagnóstico futuro crea que
        # este tenant todavía cuelga de una instancia que ya no existe.
        tw.lnbits_user_id = None
        tw.lnbits_wallet_id = None
        tw.admin_key_enc = None
    await session.commit()
    await session.refresh(tw)
    return tw


async def connect_nwc_wallet(
    session: AsyncSession, *, tenant_id: uuid.UUID, connection_uri: str
) -> TenantWallet:
    try:
        conn = parse_nwc_uri(
            connection_uri,
            # ws:// sin TLS sólo fuera de producción (tests, relay local).
            allow_insecure_relay=settings.test_mode or settings.debug,
        )
    except NWCUriError as e:
        raise WalletConnectError(str(e)) from e

    tw = (
        await session.execute(select(TenantWallet).where(TenantWallet.tenant_id == tenant_id))
    ).scalar_one_or_none()
    enc = crypto.encrypt(connection_uri.strip())
    if tw is None:
        tw = TenantWallet(
            tenant_id=tenant_id,
            provider=WalletProviderKind.nwc,
            invoice_key_enc=enc,
        )
        session.add(tw)
    else:
        tw.provider = WalletProviderKind.nwc
        tw.invoice_key_enc = enc
        tw.lnbits_user_id = None
        tw.lnbits_wallet_id = None
        tw.admin_key_enc = None
    await session.commit()
    await session.refresh(tw)
    # El secreto jamás se devuelve; sólo lo necesario para que el panel muestre el estado.
    return tw
