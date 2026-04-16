from datetime import datetime, timezone

from domain.entities.product import Product
from domain.ports.product_repository import ProductRepository
from infrastructure.db.connection import get_db


class ProductRepoSQLite(ProductRepository):
    async def create(self, product: Product) -> Product:
        db = await get_db()
        await db.execute(
            """INSERT INTO products (id, name, price_mxn, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product.id, product.name, product.price_mxn, product.active,
             product.created_at, product.updated_at),
        )
        await db.commit()
        return product

    async def get_by_id(self, product_id: str) -> Product | None:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_product(row)

    async def list_active(self) -> list[Product]:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM products WHERE active = 1 ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [self._row_to_product(r) for r in rows]

    async def update(self, product: Product) -> Product:
        db = await get_db()
        product.updated_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """UPDATE products SET name = ?, price_mxn = ?, active = ?, updated_at = ?
               WHERE id = ?""",
            (product.name, product.price_mxn, product.active,
             product.updated_at, product.id),
        )
        await db.commit()
        return product

    async def deactivate(self, product_id: str) -> bool:
        db = await get_db()
        cursor = await db.execute(
            """UPDATE products SET active = 0, updated_at = ?
               WHERE id = ? AND active = 1""",
            (datetime.now(timezone.utc).isoformat(), product_id),
        )
        await db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_product(row) -> Product:
        return Product(
            id=row["id"],
            name=row["name"],
            price_mxn=row["price_mxn"],
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
