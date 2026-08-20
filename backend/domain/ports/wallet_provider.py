"""Port de wallet Lightning por tenant.

Generaliza el LightningService single-tenant: cada operación recibe la invoice key del
wallet del tenant, y se puede provisionar un wallet nuevo. Permite intercambiar LNbits
(custodial) por NWC u otro proveedor sin tocar la lógica de negocio.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProvisionedWallet:
    provider_user_id: str | None
    wallet_id: str | None
    invoice_key: str
    admin_key: str | None


class WalletProviderUnavailable(Exception):
    """El rail de cobro externo no responde o rechaza la operación.

    Existe para distinguirla de un error nuestro. Sin ella, un proveedor caído sale como 500
    y el cajero lee "Algo salió mal": el comerciante no puede saber que el problema es del
    proveedor de pagos y culpa a la app.
    """


@dataclass
class WalletInvoice:
    payment_hash: str
    bolt11: str
    expires_at: int  # unix timestamp
    # Referencia opaca del proveedor, para los que no saben buscar por hash (Lexe).
    # `check_invoice` la recibe de vuelta; los que no la usan la ignoran.
    provider_ref: str | None = None


class WalletProvider(ABC):
    @abstractmethod
    async def provision_wallet(self, name: str) -> ProvisionedWallet: ...

    @abstractmethod
    async def create_invoice(
        self, invoice_key: str, amount_sats: int, memo: str, webhook_url: str | None = None
    ) -> WalletInvoice: ...

    @abstractmethod
    async def check_invoice(
        self, invoice_key: str, payment_hash: str, provider_ref: str | None = None
    ) -> bool: ...
