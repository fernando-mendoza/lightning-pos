"""WalletProvider sobre NWC (NIP-47): la wallet es del comercio, nosotros sólo pedimos.

La "invoice key" de este provider ES la cadena de conexión completa
(`nostr+walletconnect://…`), que ya viaja cifrada at-rest en `invoice_key_enc`. No hay
provisión: el comercio trae su wallet, y puede revocarnos desde ella cuando quiera —
ese es el punto de toda la arquitectura (custodia cero, permiso de sólo-recibir).
"""

from __future__ import annotations

from domain.ports.wallet_provider import (
    ProvisionedWallet,
    WalletInvoice,
    WalletProvider,
    WalletProviderUnavailable,
)

from .client import NWCError, rpc
from .uri import NWCUriError, parse_nwc_uri


class NWCWalletProvider(WalletProvider):
    def __init__(self, invoice_expiry: int = 300, *, allow_insecure_relay: bool = False) -> None:
        self._expiry = invoice_expiry
        self._allow_insecure = allow_insecure_relay

    async def provision_wallet(self, name: str) -> ProvisionedWallet:
        # NWC no provisiona: la wallet la trae el comercio. Si esto se llama, hay un bug de
        # cableado — mejor reventar acá que dar de alta un tenant a medias.
        raise RuntimeError("NWC no provisiona wallets: el comercio conecta la suya")

    def _conn(self, invoice_key: str):
        try:
            return parse_nwc_uri(invoice_key, allow_insecure_relay=self._allow_insecure)
        except NWCUriError as e:
            # Credencial corrupta en DB o mal migrada. No es transitorio: que se vea.
            raise WalletProviderUnavailable(f"cadena NWC inválida: {e}") from e

    async def create_invoice(
        self, invoice_key: str, amount_sats: int, memo: str, webhook_url: str | None = None
    ) -> WalletInvoice:
        # webhook_url se ignora: NWC no tiene webhooks; la confirmación va por el polling de
        # GET /invoices/{id} (reconciliación ya existente) y, a futuro, notificaciones NIP-47.
        conn = self._conn(invoice_key)
        result = await rpc(
            conn,
            "make_invoice",
            {"amount": amount_sats * 1000, "description": memo, "expiry": self._expiry},
        )
        bolt11 = result.get("invoice")
        payment_hash = result.get("payment_hash")
        if not bolt11 or not payment_hash:
            raise WalletProviderUnavailable("make_invoice respondió sin invoice/payment_hash")
        return WalletInvoice(
            payment_hash=payment_hash,
            bolt11=bolt11,
            expires_at=int(result.get("expires_at") or 0),
        )

    async def check_invoice(
        self, invoice_key: str, payment_hash: str, provider_ref: str | None = None
    ) -> bool:
        conn = self._conn(invoice_key)
        try:
            result = await rpc(conn, "lookup_invoice", {"payment_hash": payment_hash})
        except NWCError as e:
            if e.code == "NOT_FOUND":
                return False  # el wallet no la conoce ⇒ no está pagada; nunca confirmar de más
            raise WalletProviderUnavailable(str(e)) from e
        state = str(result.get("state") or "").lower()
        return bool(result.get("preimage")) or bool(result.get("settled_at")) or state == "settled"
