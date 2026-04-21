import os

import httpx
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as c:
        yield c
