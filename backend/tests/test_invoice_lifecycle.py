"""Escenario 2 del ICM — lifecycle de invoice (cancel + race con webhook tardio).

Cubre las transiciones validas e invalidas del state machine de sales:

  pending → paid       (webhook LNbits)
  pending → canceled   (POST /invoices/{hash}/cancel)

  paid NO puede cancelarse
  canceled NO puede cancelarse de nuevo
  webhook tardio sobre canceled NO revive a paid

El cancel endpoint devuelve 409 para hashes inexistentes o no-pending
(decision actual documentada; ver pos.py:98-106).
"""
import pytest

pytestmark = pytest.mark.asyncio


async def _create_pending_sale(client) -> str:
    items = [{
        "product_id": "p2",
        "product_name": "Chai",
        "price_mxn": 70.0,
        "quantity": 1,
    }]
    resp = await client.post("/api/invoices", json={"items": items})
    assert resp.status_code == 201, resp.text
    return resp.json()["payment_hash"]


async def test_cancel_sale_pending_funciona(client):
    hash_ = await _create_pending_sale(client)

    resp = await client.post(f"/api/invoices/{hash_}/cancel")
    assert resp.status_code == 200
    assert resp.json() == {"payment_hash": hash_, "status": "canceled"}

    status = await client.get(f"/api/invoices/{hash_}/status")
    assert status.json()["status"] == "canceled"


async def test_cancel_sale_ya_canceled_retorna_409(client):
    hash_ = await _create_pending_sale(client)

    first = await client.post(f"/api/invoices/{hash_}/cancel")
    assert first.status_code == 200

    second = await client.post(f"/api/invoices/{hash_}/cancel")
    assert second.status_code == 409


async def test_cancel_sale_paid_retorna_409(client):
    hash_ = await _create_pending_sale(client)

    webhook = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": hash_}
    )
    assert webhook.json()["status"] == "confirmed"

    cancel = await client.post(f"/api/invoices/{hash_}/cancel")
    assert cancel.status_code == 409

    status = await client.get(f"/api/invoices/{hash_}/status")
    assert status.json()["status"] == "paid"


async def test_cancel_sale_inexistente_retorna_409(client):
    resp = await client.post("/api/invoices/hash_que_no_existe/cancel")
    assert resp.status_code == 409


async def test_webhook_tardio_sobre_canceled_no_revive(client):
    """Cubre el caso critico del escenario 2: cliente paga un invoice que ya
    fue cancelado por el cajero. La sale debe quedar canceled."""
    hash_ = await _create_pending_sale(client)

    cancel = await client.post(f"/api/invoices/{hash_}/cancel")
    assert cancel.status_code == 200

    webhook = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": hash_}
    )
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "ignored"

    status = await client.get(f"/api/invoices/{hash_}/status")
    assert status.json()["status"] == "canceled"


async def test_status_endpoint_404_si_hash_no_existe(client):
    resp = await client.get("/api/invoices/hash_inexistente/status")
    assert resp.status_code == 404
