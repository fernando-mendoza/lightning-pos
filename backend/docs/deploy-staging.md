# Deploy staging — Backend multi-tenant (Fase 0)

⚠️ **No sobreescribir el POS single-tenant en producción** (`pos.lightningnetwork.tf`). El
backend multi-tenant se despliega como un **servicio/entorno SEPARADO** (staging) con su
propia base Postgres. El single-tenant sigue intacto hasta el cutover.

## ✅ Staging EN VIVO (2026-07-05)

- **URL:** https://backend-production-ec13.up.railway.app · health `/api/health` → 200.
- **Proyecto Railway:** `lightning-pos-mt-staging` (`cf08c123-…`), cuenta
  `lghntwrk1@mundial2026cdmx.tours` (**aislada** del proyecto de prod). Servicios: `backend`
  + `Postgres--GA0`.
- **Modo:** `LPOS_TEST_MODE=1` → wallet/exchange **fake** (staging seguro, sin tocar LNbits
  real ni fondos). Contrato OpenAPI servido en `/openapi.json`.
- **Verificado:** suite pytest (8/8) corrida **contra la URL de staging** + seed del tenant #0
  (`owner@lightningnetwork.tf`).
- **Para producción real:** quitar `LPOS_TEST_MODE`, setear `LPOS_LNBITS_URL` +
  `LPOS_BITSO_API_URL`, y re-desplegar (usa LNbits/Bitso reales).

### Config real usada (artefactos en el repo)

- `railway.json`: `build.builder=DOCKERFILE`; **`deploy.preDeployCommand="alembic upgrade
  head"`** (migra antes de arrancar); **`deploy.startCommand="sh start.sh"`**.
- `start.sh`: `exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"`.
- Variable `PORT=8000`.

### Gotchas de Railway (aprendidos)

1. **El `startCommand` se ejecuta como argv, SIN shell** → `$PORT`/`${PORT:-8000}` NO se
   expanden (uvicorn crashea con "not a valid integer"). Solución: arrancar vía un script
   (`sh start.sh`) donde el shell sí expande `$PORT`.
2. Setear `PORT=8000` para que app y proxy coincidan (además del fallback en `start.sh`).
3. Migraciones: usar `preDeployCommand` (logs limpios y falla el deploy si la migración falla),
   no encadenarlas en el `startCommand`.
4. `LPOS_DATABASE_URL` por **referencia** a Postgres, convertida a asyncpg:
   `postgresql+asyncpg://${{Postgres--GA0.PGUSER}}:${{Postgres--GA0.PGPASSWORD}}@${{Postgres--GA0.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres--GA0.PGDATABASE}}`.
5. Logs de runtime: `railway logs -d` (los de build son el default).

## Requisitos

- `RAILWAY_TOKEN` (no está en el entorno del asistente → lo provee el owner o corre el deploy).
- Cuenta/host de **LNbits** para producción de wallets por tenant (LNbits 1.5.5 ya validado:
  `POST /api/v1/account` provisiona wallet sin superuser key).

## Variables de entorno (servicio backend staging)

| Variable | Valor |
|---|---|
| `LPOS_DATABASE_URL` | Postgres de Railway en formato `postgresql+asyncpg://USER:PASS@HOST:PORT/DB` |
| `LPOS_JWT_SECRET` | `openssl rand -hex 32` |
| `LPOS_DATA_ENCRYPTION_KEY` | `openssl rand -hex 32` (cifra las llaves LNbits at-rest; **no perder**) |
| `LPOS_LNBITS_URL` | URL de la instancia LNbits (ej. `https://decimalpolenta9.lnbits.com`) |
| `LPOS_PUBLIC_BASE_URL` | URL pública del backend staging (va en el QR de pairing + webhook) |
| `LPOS_BITSO_API_URL` | `https://api.bitso.com/v3` |
| `LPOS_ALLOWED_ORIGINS` | orígenes del dashboard/app |
| `LPOS_TEST_MODE` | **no setear** (o `0`) → usa LNbits + Bitso reales |

