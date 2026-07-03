from datetime import datetime, timedelta, timezone

from config import settings
from domain.ports.sale_repository import SaleRepository

# Margen sobre el expiry del invoice antes de marcar la venta como expirada:
# cubre reloj desfasado y un webhook/poll que llegue justo al limite. Un invoice
# Lightning expirado ya no puede pagarse, asi que la venta nunca sera 'paid'.
EXPIRY_GRACE_SECONDS = 60


def _cutoff_iso() -> str:
    delta = timedelta(seconds=settings.invoice_expiry + EXPIRY_GRACE_SECONDS)
    return (datetime.now(timezone.utc) - delta).isoformat()


def is_past_expiry(created_at: str) -> bool:
    """True si la venta ya paso el expiry del invoice + gracia.
    Comparacion lexicografica: todos los created_at se generan con el mismo
    datetime.now(timezone.utc).isoformat()."""
    return created_at < _cutoff_iso()


async def expire_stale_sales(sale_repo: SaleRepository) -> int:
    """Marca como 'expired' toda venta pending cuyo invoice ya no es pagable.
    Se invoca lazy desde los endpoints de lectura (history); no hay job."""
    return await sale_repo.expire_stale(_cutoff_iso())
