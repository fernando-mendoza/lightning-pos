"""Use cases de administración del tenant: password, miembros, renames, reportes."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.multitenant.accounts import AccountError
from infrastructure.db.models import (
    Invoice,
    InvoiceStatus,
    Membership,
    Order,
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
    """Invoices pagadas del tenant agregadas por día (UTC) y por terminal.
    Rango inclusive [date_from, date_to] sobre paid_at."""
    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
    paid_filter = (
        Invoice.tenant_id == tenant_id,
        Invoice.status == InvoiceStatus.paid,
        Invoice.paid_at >= start,
        Invoice.paid_at <= end,
    )

    count, mxn, sats = (
        await session.execute(
            select(
                func.count(Invoice.id),
                func.coalesce(func.sum(Invoice.amount_mxn), 0),
                func.coalesce(func.sum(Invoice.amount_sats), 0),
            ).where(*paid_filter)
        )
    ).one()

    day = func.date_trunc("day", Invoice.paid_at).label("day")
    by_day = (
        await session.execute(
            select(
                day,
                func.count(Invoice.id),
                func.sum(Invoice.amount_mxn),
                func.sum(Invoice.amount_sats),
            )
            .where(*paid_filter)
            .group_by(day)
            .order_by(day)
        )
    ).all()

    by_terminal = (
        await session.execute(
            select(
                Order.terminal_id,
                func.max(Terminal.name),
                func.count(Invoice.id),
                func.sum(Invoice.amount_mxn),
                func.sum(Invoice.amount_sats),
            )
            .join(Order, Order.id == Invoice.order_id)
            .outerjoin(Terminal, Terminal.id == Order.terminal_id)
            .where(*paid_filter)
            .group_by(Order.terminal_id)
            .order_by(func.sum(Invoice.amount_mxn).desc())
        )
    ).all()

    def _mxn(v) -> str:
        return str(Decimal(v).quantize(Decimal("0.01")))

    return {
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "totals": {"count": count, "mxn": _mxn(mxn), "sats": int(sats)},
        "by_day": [
            {"day": d.date().isoformat(), "count": n, "mxn": _mxn(m), "sats": int(s)}
            for (d, n, m, s) in by_day
        ],
        "by_terminal": [
            {
                "terminal_id": str(tid) if tid else None,
                "name": tname,
                "count": n,
                "mxn": _mxn(m),
                "sats": int(s),
            }
            for (tid, tname, n, m, s) in by_terminal
        ],
    }
