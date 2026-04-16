from datetime import datetime, timezone

from domain.ports.sale_repository import SaleRepository
from infrastructure.ws.manager import ws_manager


async def confirm_payment(payment_hash: str, sale_repo: SaleRepository) -> bool:
    sale = await sale_repo.get_by_payment_hash(payment_hash)
    if not sale or sale.status != "pending":
        return False

    paid_at = datetime.now(timezone.utc).isoformat()
    updated = await sale_repo.mark_paid(payment_hash, paid_at)
    if not updated:
        return False

    await ws_manager.broadcast_payment(payment_hash, sale.id)
    return True
