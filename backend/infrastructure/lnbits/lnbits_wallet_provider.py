"""WalletProvider sobre LNbits (custodial, un wallet por tenant).

Provisión: `POST /api/v1/account` crea un wallet+usuario nuevo sin superuser key
(verificado en LNbits 1.5.5) y devuelve inkey/adminkey. Invoices: `POST /api/v1/payments`
con la invoice key del tenant. Estado: `GET /api/v1/payments/{hash}`.

Todo fallo de transporte o de status se traduce a `WalletProviderUnavailable`. Sin esa
traducción, un LNbits caído sube como excepción no manejada y sale por la API como 500, que
el cajero lee "Algo salió mal" — indistinguible de un bug nuestro. Pasó en producción: la
instancia expiró y cada intento de cobro con bitcoin culpaba a la app.
"""

from __future__ import annotations

import httpx

from domain.ports.wallet_provider import (
    ProvisionedWallet,
    WalletInvoice,
    WalletProvider,
    WalletProviderUnavailable,
)


def _unavailable(exc: Exception) -> WalletProviderUnavailable:
    """Traduce un fallo de httpx a nuestra excepción, sin filtrar la llave del tenant."""
    if isinstance(exc, httpx.HTTPStatusError):
        return WalletProviderUnavailable(f"lnbits respondió {exc.response.status_code}")
    return WalletProviderUnavailable(f"lnbits inalcanzable ({type(exc).__name__})")


class LNbitsWalletProvider(WalletProvider):
    def __init__(self, base_url: str, invoice_expiry: int = 300) -> None:
        self._base = base_url.rstrip("/")
        self._expiry = invoice_expiry

    async def provision_wallet(self, name: str) -> ProvisionedWallet:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base}/api/v1/account",
                    json={"name": name},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise _unavailable(e) from e
        # `id` estricto a propósito: un wallet_id ausente dejaba el alta a medias y el tenant
        # creía que podía cobrar (le pasó a AgentykCo). Mejor fallar fuerte acá.
        if not data.get("id"):
            raise WalletProviderUnavailable("lnbits no devolvió wallet id")
        return ProvisionedWallet(
            provider_user_id=data.get("user"),
            wallet_id=data["id"],
            invoice_key=data["inkey"],
            admin_key=data.get("adminkey"),
        )

    async def create_invoice(
        self, invoice_key: str, amount_sats: int, memo: str, webhook_url: str | None = None
    ) -> WalletInvoice:
        payload = {
            "out": False,
            "amount": amount_sats,
            "memo": memo,
            "expiry": self._expiry,
        }
        if webhook_url:
            payload["webhook"] = webhook_url
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base}/api/v1/payments",
                    headers={"X-Api-Key": invoice_key},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise _unavailable(e) from e
        return WalletInvoice(
            payment_hash=data["payment_hash"],
            bolt11=data["bolt11"],
            expires_at=data.get("expires_at", 0),
        )

    async def check_invoice(
        self, invoice_key: str, payment_hash: str, provider_ref: str | None = None
    ) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self._base}/api/v1/payments/{payment_hash}",
                    headers={"X-Api-Key": invoice_key},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise _unavailable(e) from e
        return bool(data.get("paid", False))
