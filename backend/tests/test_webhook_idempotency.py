"""Escenario 1 del ICM de concurrencia + hardening del webhook (run prod).

Valida que el endpoint POST /api/webhooks/lnbits:
  - Rechaza requests sin secret o con secret invalido (403)
  - NO confirma un invoice que LNbits reporta como no pagado (anti-forjado:
    el payment_hash es derivable del bolt11 que el cliente ve en el QR)
  - Ignora hashes desconocidos o payloads vacios
  - Confirma una sola vez un invoice pending pagado (webhook duplicado es no-op)
  - No revive un invoice canceled
  - Bajo race concurrente, solo una de las 2 llamadas termina marcando paid

Y que GET /api/invoices/{hash}/status reconcilia contra LNbits cuando el
webhook se perdio (poll fallback confiable).
"""
import asyncio

import pytest

from tests.conftest import pay_invoice, post_webhook

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


async def test_webhook_sin_secret_es_rechazado(client):
    payment_hash = await _create_pending_sale(client)
    await pay_invoice(client, payment_hash)

    resp = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": payment_hash}
    )
    assert resp.status_code == 403

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    # Nota: el status endpoint reconcilia contra LNbits, y aqui el invoice SI
    # esta pagado — el 403 de arriba es lo que valida el rechazo del webhook.
    assert status_resp.status_code == 200


async def test_webhook_con_secret_invalido_es_rechazado(client):
    resp = await post_webhook(client, "cualquier_hash", secret="secret-incorrecto")
    assert resp.status_code == 403


async def test_webhook_forjado_sin_pago_no_confirma(client):
    """P0: un cliente malicioso conoce el payment_hash (viene en el bolt11 del
    QR). Aunque consiga el secret, el webhook NO debe confirmar una venta que
    LNbits reporta como no pagada."""
    payment_hash = await _create_pending_sale(client)

    resp = await post_webhook(client, payment_hash)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.json()["status"] == "pending"


async def test_webhook_sin_payment_hash_se_ignora(client):
    resp = await client.post(
        "/api/webhooks/lnbits",
        params={"secret": "test-webhook-secret-fixed"},
        json={},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


async def test_webhook_con_payment_hash_desconocido_se_ignora(client):
    resp = await post_webhook(client, "hash_que_no_existe_en_db")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


async def test_webhook_confirma_sale_pending_pagada(client):
    payment_hash = await _create_pending_sale(client)
    await pay_invoice(client, payment_hash)

    resp = await post_webhook(client, payment_hash)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "paid"


async def test_webhook_duplicado_segundo_es_ignored(client):
    payment_hash = await _create_pending_sale(client)
    await pay_invoice(client, payment_hash)

    first = await post_webhook(client, payment_hash)
    assert first.json()["status"] == "confirmed"

    second = await post_webhook(client, payment_hash)
    assert second.json()["status"] == "ignored"

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.json()["status"] == "paid"


async def test_webhook_sobre_sale_canceled_no_revive(client):
    payment_hash = await _create_pending_sale(client)

    cancel_resp = await client.post(f"/api/invoices/{payment_hash}/cancel")
    assert cancel_resp.status_code == 200

    # Aunque el cliente pague despues de la cancelacion, la sale no revive.
    await pay_invoice(client, payment_hash)
    webhook_resp = await post_webhook(client, payment_hash)
    assert webhook_resp.status_code == 200
    assert webhook_resp.json()["status"] == "ignored"

    status_resp = await client.get(f"/api/invoices/{payment_hash}/status")
    assert status_resp.json()["status"] == "canceled"


async def test_webhook_concurrente_solo_uno_confirma(client):
    payment_hash = await _create_pending_sale(client)
    await pay_invoice(client, payment_hash)

    r1, r2 = await asyncio.gather(
        post_webhook(client, payment_hash),
        post_webhook(client, payment_hash),
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


async def test_poll_status_reconcilia_pago_sin_webhook(client):
    """El webhook se pierde por completo: el poll del frontend debe detectar
    el pago preguntando a LNbits y confirmar la venta."""
    payment_hash = await _create_pending_sale(client)

    before = await client.get(f"/api/invoices/{payment_hash}/status")
    assert before.json()["status"] == "pending"

    await pay_invoice(client, payment_hash)

    after = await client.get(f"/api/invoices/{payment_hash}/status")
    assert after.json()["status"] == "paid"
