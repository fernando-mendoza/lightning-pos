"""0002 ventas en efectivo: payment_method + paid_at en orders

Por qué:

La orden pasa a ser LA VENTA. Hasta ahora los reportes y el historial agregaban sobre
`invoices`, así que una venta sin invoice (efectivo) habría sido invisible para el dueño.
Para agregar sobre `orders` hacen falta dos cosas que la tabla no tenía:

- `payment_method`: cómo se cobró. Default `lightning` porque TODO lo que existe hoy se
  cobró por Lightning — el default hace que las filas viejas queden correctas sin tocarlas.
- `paid_at`: cuándo se cobró. `created_at` no sirve: una orden se crea al armar el carrito
  y se paga después, y el corte del día se hace por cuándo entró el dinero.

El backfill copia `invoices.paid_at` a la orden correspondiente para que los reportes
históricos den EXACTAMENTE lo mismo antes y después de este cambio. Sin eso, todas las
ventas anteriores quedarían con `paid_at NULL` y desaparecerían del reporte — el mismo bug
que este trabajo viene a evitar, pero al revés.

Revision ID: b2c9f4e17a05
Revises: 6e14050fd0b9
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c9f4e17a05"
down_revision: Union[str, Sequence[str], None] = "6e14050fd0b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "payment_method",
            sa.Enum("lightning", "cash", name="paymentmethod", native_enum=False, length=20),
            nullable=False,
            server_default="lightning",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill: la orden hereda el paid_at de su invoice pagada.
    op.execute(
        """
        UPDATE orders o
           SET paid_at = i.paid_at
          FROM invoices i
         WHERE i.order_id = o.id
           AND i.status = 'paid'
           AND i.paid_at IS NOT NULL
           AND o.paid_at IS NULL
        """
    )

    # Los reportes filtran por tenant + rango de paid_at. Sin este índice, cada corte
    # del día es un scan de todas las órdenes del tenant.
    op.create_index(
        "ix_orders_tenant_paid_at", "orders", ["tenant_id", "paid_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_orders_tenant_paid_at", table_name="orders")
    op.drop_column("orders", "paid_at")
    op.drop_column("orders", "payment_method")
