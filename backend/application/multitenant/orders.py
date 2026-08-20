"""Use cases de órdenes, invoices y confirmación de pago (tenant-scoped).

Reusa el patrón endurecido del POS single-tenant: el webhook exige `?secret=` (por invoice)
y SIEMPRE re-verifica contra el wallet del tenant (`check_invoice`) antes de confirmar; el
GET de estado reconcilia por si el webhook se pierde.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
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
    PaymentMethod,
    Product,
    TenantWallet,
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
        provider=tw.provider,
        provider_wallet_id=tw.lnbits_wallet_id,
        provider_ref=wi.provider_ref,
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
    now = datetime.now(timezone.utc)
    invoice.status = InvoiceStatus.paid
    invoice.paid_at = now
    if order is not None:
        order.status = OrderStatus.paid
        # La orden también sella su paid_at: los reportes agregan sobre orders, no sobre
        # invoices, así que sin esto una venta Lightning quedaría fuera del corte del día.
        order.paid_at = now


async def close_order_cash(session: AsyncSession, *, tenant_id, order_id) -> Order:
    """Cierra una orden cobrada en efectivo: sin wallet, sin invoice, sin tipo de cambio.

    Sólo se puede desde `open`. Una orden `invoiced` tiene un QR vivo que el cliente
    todavía puede pagar: cerrarla en efectivo arriesga cobrar dos veces la misma venta, y
    en un mostrador eso se descubre tarde y mal. Si el cliente cambia de opinión frente al
    QR, el camino es cobrar en una orden nueva y dejar que la anterior expire (una orden
    expirada no cuenta en los reportes).
    """
    order = (
        await session.execute(
            select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if order is None:
        raise OrderError("order_not_found")

    # Idempotente: reintentar por red inestable no puede duplicar ni fallar en falso.
    if order.status == OrderStatus.paid:
        if order.payment_method == PaymentMethod.cash:
            return order
        raise OrderError("order_already_paid")

    if order.status != OrderStatus.open:
        raise OrderError("order_not_open")
    if order.total_mxn <= 0:
        raise OrderError("empty_order")

    order.payment_method = PaymentMethod.cash
    order.status = OrderStatus.paid
    order.paid_at = datetime.now(timezone.utc)
    await session.commit()
    return order


async def list_sales(session: AsyncSession, *, tenant_id, limit: int = 50) -> list[tuple]:
    """Historial de la terminal: órdenes que llegaron a intentarse cobrar, por cualquier
    método.

    `list_invoices` sigue existiendo intacto porque las apps ya publicadas lo consumen;
    esto es el listado nuevo, el único que ve las ventas en efectivo. El LEFT JOIN trae el
    dato Lightning cuando lo hay y NULL cuando se cobró en efectivo.

    Se excluyen SÓLO las órdenes `open`: son carritos que nunca se cobraron, ruido en el
    historial. Las `invoiced`/`expired`/`cancelled` sí entran, porque el historial de la
    app hoy las muestra y quitarlas sería perder una función sin decirlo — el cajero usa
    esa vista para responder "¿esa venta sí pasó?".
    """
    rows = (
        await session.execute(
            select(Order, Invoice)
            .outerjoin(Invoice, Invoice.order_id == Order.id)
            .where(Order.tenant_id == tenant_id, Order.status != OrderStatus.open)
            .order_by(
                func.coalesce(Order.paid_at, Order.created_at).desc(),
            )
            .limit(min(limit, 200))
        )
    ).all()
    return [(o, i) for (o, i) in rows]


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
            if await wallet.check_invoice(key, invoice.payment_hash, invoice.provider_ref):
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
    if not await wallet.check_invoice(key, payment_hash, invoice.provider_ref):
        return "ignored"
    order = await session.get(Order, invoice.order_id)
    _apply_paid(invoice, order)
    await session.commit()
    return "confirmed"
