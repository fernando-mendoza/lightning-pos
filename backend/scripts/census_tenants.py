"""Censo de tenants: cuántos hay, cuáles tienen wallet custodial y cuáles recibieron dinero.

Para qué: el backend hosted provisiona una wallet LNbits en NUESTRA instancia por cada alta
(custodial). Antes de decidir cuánto corre el trabajo de devolver fondos / migrar a BYO wallet
hace falta el dato real. Y la pregunta que importa no es "cuántos tenants hay" sino
**cuántos recibieron un pago**: un tenant con wallet vacía no es un pasivo.

Sólo LEE. No escribe nada.

Uso (dentro del contenedor, que ya trae las deps y la env):

    railway ssh --service backend
    PYTHONPATH=/app python scripts/census_tenants.py

O desde fuera, con la env del servicio inyectada:

    railway run --service backend -- python backend/scripts/census_tenants.py

Necesita `LPOS_DATABASE_URL` en el entorno (SQLAlchemy async, driver asyncpg).
"""

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

SQL_TENANTS = """
SELECT
  t.name,
  t.slug,
  t.status,
  t.created_at,
  (w.id IS NOT NULL) AS tiene_wallet,
  COALESCE(SUM(CASE WHEN i.status = 'paid' THEN 1 ELSE 0 END), 0) AS pagadas,
  COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount_sats ELSE 0 END), 0) AS sats,
  COUNT(i.id) AS invoices_total,
  MAX(i.paid_at) AS ultimo_pago
FROM tenants t
LEFT JOIN tenant_wallets w ON w.tenant_id = t.id
LEFT JOIN invoices i ON i.tenant_id = t.id
GROUP BY t.id, t.name, t.slug, t.status, t.created_at, w.id
ORDER BY t.created_at
"""


async def main() -> None:
    url = os.environ.get("LPOS_DATABASE_URL")
    if not url:
        raise SystemExit("falta LPOS_DATABASE_URL en el entorno")

    engine = create_async_engine(url)
    async with engine.connect() as conn:
        rows = (await conn.execute(text(SQL_TENANTS))).mappings().all()
        usuarios = (await conn.execute(text("SELECT COUNT(*) FROM users"))).scalar()
        terminales = (await conn.execute(text("SELECT COUNT(*) FROM terminals"))).scalar()
        activas = (
            await conn.execute(
                text("SELECT COUNT(*) FROM terminals WHERE status = 'active'")
            )
        ).scalar()
    await engine.dispose()

    print(f"TENANTS: {len(rows)}   usuarios: {usuarios}   terminales: {terminales} ({activas} activas)")
    print("-" * 112)
    print(f"{'nombre':24} {'slug':20} {'creado':11} {'wallet':7} {'pagadas':8} {'sats':10} {'ult.pago':11}")
    print("-" * 112)

    con_dinero = 0
    for r in rows:
        if r["pagadas"] > 0:
            con_dinero += 1
        print(
            f"{(r['name'] or '')[:23]:24} {(r['slug'] or '')[:19]:20} "
            f"{str(r['created_at'])[:10]:11} {('si' if r['tiene_wallet'] else 'NO'):7} "
            f"{r['pagadas']:<8} {r['sats']:<10} "
            f"{(str(r['ultimo_pago'])[:10] if r['ultimo_pago'] else '-'):11}"
        )

    print("-" * 112)
    con_wallet = sum(1 for r in rows if r["tiene_wallet"])
    total_sats = sum(int(r["sats"]) for r in rows)
    print(f"RESUMEN: {len(rows)} tenants · {con_wallet} con wallet custodial · {con_dinero} con al menos un pago")
    print(f"         sats cobrados en total (histórico, no es saldo actual): {total_sats}")
    print()
    print("OJO: 'sats' es lo COBRADO histórico, no el saldo vivo en LNbits. Para el pasivo real")
    print("     hay que consultar el saldo de cada wallet en LNbits, no esta tabla.")


if __name__ == "__main__":
    asyncio.run(main())
