"""Use cases de órdenes, invoices y confirmación de pago (tenant-scoped).

Reusa el patrón endurecido del POS single-tenant: el webhook exige `?secret=` (por invoice)
y SIEMPRE re-verifica contra el wallet del tenant (`check_invoice`) antes de confirmar; el
GET de estado reconcilia por si el webhook se pierde.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from domain.ports.exchange_rate_service import ExchangeRateService
from domain.ports.wallet_provider import WalletProvider
from infrastructure.db.models import (
    Invoice,
    InvoiceStatus,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    TenantWallet,
    WalletProviderKind,
)
from infrastructure.security import crypto


class OrderError(Exception):
    pass


async def _tenant_invoice_key(session: AsyncSession, tenant_id) -> str:
    tw = (
        await session.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if tw is None:
        raise OrderError("tenant_wallet_missing")
    return crypto.decrypt(tw.invoice_key_enc)


async def create_order(
    session: AsyncSession, *, tenant_id, terminal_id, operator_user_id, items: list[dict]
) -> Order:
    if not items:
        raise OrderError("empty_order")
    order = Order(
        tenant_id=tenant_id,
        terminal_id=terminal_id,
        operator_user_id=operator_user_id,
        status=OrderStatus.open,
        subtotal_mxn=Decimal("0"),
        total_mxn=Decimal("0"),
    )
    session.add(order)
    await session.flush()

    subtotal = Decimal("0")
    for it in items:
        qty = int(it.get("qty", 1))
        if qty < 1:
            raise OrderError("invalid_qty")
        product_id = it.get("product_id")
        if product_id:
            product = (
                await session.execute(
                    select(Product).where(
                        Product.id == product_id, Product.tenant_id == tenant_id
                    )
                )
            ).scalar_one_or_none()
            if product is None:
                raise OrderError("product_not_found")
            desc, unit, pid = product.name, product.price_mxn, product.id
        else:
            if not it.get("description") or it.get("unit_price_mxn") is None:
                raise OrderError("invalid_line")
            desc = it["description"]
            unit = Decimal(str(it["unit_price_mxn"]))
            pid = None
        if unit < 0:
            raise OrderError("negative_price")
        line_total = unit * qty
        subtotal += line_total
        session.add(
            OrderItem(
                tenant_id=tenant_id,
                order_id=order.id,
                product_id=pid,
                description=desc,
                qty=qty,
                unit_price_mxn=unit,
                line_total_mxn=line_total,
            )
        )

    order.subtotal_mxn = subtotal
    order.total_mxn = subtotal
    await session.commit()
    return order


async def create_invoice_for_order(
    session: AsyncSession,
    wallet: WalletProvider,
    exchange: ExchangeRateService,
    *,
    tenant_id,
    order_id,
) -> Invoice:
    order = (
        await session.execute(
            select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if order is None:
        raise OrderError("order_not_found")
    if order.status != OrderStatus.open:
        raise OrderError("order_not_open")
    if order.total_mxn <= 0:
        raise OrderError("empty_order")

    rate = await exchange.get_rate()
    amount_sats = rate.mxn_to_sats(float(order.total_mxn))
    if amount_sats < 1:
        raise OrderError("amount_too_small")

    tw = (
        await session.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if tw is None:
        raise OrderError("tenant_wallet_missing")
    invoice_key = crypto.decrypt(tw.invoice_key_enc)

    webhook_secret = secrets.token_hex(16)
    webhook_url = (
        f"{settings.public_base_url}/api/v2/webhooks/lnbits?secret={webhook_secret}"
    )
    memo = f"Lightning POS · orden {str(order.id)[:8]}"

    wi = await wallet.create_invoice(invoice_key, amount_sats, memo, webhook_url)

    if wi.expires_at and wi.expires_at > 0:
        expires_at = datetime.fromtimestamp(wi.expires_at, tz=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.invoice_expiry)

    invoice = Invoice(
        tenant_id=tenant_id,
        order_id=order.id,
        provider=WalletProviderKind.lnbits,
        provider_wallet_id=tw.lnbits_wallet_id,
        bolt11=wi.bolt11,
        payment_hash=wi.payment_hash,
        amount_sats=amount_sats,
        amount_mxn=order.total_mxn,
        fx_rate=Decimal(str(rate.mxn_per_btc)),
        status=InvoiceStatus.pending,
        webhook_secret=webhook_secret,
        expires_at=expires_at,
    )
    session.add(invoice)
    order.status = OrderStatus.invoiced
    await session.commit()
    return invoice


def _apply_paid(invoice: Invoice, order: Order | None) -> None:
    invoice.status = InvoiceStatus.paid
    invoice.paid_at = datetime.now(timezone.utc)
    if order is not None:
        order.status = OrderStatus.paid


async def get_invoice(
    session: AsyncSession,
    wallet: WalletProvider,
    *,
    tenant_id,
    invoice_id,
    reconcile: bool = True,
) -> Invoice | None:
    invoice = (
        await session.execute(
            select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if invoice is None:
        return None

    if invoice.status == InvoiceStatus.pending:
        now = datetime.now(timezone.utc)
        order = await session.get(Order, invoice.order_id)
        if invoice.expires_at < now:
            invoice.status = InvoiceStatus.expired
            if order is not None and order.status == OrderStatus.invoiced:
                order.status = OrderStatus.expired
            await session.commit()
        elif reconcile:
            key = crypto.decrypt(
                (
                    await session.execute(
                        select(TenantWallet.invoice_key_enc).where(
                            TenantWallet.tenant_id == tenant_id
                        )
                    )
                ).scalar_one()
            )
            if await wallet.check_invoice(key, invoice.payment_hash):
                _apply_paid(invoice, order)
                await session.commit()
    return invoice


async def list_invoices(
    session: AsyncSession, *, tenant_id, limit: int = 50
) -> list[Invoice]:
    return list(
        (
            await session.execute(
                select(Invoice)
                .where(Invoice.tenant_id == tenant_id)
                .order_by(Invoice.created_at.desc())
                .limit(min(limit, 200))
            )
        )
        .scalars()
        .all()
    )


async def confirm_by_webhook(
    session: AsyncSession, wallet: WalletProvider, *, payment_hash: str, secret: str
) -> str:
    """Devuelve 'confirmed' | 'ignored' | 'forbidden'. No confía en el body: re-verifica."""
    invoice = (
        await session.execute(
            select(Invoice).where(Invoice.payment_hash == payment_hash)
        )
    ).scalar_one_or_none()
    if invoice is None:
        return "ignored"
    # Capa 1: el secret del query debe coincidir con el de ESTA invoice.
    if not secrets.compare_digest(secret or "", invoice.webhook_secret):
        return "forbidden"
    if invoice.status == InvoiceStatus.paid:
        return "confirmed"  # idempotente
    # Capa 2: re-verificar contra el wallet del tenant.
    key = await _tenant_invoice_key(session, invoice.tenant_id)
    if not await wallet.check_invoice(key, payment_hash):
        return "ignored"
    order = await session.get(Order, invoice.order_id)
    _apply_paid(invoice, order)
    await session.commit()
    return "confirmed"
