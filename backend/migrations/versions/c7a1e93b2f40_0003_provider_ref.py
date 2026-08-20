"""0003 provider_ref en invoices: la referencia con la que el proveedor identifica el pago

Por qué:

Hasta ahora `payment_hash` alcanzaba para preguntarle a LNbits si una invoice se pagó. Lexe
no: su sidecar indexa los pagos por un `index` propio con formato `<created_ms>-ln_<hash>`,
y **no expone consulta por hash** (verificado sondeando su API: `payment?hash=` y
`payment?payment_hash=` responden "missing field index"; tampoco existe un listado).

Sin guardar esa referencia, una invoice de Lexe quedaría imposible de reconciliar: el cobro
se emitiría bien y el pago del cliente nunca se confirmaría. Es exactamente el modo de falla
que veníamos arreglando — cobrar y que el dueño no lo vea.

Nullable a propósito: LNbits y NWC identifican por hash y no lo necesitan. Nada que
backfillear (ninguna invoice existente es de Lexe).

Revision ID: c7a1e93b2f40
Revises: b2c9f4e17a05
Create Date: 2026-08-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7a1e93b2f40"
down_revision: Union[str, Sequence[str], None] = "b2c9f4e17a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("provider_ref", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "provider_ref")
