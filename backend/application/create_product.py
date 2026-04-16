import uuid

from domain.entities.product import Product
from domain.ports.product_repository import ProductRepository


async def create_product(name: str, price_mxn: float, repo: ProductRepository) -> Product:
    product = Product(id=str(uuid.uuid4()), name=name, price_mxn=price_mxn)
    return await repo.create(product)
