import os

import httpx
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")
TEST_PIN = "1234"


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
