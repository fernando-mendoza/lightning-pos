# Lightning POS

POS movil (PWA) para aceptar pagos en Bitcoin Lightning Network.

## Stack

- Backend: Python 3.12+ / FastAPI / SQLite (aiosqlite)
- Frontend: React 19 / Vite 6 / TypeScript / Tailwind v4
- Lightning: Phoenixd + LNbits
- Infra: VPS Hetzner CAX11 + Caddy

## Estructura

Clean architecture en backend y frontend:
- `domain/` — entidades, ports/interfaces
- `application/` — use cases
- `infrastructure/` — implementaciones (DB, APIs externas, WebSocket)
- `presentation/` — routes (backend) / components+pages (frontend)

## Reglas

- Idioma de codigo: ingles
- Idioma de documentacion: espanol
- No exponer LNbits directamente al frontend — FastAPI es el middleware
- Montos en MXN son REAL, montos en sats son INTEGER
- Desnormalizar nombre y precio de producto en sale_items al momento de la venta
- PIN auth sin expiracion en MVP

## Desarrollo local

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Contexto del workspace

Este proyecto se creo con el workspace `new-product-creation`.
Run: `workspaces/new-product-creation/runs/2026-04-16-lightning-pos/`
