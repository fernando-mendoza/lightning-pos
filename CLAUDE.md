# Lightning POS

POS movil (PWA) para aceptar pagos en Bitcoin Lightning Network.

## Stack

- Backend: Python 3.12+ / FastAPI / SQLite (aiosqlite)
- Frontend: React 19 / Vite 6 / TypeScript / Tailwind v4
- Lightning: **tres rails intercambiables** (ver "Rails de cobro")
- Infra: **Railway** (cuenta `railway-standby-3`, proyecto `lightning-pos` `3f975bc8`) —
  servicios `frontend` (nginx: sirve la PWA y proxyea `/api` y `/ws`) + `backend`;
  DB en **Neon** + SQLite v1 en volumen. (La mención histórica a Hetzner/Caddy quedó obsoleta.)

## Rails de cobro (multi-tenant, `/api/v2`)

El puerto `domain/ports/wallet_provider.py` abstrae "de dónde sale la invoice".
`RoutingWalletProvider` elige el proveedor **por el formato de la credencial del tenant**
(`tenant_wallets.invoice_key_enc`, cifrada AES-GCM), así que sumar un rail no toca la
lógica de negocio:

| Credencial empieza con | Provider | Custodia | Estado |
|---|---|---|---|
| (cualquier otra cosa) | **LNbits** | nosotros | ⚰️ La instancia `shycurlew9` **expiró el 2026-08-15**. Legado. |
| `nostr+walletconnect://` | **NWC** (NIP-47) | **el comercio** | Arquitectura objetivo. Cliente propio (no hay librería madura en Python). |
| `lexe-sidecar:` | **Lexe** | el comercio (nodo en enclave) | Rampa para el comercio sin wallet. |

**NWC es la arquitectura; Lexe es la rampa.** NWC da permisos de sólo-recibir revocables por
el comercio y cero custodia nuestra; Lexe resuelve el arranque desde cero (su LSP abre y
fondea el primer canal sin costo on-chain, medido: comisión 0.5 %). Cuando Lexe exponga NWC
en su app —está en su nodo, con un `TODO` explícito en su código— esos tenants migran al
provider NWC sin tocar nada más.

### Qué puede cobrar cada tenant

`GET /api/v2/terminal/me` devuelve **`payment_methods`**. El efectivo siempre está; Lightning
sólo si la wallet del tenant es utilizable (`domain/capabilities.py`, regla **pura** y sin I/O
para que se pueda testear sin levantar Postgres). En LNbits, un `lnbits_wallet_id` en NULL es
un **alta a medias**: el tenant cree que puede cobrar y no puede — le pasó a AgentykCo y no se
detectó hasta un censo, semanas después.

**Regla dura: no ofrecer lo que no se puede cumplir.** Un proveedor caído sale como
**503 `lightning_unavailable`**, nunca como 500: un 500 llega al cajero como *"Algo salió
mal"* y el comerciante culpa a la app por un fallo ajeno.

### `Invoice.provider_ref` (migración 0003)

Referencia con la que el PROVEEDOR identifica el pago cuando no le alcanza el hash. Lexe
indexa por `<created_ms>-ln_<hash>` y **no acepta consulta por hash** (verificado sondeando su
API). Sin persistirla, una invoice de Lexe se emitiría bien y **jamás se podría reconciliar**.

### El sidecar de Lexe vive DENTRO de la imagen del backend

No es un servicio aparte: la cuenta de Railway está en trial y uno extra consume crédito.
`start.sh` lo levanta si hay `LEXE_CLIENT_CREDENTIALS`; el backend le habla por
`LPOS_LEXE_SIDECAR_URL` (`http://127.0.0.1:5393`). Es **config de proceso**: un sidecar = una
wallet, así que todos los tenants `lexe` cobran contra ESA wallet. Si el sidecar muere, el
backend arranca igual y el cobro devuelve 503 — mejor un POS que cobra en efectivo que un POS
que no arranca.

## Estructura

Clean architecture en backend y frontend:
- `domain/` — entidades, ports/interfaces
- `application/` — use cases
- `infrastructure/` — implementaciones (DB, APIs externas, WebSocket)
- `presentation/` — routes (backend) / components+pages (frontend)

## Reglas

- Idioma de codigo: ingles
- Idioma de documentacion: espanol
- No exponer el proveedor de pagos directamente al frontend — FastAPI es el middleware y
  el unico que conoce las credenciales (ver "Rails de cobro")
- Montos en MXN son REAL, montos en sats son INTEGER
- Desnormalizar nombre y precio de producto en sale_items al momento de la venta
- PIN auth sin expiracion en MVP

## Cache del PWA — no romper

La app se cachea a si misma (`frontend/public/sw.js`, registrado en `main.tsx`). Reglas:

- **El app shell (`/`, `/index.html`) va NETWORK-FIRST.** El cache es solo respaldo
  offline. Nunca cache-first: `index.html` referencia bundles con hash, asi que una
  copia cacheada deja al usuario clavado en una version vieja **hasta que borre el
  cache a mano** — ningun deploy lo alcanza. (Bug real 2026-07-29: el fix del boton
  "Salir" del modo demo no llegaba a nadie que ya hubiera abierto el PoS.)
- **Cache-first solo para `/assets/*`**, que llevan hash de contenido en el nombre
  (URL inmutable). En nginx van con `immutable 1y`; `index.html` con `no-cache`.
