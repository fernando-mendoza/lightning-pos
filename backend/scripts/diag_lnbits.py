"""Diagnóstico: ¿puede cada tenant emitir una invoice Lightning AHORA?

Para qué: el 2026-08-11 se descubrió que ningún comercio podía generar un QR de pago, y el
síntoma era distinto según el tenant (404 para uno, 520 para otro). Sin esta herramienta hay
que reproducirlo a mano por tenant, decidiendo a ciegas si el problema es la llave guardada,
la instancia de LNbits o el nodo detrás.

Prueba el camino REAL: desencripta la invoice key de `tenant_wallets` igual que el backend y
llama a `POST /api/v1/payments` con `amount=1`. Una invoice entrante no mueve dinero y expira
sola; no cobra nada a nadie.

**NUNCA imprime llaves.** Sólo tenant, wallet_id recortado, status HTTP y el inicio del cuerpo.
El bolt11 también se recorta: es un dato de cobro, no hace falta completo para diagnosticar.

Uso:
    railway run --service backend -- python scripts/diag_lnbits.py
"""

import asyncio
import base64
import hashlib
import os
import re

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Se replica el descifrado de `infrastructure.security.crypto` en vez de importarlo: ese
# módulo importa `config.settings`, que hace fallar el arranque si el `.env` local del dev
# trae variables extra (Settings prohíbe extras). Un diagnóstico tiene que poder correrse
# desde afuera del contenedor. Si el formato de cifrado cambia, hay que actualizar esto —
# por eso el prefijo se afirma explícitamente.
_PREFIX = "enc:v1:"


def _decrypt(token: str) -> str:
    if not token.startswith(_PREFIX):
        raise ValueError("ciphertext inválido (prefijo faltante)")
    raw = base64.b64decode(token[len(_PREFIX):])
    key = hashlib.sha256(os.environ["LPOS_DATA_ENCRYPTION_KEY"].encode()).digest()
    return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode()

SQL = """
SELECT t.name, t.slug, w.lnbits_wallet_id, w.invoice_key_enc
  FROM tenants t
  JOIN tenant_wallets w ON w.tenant_id = t.id
 ORDER BY t.created_at
"""


async def main() -> None:
    url = os.environ.get("LPOS_DATABASE_URL")
    base = (os.environ.get("LPOS_LNBITS_URL") or "").rstrip("/")
    if not url:
        raise SystemExit("falta LPOS_DATABASE_URL")
    print(f"instancia LNbits configurada: {base or '(vacía!)'}")

    engine = create_async_engine(url)
    async with engine.connect() as conn:
        filas = (await conn.execute(text(SQL))).all()
    await engine.dispose()

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            h = await client.get(f"{base}/api/v1/health")
            print(f"health de la instancia: {h.status_code} {h.text[:80]}")
        except Exception as e:
            print(f"health de la instancia: ERROR {type(e).__name__}")

        print("-" * 100)
        print(f"{'tenant':26} {'wallet_id':14} {'status':7} cuerpo")
        print("-" * 100)
        for nombre, slug, wallet_id, enc in filas:
            try:
                key = _decrypt(enc)
            except Exception as e:
                print(f"{nombre[:25]:26} {'-':14} {'-':7} NO DESENCRIPTA: {type(e).__name__}")
                continue
            wid = (wallet_id or "-")[:12]
            try:
                r = await client.post(
                    f"{base}/api/v1/payments",
                    headers={"X-Api-Key": key},
                    json={"out": False, "amount": 1, "memo": f"diag {slug}"},
                )
                cuerpo = r.text[:150].replace("\n", " ")
                # recortar cualquier bolt11 del cuerpo: es un dato de cobro
                cuerpo = re.sub(r"(lnbc[a-z0-9]{10})[a-z0-9]+", r"\1…", cuerpo)
                print(f"{nombre[:25]:26} {wid:14} {r.status_code:<7} {cuerpo}")
            except Exception as e:
                print(f"{nombre[:25]:26} {wid:14} {'ERR':7} {type(e).__name__}: {e}"[:150])

    print("-" * 100)
    print("Lectura: 201/200 = puede cobrar · 401 = llave inválida para esta instancia ·")
    print("         404 = la llave no resuelve a ninguna wallet acá (¿wallet borrada o de otra")
    print("         instancia?) · 520 'Channel has been shut down' = LNbits no alcanza su nodo")
    print("         Lightning (falla de la instancia, no nuestra).")


if __name__ == "__main__":
    asyncio.run(main())
