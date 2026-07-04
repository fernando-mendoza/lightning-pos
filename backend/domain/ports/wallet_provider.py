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


@dataclass
class WalletInvoice:
    payment_hash: str
    bolt11: str
    expires_at: int  # unix timestamp


class WalletProvider(ABC):
    @abstractmethod
    async def provision_wallet(self, name: str) -> ProvisionedWallet: ...

    @abstractmethod
    async def create_invoice(
        self, invoice_key: str, amount_sats: int, memo: str, webhook_url: str | None = None
    ) -> WalletInvoice: ...

    @abstractmethod
    async def check_invoice(self, invoice_key: str, payment_hash: str) -> bool: ...
