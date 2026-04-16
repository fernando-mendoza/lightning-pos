from datetime import datetime, timezone

from domain.entities.sale import Sale, SaleItem
from domain.ports.sale_repository import SaleRepository
from infrastructure.db.connection import get_db


class SaleRepoSQLite(SaleRepository):
    async def create(self, sale: Sale) -> Sale:
        db = await get_db()
        await db.execute(
            """INSERT INTO sales (id, total_mxn, total_sats, exchange_rate,
               payment_hash, bolt11, status, created_at, paid_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sale.id, sale.total_mxn, sale.total_sats, sale.exchange_rate,
             sale.payment_hash, sale.bolt11, sale.status,
             sale.created_at, sale.paid_at),
        )
        for item in sale.items:
            await db.execute(
                """INSERT INTO sale_items (id, sale_id, product_id, product_name,
                   price_mxn, quantity, subtotal_mxn)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (item.id, item.sale_id, item.product_id, item.product_name,
                 item.price_mxn, item.quantity, item.subtotal_mxn),
            )
        await db.commit()
        return sale

    async def get_by_payment_hash(self, payment_hash: str) -> Sale | None:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM sales WHERE payment_hash = ?", (payment_hash,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        sale = self._row_to_sale(row)
        sale.items = await self._get_items(db, sale.id)
        return sale

    async def mark_paid(self, payment_hash: str, paid_at: str) -> bool:
        db = await get_db()
        cursor = await db.execute(
            """UPDATE sales SET status = 'paid', paid_at = ?
               WHERE payment_hash = ? AND status = 'pending'""",
            (paid_at, payment_hash),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def list_by_date(self, date_str: str) -> list[Sale]:
        db = await get_db()
        cursor = await db.execute(
            """SELECT * FROM sales
               WHERE date(created_at) = ? AND status = 'paid'
               ORDER BY created_at DESC""",
            (date_str,),
        )
        rows = await cursor.fetchall()
        sales = []
        for row in rows:
            sale = self._row_to_sale(row)
            sale.items = await self._get_items(db, sale.id)
            sales.append(sale)
        return sales

    @staticmethod
    async def _get_items(db, sale_id: str) -> list[SaleItem]:
        cursor = await db.execute(
            "SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,)
        )
        rows = await cursor.fetchall()
        return [
            SaleItem(
                id=r["id"],
                sale_id=r["sale_id"],
                product_id=r["product_id"],
                product_name=r["product_name"],
                price_mxn=r["price_mxn"],
                quantity=r["quantity"],
                subtotal_mxn=r["subtotal_mxn"],
            )
            for r in rows
        ]

    @staticmethod
    def _row_to_sale(row) -> Sale:
        return Sale(
            id=row["id"],
            total_mxn=row["total_mxn"],
            total_sats=row["total_sats"],
            exchange_rate=row["exchange_rate"],
            payment_hash=row["payment_hash"],
            bolt11=row["bolt11"],
            status=row["status"],
            created_at=row["created_at"],
            paid_at=row["paid_at"],
        )
