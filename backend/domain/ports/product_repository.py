from abc import ABC, abstractmethod

from domain.entities.product import Product


class ProductRepository(ABC):
    @abstractmethod
    async def create(self, product: Product) -> Product: ...

    @abstractmethod
    async def get_by_id(self, product_id: str) -> Product | None: ...

    @abstractmethod
    async def list_active(self) -> list[Product]: ...

    @abstractmethod
    async def update(self, product: Product) -> Product: ...

    @abstractmethod
    async def deactivate(self, product_id: str) -> bool: ...
