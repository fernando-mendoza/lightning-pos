from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from infrastructure.db.connection import init_db, close_db
from infrastructure.ws.manager import ws_manager
from presentation.middleware.pin_auth import PinAuthMiddleware
from presentation.routes import products, pos, sales, webhooks, auth, dashboard, testing


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

if settings.test_mode:
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
