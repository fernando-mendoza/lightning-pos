import uuid

from domain.entities.sale import Sale, SaleItem
from domain.ports.exchange_rate_service import ExchangeRateService
from domain.ports.lightning_service import LightningService
from domain.ports.sale_repository import SaleRepository


async def create_invoice(
    items: list[dict],
    exchange_service: ExchangeRateService,
    lightning_service: LightningService,
    sale_repo: SaleRepository,
    tip_mxn: float = 0.0,
    discount_mxn: float = 0.0,
) -> dict:
    rate = await exchange_service.get_rate()

    subtotal_mxn = sum(i["price_mxn"] * i["quantity"] for i in items)

    if discount_mxn < 0 or tip_mxn < 0:
        raise ValueError("tip and discount cannot be negative")
    if discount_mxn > subtotal_mxn:
        raise ValueError("discount cannot exceed subtotal")

    total_mxn = subtotal_mxn - discount_mxn + tip_mxn
    if total_mxn <= 0:
        raise ValueError("Total after discount/tip must be positive")

    total_sats = rate.mxn_to_sats(total_mxn)

    if total_sats < 1:
        raise ValueError("Amount too small to create invoice")

    names = ", ".join(f'{i["product_name"]} x{i["quantity"]}' for i in items)
    memo = f"Lightning POS: {names}"
    if len(memo) > 150:
        memo = memo[:147] + "..."

    invoice = await lightning_service.create_invoice(total_sats, memo)

    sale_id = str(uuid.uuid4())
    sale_items = [
        SaleItem(
            id=str(uuid.uuid4()),
            sale_id=sale_id,
            product_id=i["product_id"],
            product_name=i["product_name"],
            price_mxn=i["price_mxn"],
            quantity=i["quantity"],
            subtotal_mxn=i["price_mxn"] * i["quantity"],
        )
        for i in items
    ]

    sale = Sale(
        id=sale_id,
        total_mxn=total_mxn,
        total_sats=total_sats,
        exchange_rate=rate.mxn_per_btc,
        payment_hash=invoice.payment_hash,
        bolt11=invoice.bolt11,
        tip_mxn=tip_mxn,
        discount_mxn=discount_mxn,
        items=sale_items,
    )
    await sale_repo.create(sale)

    return {
        "sale_id": sale.id,
        "payment_hash": invoice.payment_hash,
        "bolt11": invoice.bolt11,
        "total_mxn": total_mxn,
        "total_sats": total_sats,
        "exchange_rate": rate.mxn_per_btc,
        "expires_at": invoice.expires_at,
        "tip_mxn": tip_mxn,
        "discount_mxn": discount_mxn,
    }
