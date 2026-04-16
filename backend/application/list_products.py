from domain.entities.product import Product
from domain.ports.product_repository import ProductRepository


async def list_products(repo: ProductRepository) -> list[Product]:
    return await repo.list_active()
