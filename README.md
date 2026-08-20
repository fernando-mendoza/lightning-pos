# Lightning POS ⚡

Punto de venta móvil para aceptar pagos en Bitcoin por Lightning Network, con precios en MXN y conversión automática a sats. Disponible como **app iOS**, **app Android** y **PWA web**.

> **Estado:** en producción.
> **App iOS:** [Lightning POS en el App Store](https://apps.apple.com/app/lightning-pos/id6790569225) — gratis, iPhone/iPad, iOS 15.1+ (v1.0, publicada el 26/07/2026).
> **App Android:** [Lightning POS en Google Play](https://play.google.com/store/apps/details?id=tf.lightningnetwork.pos) — gratis, v1.0.0 (publicada el 02/08/2026).
> **PoS web:** **[pos.lightningnetwork.tf](https://pos.lightningnetwork.tf)** — probalo sin instalar nada ni tocar el backend con el **[modo demostración](https://pos.lightningnetwork.tf/demo)** (o con el PIN `1111`): un PoS mock 100% en el navegador.
> **Landing del producto:** [lightningnetwork.tf](https://lightningnetwork.tf)

## Descargar la app

<a href="https://apps.apple.com/app/lightning-pos/id6790569225"><img src="docs/appstore-badge-es.svg" alt="Descárgalo en el App Store" height="52"></a>
<a href="https://play.google.com/store/apps/details?id=tf.lightningnetwork.pos"><img src="docs/googleplay-badge-es.png" alt="Disponible en Google Play" height="52"></a>

La app móvil es un *thin client* del backend multi-tenant de este repo (`/api/v2`): la terminal
se empareja escaneando un QR y solo guarda un device token. **La app nunca tiene llaves ni
fondos**: los invoices los emite la wallet del comercio y el pago liquida directo ahí.

Sobre la custodia, con precisión: el rail original (LNbits) sí era custodial **de nuestro lado**
— los saldos eran asientos en una base nuestra. El rail actual es **BYO wallet vía NWC**
(NIP-47): el comercio conecta *su* wallet con permisos de **sólo-recibir revocables por él**, y
nosotros nunca tocamos los fondos. Para el comercio que todavía no tiene wallet hay una rampa
(Lexe, self-custodial con nodo hospedado). Su código vive en un repo aparte (`expo-pos-terminal`).

Para evaluarla sin cuenta: al emparejar, usar el código `demo` → arranca un **modo demostración**
autocontenido (datos de ejemplo, sin backend ni wallet, los cobros se auto-confirman).

## Capturas

Todas las imágenes son del **modo demostración** en vivo ([`/demo`](https://pos.lightningnetwork.tf/demo)), que replica el flujo completo con datos de ejemplo y **sin conexión al backend**.

![Demostración del PoS web](docs/screenshots/demo.gif)

<table>
  <tr>
    <td width="50%"><b>Catálogo y cobro táctil</b><br><img src="docs/screenshots/01-pos.png" alt="Catálogo del POS"></td>
    <td width="50%"><b>Carrito con propina y descuento</b><br><img src="docs/screenshots/02-carrito.png" alt="Carrito"></td>
  </tr>
  <tr>
    <td><b>Cobro Lightning: QR BOLT11 · MXN↔sats</b><br><img src="docs/screenshots/03-cobro.png" alt="Cobro con QR Lightning"></td>
    <td><b>Historial de ventas del día</b><br><img src="docs/screenshots/04-historial.png" alt="Historial de ventas"></td>
  </tr>
  <tr>
    <td><b>Dashboard: hoy, últimos 7 días, top productos</b><br><img src="docs/screenshots/05-dashboard.png" alt="Dashboard de ventas"></td>
    <td><b>Gestión de productos (ABM)</b><br><img src="docs/screenshots/06-productos.png" alt="Gestión de productos"></td>
  </tr>
</table>

## Características

- 🛒 Catálogo de productos y carrito, pensado para uso táctil en móvil
- ⚡ Cobro por Lightning: invoice BOLT11 con QR. **Tres proveedores intercambiables** detrás de un solo puerto — el comercio puede **conectar su propia wallet** por [NWC / NIP-47](https://nwc.dev) y conservar la custodia
- 💵 **Cobro en efectivo**, con recibo, historial y reportes por método: la orden es la venta, así que una venta sin bitcoin no es invisible para el dueño
- 💱 Conversión MXN → sats en tiempo real con tipo de cambio de Bitso
- 🔔 Confirmación de pago por webhook + WebSocket, con *poll fallback* si el WS cae
- 🔐 Autenticación por PIN con JWT firmado, rate limit y lockout ante fuerza bruta
- 📊 Dashboard de ventas e historial
- 📱 Instalable como PWA (manifest + service worker)
- 🍎 App nativa en el [App Store](https://apps.apple.com/app/lightning-pos/id6790569225) y 🤖 en [Google Play](https://play.google.com/store/apps/details?id=tf.lightningnetwork.pos): terminal multi-tenant que se empareja por QR (`/api/v2`)

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · PostgreSQL (multi-tenant, `/api/v2`) · SQLite (instalación single-tenant) |
| Frontend | React 19 · Vite · TypeScript · Tailwind CSS v4 |
| App móvil (iOS + Android) | Expo SDK 54 · React Native · TypeScript (repo `expo-pos-terminal`, consume `/api/v2`) |
| Lightning | **NWC / NIP-47** (BYO wallet, cliente propio) · **Lexe** (nodo self-custodial hospedado) · LNbits (legado) |
| Infra | Docker Compose · Nginx (frontend) |

Arquitectura limpia en ambos lados: `domain/` (entidades y ports), `application/` (use cases), `infrastructure/` (DB, APIs externas, WebSocket) y `presentation/` (routes / components).

El frontend nunca habla con el proveedor de pagos directamente: FastAPI es el middleware y el único que conoce las credenciales, que viajan cifradas at-rest por comercio.

Cambiar de proveedor **no toca la lógica de negocio**: `domain/ports/wallet_provider.py` define el puerto y el router elige la implementación por el **formato de la credencial** del comercio. Con NWC los fondos nunca pasan por nosotros — el comercio concede permiso de **sólo recibir** y lo revoca desde su propia wallet cuando quiera.

## Quickstart (desarrollo)

> El stack local levanta la instalación **single-tenant** con LNbits, que es el camino más
> corto para probar sin cuentas. El API multi-tenant (`/api/v2`) usa los rails NWC / Lexe y se
> testea con `docker-compose.test-mt.yml`.

Requisitos: Docker + Docker Compose.

```bash
cp .env.example .env

# Levanta backend + frontend + LNbits con FakeWallet (sin Bitcoin real)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Primer arranque:

1. Abrir LNbits en `http://localhost:5001`, crear cuenta y wallet.
2. Copiar la **Admin key** del wallet y ponerla en `.env` como `LPOS_LNBITS_API_KEY`.
3. Reiniciar el backend: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend`.
4. Abrir el POS en `http://localhost:8080` y configurar un PIN.

Para simular un pago con FakeWallet: desde otro wallet de la misma instancia LNbits, pegar el BOLT11 en *Pay invoice*. El webhook marca la venta como pagada y la UI lo refleja al instante.

## Tests

Todos los tests corren en Docker; no hace falta instalar pytest ni Playwright localmente.

```bash
# Backend (pytest + httpx): lifecycle de invoices, idempotencia de webhooks,
# concurrencia de catálogo y stress de 5 cajeros simultáneos
docker compose -f docker-compose.test.yml run --rm --build backend-tests

# E2E (Playwright)
docker compose -f docker-compose.test.yml run --rm --build playwright

# Limpieza
docker compose -f docker-compose.test.yml down --volumes --remove-orphans
```

## Configuración

Todas las variables del backend usan el prefijo `LPOS_` y están documentadas en [`.env.example`](.env.example). Las críticas para producción:

- `LPOS_JWT_SECRET` — obligatorio (`openssl rand -hex 32`)
- `LPOS_PIN_HASH` — SHA-256 del PIN inicial
- Del proveedor de pagos, según el rail: `LPOS_LNBITS_*` (legado) o `LPOS_LEXE_SIDECAR_URL`.
  **NWC no necesita configuración global**: cada comercio trae su cadena de conexión.
- `LPOS_LIGHTNING_ENABLED` — interruptor del rail Lightning (el efectivo nunca depende de él)
- `LPOS_ALLOWED_ORIGINS` — CORS explícito, sin wildcards

## Decisiones de diseño

- Montos en MXN se almacenan como `REAL`; montos en sats como `INTEGER`.
- Nombre y precio del producto se desnormalizan en `sale_items` al momento de la venta: el ticket histórico no cambia si el catálogo se edita después.
- Webhooks de pago son idempotentes; un reintento del proveedor no duplica ventas.
- **No se ofrece un método de pago que no se pueda cumplir**: la app pregunta al backend qué puede cobrar ese comercio, y un proveedor caído responde con un código propio en vez de un error genérico — el comerciante puede distinguir "el proveedor está caído" de "la app está rota".

## Licencia

[MIT](LICENSE)

---

<!-- BEGIN:DEPLOY-LOCATION (generado por railway-fleet/stamp-deploy-location.sh — no editar a mano) -->
## 🚀 Dónde está desplegado

**Cuenta Railway: `railway-standby-3`** · tier `auto` · proyecto `lightning-pos`

Las cuentas Railway de este portafolio son **trials rotativas**: cuando una vence, el workload se muda a otra. Por eso el nombre de la cuenta no es garantía de nada — **la fuente de verdad es el inventario del hub**, no este archivo:

- `shared/infra/railway-inventory.json` en `x0r-memories` (campo `hosts` por cuenta)
- el vigilante reconcilia ese inventario contra la API de Railway en cada corrida y reporta la deriva; el reporte publica el mapa `workload → cuenta` verificado
- runbook de migración y checklist obligatorio: `workspaces/runs/2026-07-27-railway-auto-migration/02-runbook-migracion-neon.md`

**Al mover este workload entre cuentas hay que actualizar el inventario en el mismo commit** (regla no negociable del hub) y volver a correr `stamp-deploy-location.sh` acá.

<sub>Sincronizado con el inventario el 2026-08-20.</sub>
<!-- END:DEPLOY-LOCATION -->
