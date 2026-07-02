"""Escenario 4 del ICM — 5 cajeros concurrentes.

Mide la latencia de POST /api/invoices bajo N=5 clientes concurrentes.
Target inicial: p95 < 500ms.

Ademas valida:
  - 5 webhooks concurrentes: cada sale termina paid exactamente una vez
  - Workload mixto (invoice + listados + status) sin deadlock

Context: el backend mantiene un unico `aiosqlite.Connection` global
(connection.py:5), por lo que toda escritura se serializa en el lock interno
de aiosqlite. Este test valida que la serializacion es aceptable para
el target de 5 cajeros sin migrar a pool.
"""
import asyncio
import statistics
import time

import httpx
import pytest

from tests.conftest import BACKEND_URL, TEST_PIN, pay_invoice, post_webhook

pytestmark = pytest.mark.asyncio

CASHIERS = 5
INVOICES_PER_CASHIER = 10
LATENCY_TARGET_P95_MS = 500


async def _obtain_token() -> str:
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as c:
        await c.post("/api/auth/setup-pin", json={"pin": TEST_PIN})
        resp = await c.post("/api/auth/verify-pin", json={"pin": TEST_PIN})
        resp.raise_for_status()
        return resp.json()["token"]


async def _cashier_creates_invoices(
    token: str, n: int, cashier_id: int
) -> list[float]:
    """Un cajero crea n invoices serial. Retorna latencias individuales."""
    headers = {"Authorization": f"Bearer {token}"}
    latencies: list[float] = []
    items = [{
        "product_id": f"c{cashier_id}",
        "product_name": f"Cashier{cashier_id}",
        "price_mxn": 10.0,
        "quantity": 1,
    }]

    async with httpx.AsyncClient(
        base_url=BACKEND_URL, timeout=10.0, headers=headers
    ) as c:
        for _ in range(n):
            start = time.perf_counter()
            resp = await c.post("/api/invoices", json={"items": items})
            elapsed_ms = (time.perf_counter() - start) * 1000
            resp.raise_for_status()
            latencies.append(elapsed_ms)
    return latencies


def _pct(sorted_samples: list[float], p: float) -> float:
    idx = min(int(len(sorted_samples) * p), len(sorted_samples) - 1)
    return sorted_samples[idx]


async def test_5_concurrent_invoices_throughput():
    token = await _obtain_token()

    wall_start = time.perf_counter()
    results = await asyncio.gather(*[
        _cashier_creates_invoices(token, INVOICES_PER_CASHIER, i)
        for i in range(CASHIERS)
    ])
    wall_seconds = time.perf_counter() - wall_start

    all_latencies = sorted(lat for cashier in results for lat in cashier)
    total = len(all_latencies)
    assert total == CASHIERS * INVOICES_PER_CASHIER

    p50 = statistics.median(all_latencies)
    p95 = _pct(all_latencies, 0.95)
    p99 = _pct(all_latencies, 0.99)
    rps = total / wall_seconds

    print(
        f"\n[stress invoices] {CASHIERS} cashiers x {INVOICES_PER_CASHIER} = "
        f"{total} reqs"
    )
    print(
        f"[stress invoices] wall={wall_seconds:.2f}s  rps={rps:.1f}  "
        f"min={all_latencies[0]:.0f}ms  max={all_latencies[-1]:.0f}ms"
    )
    print(f"[stress invoices] p50={p50:.0f}ms  p95={p95:.0f}ms  p99={p99:.0f}ms")

    assert p95 < LATENCY_TARGET_P95_MS, (
        f"p95={p95:.0f}ms excede target={LATENCY_TARGET_P95_MS}ms. "
        f"Considerar pool de conexiones en connection.py."
    )


async def test_5_concurrent_webhooks_no_corruption(client):
    """Crear 5 invoices, disparar 5 webhooks concurrentes distintos, validar
    que cada sale termina paid exactamente una vez."""
    items = [{
        "product_id": "w",
        "product_name": "W",
        "price_mxn": 10.0,
        "quantity": 1,
    }]

    hashes: list[str] = []
    for _ in range(5):
        resp = await client.post("/api/invoices", json={"items": items})
        assert resp.status_code == 201
        hashes.append(resp.json()["payment_hash"])

    for h in hashes:
        await pay_invoice(client, h)

    webhook_responses = await asyncio.gather(*[
        post_webhook(client, h) for h in hashes
    ])
    for r in webhook_responses:
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    for h in hashes:
        status_resp = await client.get(f"/api/invoices/{h}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "paid"


async def test_5_concurrent_mixed_workload():
    """5 workers concurrentes haciendo mezcla (invoice + list products + status).
    Valida no deadlock y respuestas coherentes."""
    token = await _obtain_token()

    async def worker(worker_id: int):
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(
            base_url=BACKEND_URL, timeout=10.0, headers=headers
        ) as c:
            items = [{
                "product_id": f"mix{worker_id}",
                "product_name": f"Mix{worker_id}",
                "price_mxn": 20.0,
                "quantity": 1,
            }]
            inv = await c.post("/api/invoices", json={"items": items})
            assert inv.status_code == 201
            h = inv.json()["payment_hash"]

            products = await c.get("/api/products")
            assert products.status_code == 200
            assert isinstance(products.json(), list)

            status = await c.get(f"/api/invoices/{h}/status")
            assert status.status_code == 200
            assert status.json()["status"] == "pending"

    await asyncio.gather(*[worker(i) for i in range(CASHIERS)])
