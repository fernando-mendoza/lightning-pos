"""WalletProvider sobre LNbits (custodial, un wallet por tenant).

Provisión: `POST /api/v1/account` crea un wallet+usuario nuevo sin superuser key
(verificado en LNbits 1.5.5) y devuelve inkey/adminkey. Invoices: `POST /api/v1/payments`
con la invoice key del tenant. Estado: `GET /api/v1/payments/{hash}`.
"""

from __future__ import annotations

import httpx

from domain.ports.wallet_provider import (
    ProvisionedWallet,
    WalletInvoice,
    WalletProvider,
)


class LNbitsWalletProvider(WalletProvider):
    def __init__(self, base_url: str, invoice_expiry: int = 300) -> None:
        self._base = base_url.rstrip("/")
        self._expiry = invoice_expiry

    async def provision_wallet(self, name: str) -> ProvisionedWallet:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/api/v1/account",
                json={"name": name},
            )
            resp.raise_for_status()
            data = resp.json()
        return ProvisionedWallet(
            provider_user_id=data.get("user"),
            wallet_id=data.get("id"),
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
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/api/v1/payments",
                headers={"X-Api-Key": invoice_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return WalletInvoice(
            payment_hash=data["payment_hash"],
            bolt11=data["bolt11"],
            expires_at=data.get("expires_at", 0),
        )

    async def check_invoice(self, invoice_key: str, payment_hash: str) -> bool:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base}/api/v1/payments/{payment_hash}",
                headers={"X-Api-Key": invoice_key},
            )
            resp.raise_for_status()
            data = resp.json()
        return bool(data.get("paid", False))
