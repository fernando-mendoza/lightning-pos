import os

import httpx
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")
TEST_PIN = "1234"
# Debe coincidir con LPOS_LNBITS_WEBHOOK_SECRET en docker-compose.test.yml
WEBHOOK_SECRET = "test-webhook-secret-fixed"


async def pay_invoice(client, payment_hash: str) -> None:
    """Simula que el cliente pago el invoice en el fake de LNbits."""
    resp = await client.post(f"/api/test/payments/{payment_hash}/pay")
    assert resp.status_code == 200, f"pay fallo: {resp.status_code} {resp.text}"


async def post_webhook(client, payment_hash: str, secret: str = WEBHOOK_SECRET):
    """POSTea el webhook de LNbits como lo haria LNbits real (con ?secret=)."""
    return await client.post(
        "/api/webhooks/lnbits",
        params={"secret": secret},
        json={"payment_hash": payment_hash},
    )


@pytest_asyncio.fixture(scope="session")
async def auth_token():
    """Devuelve un token valido. Setea el PIN si no existia, hace login siempre.
    Idempotente entre runs: si el PIN ya existe por una corrida previa,
    setup-pin responde 409 y seguimos a verify-pin."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as c:
        await c.post("/api/auth/setup-pin", json={"pin": TEST_PIN})
        login = await c.post("/api/auth/verify-pin", json={"pin": TEST_PIN})
        login.raise_for_status()
        return login.json()["token"]


@pytest_asyncio.fixture
async def client(auth_token):
    async with httpx.AsyncClient(
        base_url=BACKEND_URL,
        timeout=10.0,
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as c:
        yield c
