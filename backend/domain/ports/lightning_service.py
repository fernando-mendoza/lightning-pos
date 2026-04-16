from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InvoiceResult:
    payment_hash: str
    bolt11: str
    expires_at: int  # unix timestamp


class LightningService(ABC):
    @abstractmethod
    async def create_invoice(self, amount_sats: int, memo: str) -> InvoiceResult: ...

    @abstractmethod
    async def check_invoice(self, payment_hash: str) -> bool: ...
