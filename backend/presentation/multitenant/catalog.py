"""Rutas de catálogo (/api/v2).

Lectura/lookup: device token (la terminal). CRUD: JWT de usuario (manager/owner).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.multitenant.catalog import (
    CatalogError,
    create_product,
    delete_product,
    get_product,
    list_products,
    update_product,
)
from infrastructure.db.base import get_session
from presentation.multitenant.deps import (
    CurrentUser,
    TerminalContext,
    get_terminal_context,
    require_manager,
)

router = APIRouter()


class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    price_mxn: Decimal = Field(ge=0)
    barcode: str | None = None
    sku: str | None = None


class ProductPatch(BaseModel):
    name: str | None = None
    price_mxn: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = None
    sku: str | None = None
    active: bool | None = None


class ProductOut(BaseModel):
    id: str
    name: str
    price_mxn: Decimal
    barcode: str | None
    sku: str | None
    active: bool
    created_at: datetime


def _out(p) -> ProductOut:
    return ProductOut(
        id=str(p.id),
        name=p.name,
        price_mxn=p.price_mxn,
        barcode=p.barcode,
        sku=p.sku,
        active=p.active,
        created_at=p.created_at,
    )


# ---- terminal (device token): lookup/list ----
@router.get("/catalog/products", response_model=list[ProductOut])
async def list_catalog(
    query: str | None = None,
    barcode: str | None = None,
    limit: int = 50,
    tc: TerminalContext = Depends(get_terminal_context),
    session: AsyncSession = Depends(get_session),
):
    products = await list_products(
        session, tenant_id=tc.tenant_id, query=query, barcode=barcode, limit=limit
    )
    return [_out(p) for p in products]


# ---- manager (JWT): CRUD ----
@router.post("/catalog/products", response_model=ProductOut, status_code=201)
async def create_catalog_product(
    body: ProductIn,
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    try:
        product = await create_product(
            session,
            tenant_id=cu.tenant.id,
            name=body.name,
            price_mxn=body.price_mxn,
            barcode=body.barcode,
            sku=body.sku,
        )
    except CatalogError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _out(product)


@router.patch("/catalog/products/{product_id}", response_model=ProductOut)
async def patch_catalog_product(
    product_id: uuid.UUID,
    body: ProductPatch,
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    product = await update_product(
        session, tenant_id=cu.tenant.id, product_id=product_id, **body.model_dump()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="product_not_found")
    return _out(product)


@router.delete("/catalog/products/{product_id}")
async def delete_catalog_product(
    product_id: uuid.UUID,
    cu: CurrentUser = Depends(require_manager),
    session: AsyncSession = Depends(get_session),
):
    ok = await delete_product(session, tenant_id=cu.tenant.id, product_id=product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="product_not_found")
    return {"status": "deleted"}