> `LPOS_DATABASE_URL` de Railway suele venir como `postgresql://...`; convertir el esquema a
> `postgresql+asyncpg://...` para el driver async.

## Pasos (Railway)

1. Crear (o reutilizar en un entorno **staging**) un **servicio Postgres**.
2. Crear el **servicio backend** desde el repo (usa `backend/Dockerfile`), rootDir `backend`.
3. Setear las variables de arriba.
4. **Start command** del servicio staging (corre migraciones antes de servir; NO cambiar el
   Dockerfile para no afectar prod):
   ```sh
   sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
   ```
5. Deploy. Verificar `/api/health` → 200.
6. **Seed del tenant #0** (una vez): correr en el servicio (Railway "run" / one-off) con las
   mismas env vars:
   ```sh
   SEED_EMAIL=owner@lightningnetwork.tf SEED_PASSWORD=<seguro> SEED_TENANT="Lightning POS" \
     python scripts/seed_tenant_zero.py
   ```

## Runbook de verificación (contra cualquier `BASE`)

`BASE=https://<staging-host>/api/v2` (o `http://localhost:8000/api/v2` en local).

```sh
# 0. health
curl -s ${BASE%/api/v2}/api/health         # {"status":"ok"}

# 1. registrar comercio (crea tenant + provisiona wallet LNbits real)
curl -s -X POST $BASE/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"demo@x.mx","password":"supersecret1","tenant_name":"Demo"}'
# -> access_token, tenant_id

# 2. generar QR de pairing (manager). TOKEN y TENANT del paso 1
curl -s -X POST $BASE/pairing-codes -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT" -H 'Content-Type: application/json' \
  -d '{"name":"Mesa 1","role":"cashier"}'
# -> code + pairing_payload {server_url, code}  (esto va en el QR)

# 3. la app canjea el código -> device token
curl -s -X POST $BASE/pairing/redeem -H 'Content-Type: application/json' \
  -d '{"code":"<code>","device_name":"iPhone"}'
# -> device_token

# 4. (manager) crear producto
curl -s -X POST $BASE/catalog/products -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT" -H 'Content-Type: application/json' \
  -d '{"name":"Cafe","price_mxn":"50.00","barcode":"750111"}'

# 5. (terminal) lookup por barcode
curl -s "$BASE/catalog/products?barcode=750111" -H "Authorization: Bearer $DEVICE_TOKEN"

# 6. (terminal) crear orden + invoice (Lightning REAL)
curl -s -X POST $BASE/orders -H "Authorization: Bearer $DEVICE_TOKEN" \
  -H 'Content-Type: application/json' -d '{"items":[{"product_id":"<pid>","qty":1}]}'
curl -s -X POST $BASE/orders/<order_id>/invoice -H "Authorization: Bearer $DEVICE_TOKEN"
# -> bolt11 + amount_sats + amount_mxn  (mostrar QR del bolt11 al cliente)

# 7. pagar el bolt11 con una wallet Lightning real; luego consultar estado (reconcilia)
curl -s $BASE/invoices/<invoice_id> -H "Authorization: Bearer $DEVICE_TOKEN"
# -> status: "paid" tras el pago (webhook o poll)
```

**Criterios de aceptación staging:** health 200; register provisiona wallet; pairing→redeem
da device token; producto/orden/invoice crean invoice Lightning real; el pago real marca la
invoice `paid` (vía webhook LNbits o el poll de estado). Revocar terminal → `terminal/me` 401.

## Notas de seguridad

- Guardar `LPOS_DATA_ENCRYPTION_KEY` y `LPOS_JWT_SECRET` en el vault de Railway; si se pierde
  la de encriptación, las llaves LNbits guardadas no se pueden descifrar.
- Custodial: la instancia LNbits custodia los sats de los tenants (decisión de negocio).
