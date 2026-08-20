"""Use cases de administración del tenant: password, miembros, renames, reportes."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.multitenant.accounts import AccountError
from infrastructure.db.models import (
    Invoice,
    InvoiceStatus,
    Membership,
    Order,
    OrderStatus,
    PaymentMethod,
    Role,
    Tenant,
    Terminal,
    User,
)
from infrastructure.security.passwords import hash_password, verify_password


async def change_password(
    session: AsyncSession, user: User, *, current_password: str, new_password: str
) -> bool:
    """Cambia el password verificando el actual. Los JWT ya emitidos siguen
    vigentes hasta expirar (no hay lista de revocación)."""
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        return False
    user.password_hash = hash_password(new_password)
    await session.commit()
    return True


async def list_members(
    session: AsyncSession, *, tenant_id
) -> list[tuple[Membership, User]]:
    rows = (
        await session.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.tenant_id == tenant_id)
            .order_by(User.email)
        )
    ).all()
    return [(m, u) for (m, u) in rows]


async def add_member(
    session: AsyncSession,
    *,
    tenant_id,
    email: str,
    password: str | None,
    name: str | None,
    role: Role,
) -> tuple[Membership, User, bool]:
    """Agrega un miembro al tenant. Si el email ya es un usuario existente solo
    crea la membership (el password recibido se ignora); si no, crea el usuario
    con ese password inicial. Devuelve (membership, user, user_created)."""
    email = email.strip().lower()
    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    created = False
    if user is None:
        if not password:
            raise AccountError("password_required")
        user = User(email=email, password_hash=hash_password(password), name=name)
        session.add(user)
        await session.flush()
        created = True
    else:
        existing = (
            await session.execute(
                select(Membership).where(
                    Membership.tenant_id == tenant_id, Membership.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise AccountError("already_member")
    membership = Membership(tenant_id=tenant_id, user_id=user.id, role=role)
    session.add(membership)
    await session.commit()
    return membership, user, created


async def remove_member(session: AsyncSession, *, tenant_id, user_id) -> bool:
    membership = (
        await session.execute(
            select(Membership).where(
                Membership.tenant_id == tenant_id, Membership.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        return False
    if membership.role == Role.owner:
        raise AccountError("cannot_remove_owner")
    await session.delete(membership)
    await session.commit()
    return True


async def rename_tenant(session: AsyncSession, *, tenant_id, name: str) -> Tenant:
    tenant = await session.get(Tenant, tenant_id)
    tenant.name = name
    await session.commit()
    return tenant


async def rename_terminal(
    session: AsyncSession, *, tenant_id, terminal_id, name: str
) -> Terminal | None:
    terminal = (
        await session.execute(
            select(Terminal).where(
                Terminal.id == terminal_id, Terminal.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if terminal is None:
        return None
    terminal.name = name
    await session.commit()
    return terminal


async def sales_summary(
    session: AsyncSession, *, tenant_id, date_from: date, date_to: date
) -> dict:
    """VENTAS del tenant (órdenes pagadas, por cualquier método) por día (UTC) y terminal.

    Agrega sobre `orders`, no sobre `invoices`: una venta en efectivo no tiene invoice y
    antes de la Fase 1 habría sido invisible acá — el dueño no vería el dinero que su
    cajero sí cobró.

    Los sats salen del LEFT JOIN con la invoice pagada, así que una venta en efectivo
    aporta al total en MXN pero **0 sats**, que es la verdad: no hubo bitcoin de por medio.
    Una orden tiene como mucho una invoice (no se puede re-facturar una orden ya facturada),
    así que el join no duplica filas.
    """
    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
    paid_filter = (
        Order.tenant_id == tenant_id,
        Order.status == OrderStatus.paid,
        Order.paid_at >= start,
        Order.paid_at <= end,
    )
    paid_invoice = (Invoice.order_id == Order.id) & (Invoice.status == InvoiceStatus.paid)

    is_cash = Order.payment_method == PaymentMethod.cash
    cash_mxn = func.coalesce(func.sum(case((is_cash, Order.total_mxn), else_=0)), 0)
    ln_mxn = func.coalesce(func.sum(case((is_cash, 0), else_=Order.total_mxn)), 0)
    cash_count = func.count(case((is_cash, Order.id)))
    sats_sum = func.coalesce(func.sum(Invoice.amount_sats), 0)

    def _base():
        return select().select_from(Order).outerjoin(Invoice, paid_invoice).where(*paid_filter)

    count, mxn, sats, c_count, c_mxn, l_mxn = (
        await session.execute(
            _base().add_columns(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_mxn), 0),
                sats_sum,
                cash_count,
                cash_mxn,
                ln_mxn,
            )
        )
    ).one()

    day = func.date_trunc("day", Order.paid_at).label("day")
    by_day = (
        await session.execute(
            _base()
            .add_columns(
                day,
                func.count(Order.id),
                func.sum(Order.total_mxn),
                sats_sum,
                cash_mxn,
                ln_mxn,
            )
            .group_by(day)
            .order_by(day)
        )
    ).all()

    by_terminal = (
        await session.execute(
            _base()
            .outerjoin(Terminal, Terminal.id == Order.terminal_id)
            .add_columns(
                Order.terminal_id,
                func.max(Terminal.name),
                func.count(Order.id),
                func.sum(Order.total_mxn),
                sats_sum,
                cash_mxn,
                ln_mxn,
            )
            .group_by(Order.terminal_id)
            .order_by(func.sum(Order.total_mxn).desc())
        )
    ).all()

    def _mxn(v) -> str:
        return str(Decimal(v).quantize(Decimal("0.01")))

    return {
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "totals": {
            "count": count,
            "mxn": _mxn(mxn),
            "sats": int(sats),
            # Desglose por método. `mxn` es TODO lo cobrado; `sats` sólo la parte Lightning.
            "cash_count": c_count,
            "cash_mxn": _mxn(c_mxn),
            "lightning_count": count - c_count,
            "lightning_mxn": _mxn(l_mxn),
        },
        "by_day": [
            {
                "day": d.date().isoformat(),
                "count": n,
                "mxn": _mxn(m),
                "sats": int(s),
                "cash_mxn": _mxn(cm),
                "lightning_mxn": _mxn(lm),
            }
            for (d, n, m, s, cm, lm) in by_day
        ],
        "by_terminal": [
            {
                "terminal_id": str(tid) if tid else None,
                "name": tname,
                "count": n,
                "mxn": _mxn(m),
                "sats": int(s),
                "cash_mxn": _mxn(cm),
                "lightning_mxn": _mxn(lm),
            }
            for (tid, tname, n, m, s, cm, lm) in by_terminal
        ],
    }
