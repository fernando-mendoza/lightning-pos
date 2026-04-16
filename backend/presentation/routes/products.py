from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from application.create_product import create_product
from application.update_product import update_product
from application.list_products import list_products
from application.delete_product import delete_product
from infrastructure.db.product_repo_sqlite import ProductRepoSQLite

router = APIRouter()
repo = ProductRepoSQLite()


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_mxn: float = Field(gt=0)


class ProductUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_mxn: float = Field(gt=0)


class ProductResponse(BaseModel):
    id: str
    name: str
    price_mxn: float
    active: bool
    created_at: str
    updated_at: str


@router.get("", response_model=list[ProductResponse])
async def get_products():
    products = await list_products(repo)
    return [ProductResponse(**p.__dict__) for p in products]


@router.post("", response_model=ProductResponse, status_code=201)
async def post_product(body: ProductCreate):
    product = await create_product(body.name, body.price_mxn, repo)
    return ProductResponse(**product.__dict__)


@router.put("/{product_id}", response_model=ProductResponse)
async def put_product(product_id: str, body: ProductUpdate):
    product = await update_product(product_id, body.name, body.price_mxn, repo)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(**product.__dict__)


@router.delete("/{product_id}", status_code=204)
async def remove_product(product_id: str):
    deleted = await delete_product(product_id, repo)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
