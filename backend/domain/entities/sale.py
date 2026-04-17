from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SaleItem:
    id: str
    sale_id: str
    product_id: str
    product_name: str
    price_mxn: float
    quantity: int
    subtotal_mxn: float


@dataclass
class Sale:
    id: str
    total_mxn: float
    total_sats: int
    exchange_rate: float
    payment_hash: str
    bolt11: str
    status: str = "pending"  # pending | paid | expired | canceled
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    paid_at: str | None = None
    tip_mxn: float = 0.0
    discount_mxn: float = 0.0
    items: list[SaleItem] = field(default_factory=list)
