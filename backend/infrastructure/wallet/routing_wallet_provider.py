"""Enruta cada operación al provider que entiende la credencial del tenant.

La credencial es auto-descriptiva: una cadena `nostr+walletconnect://…` es NWC; cualquier
otra cosa es la invoice key del provider base (LNbits en prod, fake en tests). Así el punto
de decisión es UNO y no hay que tocar la lógica de negocio para sumar un provider — que es
exactamente lo que prometía el docstring del puerto.

`__getattr__` delega lo no estándar al base: la ruta de testing detecta el fake por
`hasattr(wallet, "mark_paid")`, y ese contrato debe sobrevivir al wrapper.
"""

from __future__ import annotations

from domain.ports.wallet_provider import ProvisionedWallet, WalletInvoice, WalletProvider
from infrastructure.lexe.lexe_wallet_provider import CREDENTIAL_PREFIX as LEXE_PREFIX
from infrastructure.nwc.uri import SCHEME as NWC_SCHEME


class RoutingWalletProvider(WalletProvider):
    def __init__(
        self, base: WalletProvider, nwc: WalletProvider, lexe: WalletProvider | None = None
    ) -> None:
        self._base = base
        self._nwc = nwc
        self._lexe = lexe

    def _pick(self, invoice_key: str) -> WalletProvider:
        if invoice_key.startswith(f"{NWC_SCHEME}://"):
            return self._nwc
        if self._lexe is not None and invoice_key.startswith(LEXE_PREFIX):
            return self._lexe
        return self._base

    async def provision_wallet(self, name: str) -> ProvisionedWallet:
        return await self._base.provision_wallet(name)

    async def create_invoice(
        self, invoice_key: str, amount_sats: int, memo: str, webhook_url: str | None = None
    ) -> WalletInvoice:
        return await self._pick(invoice_key).create_invoice(invoice_key, amount_sats, memo, webhook_url)

    async def check_invoice(
        self, invoice_key: str, payment_hash: str, provider_ref: str | None = None
    ) -> bool:
        return await self._pick(invoice_key).check_invoice(
            invoice_key, payment_hash, provider_ref
        )

    def __getattr__(self, name: str):
        return getattr(self._base, name)
