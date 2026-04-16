from domain.ports.product_repository import ProductRepository


async def delete_product(product_id: str, repo: ProductRepository) -> bool:
    return await repo.deactivate(product_id)
