from fastapi import APIRouter, Query
from pydantic import BaseModel

from infrastructure.db.sale_repo_sqlite import SaleRepoSQLite

router = APIRouter()
sale_repo = SaleRepoSQLite()


class SaleItemResponse(BaseModel):
    product_name: str
    price_mxn: float
    quantity: int
    subtotal_mxn: float


class SaleResponse(BaseModel):
    id: str
    total_mxn: float
    total_sats: int
    exchange_rate: float
    payment_hash: str
    status: str
    created_at: str
    paid_at: str | None
    items: list[SaleItemResponse]


@router.get("", response_model=list[SaleResponse])
async def get_sales(date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$")):
    sales = await sale_repo.list_by_date(date)
    return [
        SaleResponse(
            id=s.id,
            total_mxn=s.total_mxn,
            total_sats=s.total_sats,
            exchange_rate=s.exchange_rate,
            payment_hash=s.payment_hash,
            status=s.status,
            created_at=s.created_at,
            paid_at=s.paid_at,
            items=[
                SaleItemResponse(
                    product_name=i.product_name,
                    price_mxn=i.price_mxn,
                    quantity=i.quantity,
                    subtotal_mxn=i.subtotal_mxn,
                )
                for i in s.items
            ],
        )
        for s in sales
    ]
