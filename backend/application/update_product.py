from domain.entities.product import Product
from domain.ports.product_repository import ProductRepository


async def update_product(
    product_id: str, name: str, price_mxn: float, repo: ProductRepository
) -> Product | None:
    product = await repo.get_by_id(product_id)
    if not product:
        return None
    product.name = name
    product.price_mxn = price_mxn
    return await repo.update(product)
