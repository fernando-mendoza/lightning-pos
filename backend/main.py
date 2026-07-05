from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from infrastructure.db.connection import init_db, close_db
from infrastructure.ws.manager import ws_manager
from presentation.middleware.pin_auth import PinAuthMiddleware
from presentation.routes import products, pos, sales, webhooks, auth, dashboard, testing
from presentation.multitenant import (
    accounts as mt_accounts,
    catalog as mt_catalog,
    orders as mt_orders,
    pairing as mt_pairing,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(PinAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(pos.router, prefix="/api", tags=["pos"])
app.include_router(sales.router, prefix="/api/sales", tags=["sales"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

# API multi-tenant (Fase 0). Auth propia (JWT usuario / device token); exenta del PIN middleware.
app.include_router(mt_accounts.router, prefix="/api/v2", tags=["v2-accounts"])
app.include_router(mt_pairing.router, prefix="/api/v2", tags=["v2-pairing"])
app.include_router(mt_catalog.router, prefix="/api/v2", tags=["v2-catalog"])
app.include_router(mt_orders.router, prefix="/api/v2", tags=["v2-orders"])

if settings.test_mode:
    app.include_router(mt_orders.testing_router, prefix="/api/v2", tags=["v2-testing"])
    app.include_router(testing.router, prefix="/api/test", tags=["testing"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/payments")
async def ws_payments(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