- **Al tocar el shell o la estrategia del SW: bumpear `CACHE_NAME`** (`lpos-vN`).
  El handler de `activate` purga las caches con otro nombre.
- `main.tsx` recarga UNA vez ante `controllerchange` (SW nuevo tomo control), con
  guardas `hadController`/`refreshing`. Sin eso, el SW viejo sigue sirviendo su
  shell y la actualizacion tarda varias cargas.
- Al cambiar cualquiera de estas piezas, verificar el camino del **usuario ya
  atrapado** (perfil de navegador persistente: cachear el build viejo y luego
  servir el nuevo en el mismo origen), no solo una ventana limpia.

## Deploy

- `pos.lightningnetwork.tf` **NO lo sirve Railway directo**: lo sirve el Worker de CF
  `lpos-proxy` (cuenta `cf-cldflr`, zona `lightningnetwork.tf`), que reescribe el Host
  hacia el dominio del servicio. **El punto de control del ruteo es el `ORIGIN` del
  Worker** (`infra/cf-proxy-worker.js`), no el custom domain de Railway: en cada
  rotacion de cuenta se cambia ahi + `railway up`.
- `railway up` del `frontend` va **desde la RAIZ del repo** (el servicio tiene
  `rootDirectory=/frontend`; correrlo desde `frontend/` falla con *"directory frontend
  does not exist"*).
- Tokens siempre via `hub-secret` (`railway-standby-3`, `cf-cldflr`, `gitea-zeeker`);
  jamas pegar un secreto en el chat.
- Antes de tocar ruteo/infra: **sincronizar el hub** (`hub-sync --pull`). Un catalogo
  rezagado puede decir que prod vive en una cuenta que ya se migro.

### Operar Railway sin perder tiempo (aprendido a los golpes el 2026-08-18)

- **El link es POR DIRECTORIO.** Correr desde `backend/` da *"Project not found"*: los
  comandos van desde la raiz del repo.
- **`railway deployment list` es la fuente de verdad**, no sondear HTTP. Un deploy puede
  tardar ~25 min en tomar trafico, y todo ese rato el sondeo muestra el codigo VIEJO.
- **`railway logs --build` muestra el ultimo build EXITOSO**, no el que esta corriendo.
  Para el deploy en curso: `railway logs --service backend --deployment <id>`.
- **`railway up` puede morir con 500 en el upload.** Reintentar suele alcanzar.
- **No hay llave SSH registrada** (la de ops se removio), asi que `railway ssh` no sirve.
  Para tocar la DB: `railway run -- <cmd local>` con un venv que tenga `asyncpg`.
- **Nunca `railway variables` sin `--json`**: el listado imprime VALORES al transcript.
  Para setear un secreto, expandirlo dentro del comando (`--set "K=$K"`) y silenciar salida.

## Publicar el repo público de GitHub (NO es un mirror)

Hay dos remotos y **no se comportan igual**:

| Remoto | Qué es | Cómo se actualiza |
|---|---|---|
| `origin` → Gitea | **canónico**, privado | push normal |
| `github` → `fernando-mendoza/lightning-pos` | **PÚBLICO**, no es mirror | **snapshots squasheados**, a mano |

**El repo público se publica como un commit único por publicación**, con la infra excluida por
construcción. No se pushea la historia canónica: contendría el código del Worker, que el owner
decidió **no publicar** (lleva el hostname del origen en Railway → ver `infra/README.md`).

Procedimiento (desde la raíz del repo):

```sh
# 1. verificar que el árbol no lleve nada que no deba ser público
git grep -n "up.railway.app" -- .            # debe dar vacío
# 2. snapshot squasheado sobre lo que ya está publicado
git fetch github main
git switch -c public-snapshot github/main
git read-tree -u --reset main                # árbol == canónico
git commit -m "release: <resumen> (snapshot de <sha-canónico>)"
# 3. publicar (token del vault; la cuenta gh activa puede ser otra)
hub-secret gh-fernando-mendoza -- git -c credential.helper='!f() { echo username=fernando-mendoza; echo password=$GITHUB_TOKEN; }; f' push github public-snapshot:main
git switch main && git branch -D public-snapshot
```

**Por qué squash y no reescribir la historia:** quitar el archivo de los 21 commits generaría
SHAs nuevos, divergentes del canónico que los docs ICM referencian por hash, exigiría
force-push, **y cada publicación futura necesitaría la misma cirugía** — una trampa que alguien
va a olvidar. Con snapshots, cada publicación es un fast-forward sobre la anterior y lo excluido
queda excluido por construcción.

**Costo asumido:** el repo público no tiene historia granular. Los mensajes de commit detallados
viven sólo en Gitea.

⚠️ La cuenta activa de `gh` puede no tener permiso sobre `fernando-mendoza/*` (acá es
`fer-zulu` y da **403**). De ahí el token del vault en el paso 3.

## Desarrollo local

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && pnpm install && pnpm dev
```

## Correr tests

Todos los tests corren en Docker. No instalar pytest/playwright localmente.

```bash
# Tests de backend (pytest + httpx)
docker compose -f docker-compose.test.yml run --rm --build backend-tests

# Tests E2E de frontend (Playwright)
docker compose -f docker-compose.test.yml run --rm --build playwright

# Limpiar recursos
docker compose -f docker-compose.test.yml down --volumes --remove-orphans
```

El `docker-compose.test.yml` es independiente del stack base; levanta su propio
backend (+ frontend cuando aplica) con DB efimera y secretos fijos de test.
