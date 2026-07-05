"""Rutas de órdenes, invoices y webhook (/api/v2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.multitenant.orders import (
    OrderError,
    confirm_by_webhook,
    create_invoice_for_order,
    create_order,
    get_invoice,
    list_invoices,
)
from infrastructure.db.base import get_session
from infrastructure.db.models import Invoice
from presentation.multitenant.deps import (
    TerminalContext,
    get_exchange,
    get_terminal_context,
    get_wallet,
)

router = APIRouter()


class OrderItemIn(BaseModel):
    product_id: uuid.UUID | None = None
    description: str | None = None
    qty: int = 1
    unit_price_mxn: Decimal | None = None


class OrderIn(BaseModel):
    items: list[OrderItemIn]


class OrderOut(BaseModel):
    id: str
    status: str
    subtotal_mxn: Decimal
    total_mxn: Decimal
    created_at: datetime


class InvoiceOut(BaseModel):
    id: str
    order_id: str
    status: str
    amount_sats: int
    amount_mxn: Decimal
    fx_rate: Decimal
    bolt11: str
    payment_hash: str
    expires_at: datetime
    paid_at: datetime | None


def _order_out(o) -> OrderOut:
    return OrderOut(
        id=str(o.id),
        status=o.status.value,
        subtotal_mxn=o.subtotal_mxn,
        total_mxn=o.total_mxn,
        created_at=o.created_at,
    )


def _invoice_out(i) -> InvoiceOut:
    return InvoiceOut(
        id=str(i.id),
        order_id=str(i.order_id),
        status=i.status.value,
        amount_sats=i.amount_sats,
        amount_mxn=i.amount_mxn,
        fx_rate=i.fx_rate,
        bolt11=i.bolt11,
        payment_hash=i.payment_hash,
        expires_at=i.expires_at,
        paid_at=i.paid_at,
    )


# ---- terminal (device token) ----
@router.post("/orders", response_model=OrderOut, status_code=201)
async def new_order(
    body: OrderIn,
    tc: TerminalContext = Depends(get_terminal_context),
    session: AsyncSession = Depends(get_session),
):
    try:
        order = await create_order(
            session,
            tenant_id=tc.tenant_id,
            terminal_id=tc.terminal.id,
            operator_user_id=None,
            items=[i.model_dump() for i in body.items],
        )
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _order_out(order)


@router.post("/orders/{order_id}/invoice", response_model=InvoiceOut, status_code=201)
async def invoice_order(
    order_id: uuid.UUID,
    tc: TerminalContext = Depends(get_terminal_context),
    session: AsyncSession = Depends(get_session),
    wallet=Depends(get_wallet),
    exchange=Depends(get_exchange),
):
    try:
        invoice = await create_invoice_for_order(
            session, wallet, exchange, tenant_id=tc.tenant_id, order_id=order_id
        )
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _invoice_out(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def invoice_status(
    invoice_id: uuid.UUID,
    tc: TerminalContext = Depends(get_terminal_context),
    session: AsyncSession = Depends(get_session),
    wallet=Depends(get_wallet),
):
    invoice = await get_invoice(
        session, wallet, tenant_id=tc.tenant_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    return _invoice_out(invoice)


@router.get("/invoices", response_model=list[InvoiceOut])
async def invoice_history(
    limit: int = 50,
    tc: TerminalContext = Depends(get_terminal_context),
    session: AsyncSession = Depends(get_session),
):
    invoices = await list_invoices(session, tenant_id=tc.tenant_id, limit=limit)
    return [_invoice_out(i) for i in invoices]


# ---- webhook (público, verificado por secret + re-check contra el wallet) ----
@router.post("/webhooks/lnbits")
async def lnbits_webhook(
    request: Request,
    secret: str = "",
    session: AsyncSession = Depends(get_session),
    wallet=Depends(get_wallet),
):
    body = await request.json()
    payment_hash = body.get("payment_hash", "")
    if not payment_hash:
        return {"status": "ignored"}
    result = await confirm_by_webhook(
        session, wallet, payment_hash=payment_hash, secret=secret
    )
    if result == "forbidden":
        raise HTTPException(status_code=403, detail="invalid_webhook_secret")
    return {"status": result}


# ---- test-only (registrado solo si LPOS_TEST_MODE=1) ----
testing_router = APIRouter()


@testing_router.post("/testing/fake-pay/{invoice_id}")
async def fake_pay(
    invoice_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    wallet=Depends(get_wallet),
):
    """Marca como pagada la invoice en el FakeWalletProvider y devuelve el secret del
    webhook para poder simular la llamada de LNbits en tests. Solo dev/test."""
    invoice = (
        await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    if not hasattr(wallet, "mark_paid"):
        raise HTTPException(status_code=400, detail="not_a_fake_wallet")
    wallet.mark_paid(invoice.payment_hash)
    return {"payment_hash": invoice.payment_hash, "webhook_secret": invoice.webhook_secret}
