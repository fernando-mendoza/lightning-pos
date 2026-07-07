"""Use cases de catálogo (tenant-scoped)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Product


class CatalogError(Exception):
    pass


async def create_product(
    session: AsyncSession,
    *,
    tenant_id,
    name: str,
    price_mxn: Decimal,
    barcode: str | None = None,
    sku: str | None = None,
) -> Product:
    if barcode:
        dup = (
            await session.execute(
                select(Product.id).where(
                    Product.tenant_id == tenant_id, Product.barcode == barcode
                )
            )
        ).first()
        if dup:
            raise CatalogError("barcode_exists")
    product = Product(
        tenant_id=tenant_id, name=name, price_mxn=price_mxn, barcode=barcode, sku=sku, active=True
    )
    session.add(product)
    await session.commit()
    return product


async def list_products(
    session: AsyncSession,
    *,
    tenant_id,
    query: str | None = None,
    barcode: str | None = None,
    limit: int = 50,
    include_inactive: bool = False,
) -> list[Product]:
    stmt = select(Product).where(Product.tenant_id == tenant_id)
    if not include_inactive:
        stmt = stmt.where(Product.active.is_(True))
    if barcode:
        stmt = stmt.where(Product.barcode == barcode)
    if query:
        stmt = stmt.where(Product.name.ilike(f"%{query}%"))
    stmt = stmt.order_by(Product.name).limit(min(limit, 200))
    return list((await session.execute(stmt)).scalars().all())


async def get_product(session: AsyncSession, *, tenant_id, product_id) -> Product | None:
    return (
        await session.execute(
            select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()


async def update_product(
    session: AsyncSession, *, tenant_id, product_id, **fields
) -> Product | None:
    product = await get_product(session, tenant_id=tenant_id, product_id=product_id)
    if product is None:
        return None
    for key in ("name", "price_mxn", "barcode", "sku", "active"):
        if key in fields and fields[key] is not None:
            setattr(product, key, fields[key])
    await session.commit()
    return product


async def delete_product(session: AsyncSession, *, tenant_id, product_id) -> bool:
    """Soft-delete: active=False (preserva integridad con order_items históricos)."""
    product = await get_product(session, tenant_id=tenant_id, product_id=product_id)
    if product is None:
        return False
    product.active = False
    await session.commit()
    return True
