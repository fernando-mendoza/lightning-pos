from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from application.get_exchange_rate import get_exchange_rate
from application.create_invoice import create_invoice
from application.cancel_sale import cancel_sale
from application.confirm_payment import confirm_payment
from infrastructure.db.sale_repo_sqlite import SaleRepoSQLite
from infrastructure.providers import exchange_service, lightning_service

router = APIRouter()

sale_repo = SaleRepoSQLite()


class ExchangeRateResponse(BaseModel):
    mxn_per_btc: float
    sats_per_mxn: float
    fetched_at: float
    source: str


class InvoiceItem(BaseModel):
    product_id: str
    product_name: str
    price_mxn: float = Field(gt=0)
    quantity: int = Field(gt=0)


class CreateInvoiceRequest(BaseModel):
    items: list[InvoiceItem] = Field(min_length=1)
    tip_mxn: float = Field(default=0.0, ge=0)
    discount_mxn: float = Field(default=0.0, ge=0)


class CreateInvoiceResponse(BaseModel):
    sale_id: str
    payment_hash: str
    bolt11: str
    total_mxn: float
    total_sats: int
    exchange_rate: float
    expires_at: int
    tip_mxn: float
    discount_mxn: float


@router.get("/exchange-rate", response_model=ExchangeRateResponse)
async def get_rate():
    try:
        rate = await get_exchange_rate(exchange_service)
    except Exception:
        raise HTTPException(status_code=502, detail="Exchange rate unavailable")
    return ExchangeRateResponse(
        mxn_per_btc=rate.mxn_per_btc,
        sats_per_mxn=rate.sats_per_mxn,
        fetched_at=rate.fetched_at,
        source=rate.source,
    )


@router.post("/invoices", response_model=CreateInvoiceResponse, status_code=201)
async def post_invoice(body: CreateInvoiceRequest):
    items = [
        {
            "product_id": i.product_id,
            "product_name": i.product_name,
            "price_mxn": i.price_mxn,
            "quantity": i.quantity,
        }
        for i in body.items
    ]
    try:
        result = await create_invoice(
            items,
            exchange_service,
            lightning_service,
            sale_repo,
            tip_mxn=body.tip_mxn,
            discount_mxn=body.discount_mxn,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return CreateInvoiceResponse(**result)


@router.get("/invoices/{payment_hash}/status")
async def get_invoice_status(payment_hash: str):
    sale = await sale_repo.get_by_payment_hash(payment_hash)
    if not sale:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # Reconciliacion: si el webhook de LNbits se perdio, el poll del frontend
    # es el unico camino para detectar el pago — preguntar a LNbits directo.
    if sale.status == "pending":
        try:
            paid = await lightning_service.check_invoice(payment_hash)
        except Exception:
            paid = False
        if paid:
            await confirm_payment(payment_hash, sale_repo)
            sale = await sale_repo.get_by_payment_hash(payment_hash)
    return {"payment_hash": payment_hash, "status": sale.status}


@router.post("/invoices/{payment_hash}/cancel")
async def post_cancel_invoice(payment_hash: str):
    ok = await cancel_sale(payment_hash, sale_repo)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail="Sale cannot be canceled (not pending or not found)",
        )
    return {"payment_hash": payment_hash, "status": "canceled"}
