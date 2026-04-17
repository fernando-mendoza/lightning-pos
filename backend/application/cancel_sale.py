from domain.ports.sale_repository import SaleRepository


async def cancel_sale(payment_hash: str, sale_repo: SaleRepository) -> bool:
    sale = await sale_repo.get_by_payment_hash(payment_hash)
    if not sale or sale.status != "pending":
        return False
    return await sale_repo.mark_canceled(payment_hash)
