"""WalletProvider fake determinista para dev/tests (sin LNbits real).

Mantiene estado en memoria; `mark_paid` simula el pago de una invoice (lo usa la ruta de
testing). Debe ser un singleton compartido entre rutas (ver infrastructure/providers.py).
"""

from __future__ import annotations

import secrets
import time

from domain.ports.wallet_provider import (
    ProvisionedWallet,
    WalletInvoice,
    WalletProvider,
)


class FakeWalletProvider(WalletProvider):
    def __init__(self) -> None:
        self._counter = 0
        self._paid: set[str] = set()

    async def provision_wallet(self, name: str) -> ProvisionedWallet:
        self._counter += 1
        n = self._counter
        return ProvisionedWallet(
            provider_user_id=f"fakeuser{n:04d}",
            wallet_id=f"fakewallet{n:04d}",
            invoice_key=f"fakeinvoicekey{n:04d}",
            admin_key=f"fakeadminkey{n:04d}",
        )

    async def create_invoice(
        self, invoice_key: str, amount_sats: int, memo: str, webhook_url: str | None = None
    ) -> WalletInvoice:
        self._counter += 1
        # Aleatorio, no secuencial: el contador vive en memoria y tras un restart
        # del backend chocaría con hashes ya persistidos en la DB (unicidad real).
        payment_hash = f"fakehash{secrets.token_hex(12)}"
        bolt11 = f"lnbcfake{amount_sats}n1{payment_hash}"
        return WalletInvoice(
            payment_hash=payment_hash, bolt11=bolt11, expires_at=int(time.time()) + 300
        )

    async def check_invoice(self, invoice_key: str, payment_hash: str) -> bool:
        return payment_hash in self._paid

    # ---- solo para dev/tests ----
    def mark_paid(self, payment_hash: str) -> None:
        self._paid.add(payment_hash)
