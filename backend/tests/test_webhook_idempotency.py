"""Escenario 1 del ICM de concurrencia — webhook LNbits idempotencia.

Valida que el endpoint POST /api/webhooks/lnbits:
  - Ignora hashes desconocidos o payloads vacios
  - Confirma una sola vez un invoice pending (webhook duplicado es no-op)
  - No revive un invoice canceled
  - Bajo race concurrente, solo una de las 2 llamadas termina marcando paid
"""
import asyncio

import pytest

pytestmark = pytest.mark.asyncio


async def _create_pending_sale(client) -> str:
    items = [{
        "product_id": "p1",
        "product_name": "Cafe",
        "price_mxn": 50.0,
        "quantity": 1,
    }]
    resp = await client.post("/api/invoices", json={"items": items})
    assert resp.status_code == 201, f"create invoice fallo: {resp.status_code} {resp.text}"
    return resp.json()["payment_hash"]


async def test_webhook_sin_payment_hash_se_ignora(client):
    resp = await client.post("/api/webhooks/lnbits", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


async def test_webhook_con_payment_hash_desconocido_se_ignora(client):
    resp = await client.post(
        "/api/webhooks/lnbits",
        json={"payment_hash": "hash_que_no_existe_en_db"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


async def test_webhook_confirma_sale_pending(client):
    payment_hash = await _create_pending_sale(client)

    resp = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": payment_hash}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "paid"


async def test_webhook_duplicado_segundo_es_ignored(client):
    payment_hash = await _create_pending_sale(client)

    first = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": payment_hash}
    )
    assert first.json()["status"] == "confirmed"

    second = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": payment_hash}
    )
    assert second.json()["status"] == "ignored"

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.json()["status"] == "paid"


async def test_webhook_sobre_sale_canceled_no_revive(client):
    payment_hash = await _create_pending_sale(client)

    cancel_resp = await client.post(f"/api/invoices/{payment_hash}/cancel")
    assert cancel_resp.status_code == 200

    webhook_resp = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": payment_hash}
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.json()["status"] == "ignored"

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.json()["status"] == "canceled"


async def test_webhook_concurrente_solo_uno_confirma(client):
    payment_hash = await _create_pending_sale(client)

    payload = {"payment_hash": payment_hash}
    r1, r2 = await asyncio.gather(
        client.post("/api/webhooks/lnbits", json=payload),
        client.post("/api/webhooks/lnbits", json=payload),
    )

    statuses = [r1.json()["status"], r2.json()["status"]]
    confirmed_count = statuses.count("confirmed")
    ignored_count = statuses.count("ignored")

    assert confirmed_count == 1, (
        f"Esperaba exactamente 1 confirmacion, obtuve {confirmed_count}. "
        f"Statuses: {statuses}"
    )
    assert ignored_count == 1

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.json()["status"] == "paid"
