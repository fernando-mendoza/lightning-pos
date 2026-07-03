"""Expiración de invoices (run prod 2026-07-02).

Un invoice Lightning expira a los LPOS_INVOICE_EXPIRY segundos (300 default)
y ya no puede pagarse. Las ventas pending con invoice vencido deben pasar a
'expired' (antes quedaban "Pendiente" para siempre en el historial).

La expiración es lazy: la dispara GET /api/sales (bulk) y
GET /api/invoices/{hash}/status (individual). Los tests backdatean created_at
vía la ruta test-only /api/test/sales/{hash}/backdate.
"""
from datetime import datetime, timezone

import pytest

from tests.conftest import pay_invoice, post_webhook

pytestmark = pytest.mark.asyncio

# invoice_expiry (300) + EXPIRY_GRACE_SECONDS (60) + margen
PAST_EXPIRY_SECONDS = 400


async def _create_pending_sale(client) -> str:
    items = [{
        "product_id": "exp1",
        "product_name": "Expirable",
        "price_mxn": 25.0,
        "quantity": 1,
    }]
    resp = await client.post("/api/invoices", json={"items": items})
    assert resp.status_code == 201, resp.text
    return resp.json()["payment_hash"]


async def _backdate(client, payment_hash: str, seconds: int) -> None:
    resp = await client.post(
        f"/api/test/sales/{payment_hash}/backdate", json={"seconds": seconds}
    )
    assert resp.status_code == 200, resp.text


async def test_venta_reciente_sigue_pending(client):
    payment_hash = await _create_pending_sale(client)
    resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert resp.json()["status"] == "pending"


async def test_status_endpoint_expira_venta_vencida(client):
    payment_hash = await _create_pending_sale(client)
    await _backdate(client, payment_hash, PAST_EXPIRY_SECONDS)

    resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert resp.json()["status"] == "expired"


async def test_history_expira_ventas_vencidas_en_bulk(client):
    payment_hash = await _create_pending_sale(client)
    await _backdate(client, payment_hash, PAST_EXPIRY_SECONDS)

    # la venta backdateada puede caer en hoy o ayer (UTC) segun la hora
    today = datetime.now(timezone.utc).date()
    found = None
    for date_str in (today.isoformat(),):
        resp = await client.get(f"/api/sales?date={date_str}")
        assert resp.status_code == 200
        found = next(
            (s for s in resp.json() if s["payment_hash"] == payment_hash), found
        )
    if found is None:
        from datetime import timedelta
        yesterday = (today - timedelta(days=1)).isoformat()
        resp = await client.get(f"/api/sales?date={yesterday}")
        found = next(
            (s for s in resp.json() if s["payment_hash"] == payment_hash), None
        )
    assert found is not None, "venta backdateada no aparece en el historial"
    assert found["status"] == "expired"


async def test_venta_pagada_no_expira(client):
    payment_hash = await _create_pending_sale(client)
    await pay_invoice(client, payment_hash)
    resp = await post_webhook(client, payment_hash)
    assert resp.json()["status"] == "confirmed"

    await _backdate(client, payment_hash, PAST_EXPIRY_SECONDS)
    status = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status.json()["status"] == "paid"


async def test_pago_en_lnbits_gana_sobre_expiracion(client):
    """Si LNbits registra el pago (webhook perdido) y el poll llega tarde,
    el pago gana: no se debe marcar expired una venta realmente cobrada."""
    payment_hash = await _create_pending_sale(client)
    await pay_invoice(client, payment_hash)
    await _backdate(client, payment_hash, PAST_EXPIRY_SECONDS)

    resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert resp.json()["status"] == "paid"


async def test_webhook_sobre_expirada_no_revive(client):
    payment_hash = await _create_pending_sale(client)
    await _backdate(client, payment_hash, PAST_EXPIRY_SECONDS)

    status = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status.json()["status"] == "expired"

    await pay_invoice(client, payment_hash)
    webhook = await post_webhook(client, payment_hash)
    assert webhook.json()["status"] == "ignored"

    status = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status.json()["status"] == "expired"


async def test_cancel_sobre_expirada_retorna_409(client):
    payment_hash = await _create_pending_sale(client)
    await _backdate(client, payment_hash, PAST_EXPIRY_SECONDS)

    status = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status.json()["status"] == "expired"

    cancel = await client.post(f"/api/invoices/{payment_hash}/cancel")
    assert cancel.status_code == 409