from abc import ABC, abstractmethod

from domain.entities.sale import Sale


class SaleRepository(ABC):
    @abstractmethod
    async def create(self, sale: Sale) -> Sale: ...

    @abstractmethod
    async def get_by_payment_hash(self, payment_hash: str) -> Sale | None: ...

    @abstractmethod
    async def mark_paid(self, payment_hash: str, paid_at: str) -> bool: ...

    @abstractmethod
    async def list_by_date(self, date_str: str) -> list[Sale]: ...
