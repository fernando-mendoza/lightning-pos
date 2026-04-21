"""Escenario 3 del ICM — writes concurrentes al catalogo.

Politica: last-write-wins, sin optimistic locking (decision del intake).
Los tests documentan esta politica aceptada y validan que el historial de ventas
(sale_items) es inmune a edits posteriores del producto por la desnormalizacion.
"""
import asyncio
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.asyncio


async def _create_product(client, name: str, price: float) -> str:
    resp = await client.post(
        "/api/products", json={"name": name, "price_mxn": price}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _get_product(client, product_id: str) -> dict:
    resp = await client.get("/api/products")
    assert resp.status_code == 200
    for p in resp.json():
        if p["id"] == product_id:
            return p
    raise AssertionError(f"Product {product_id} no encontrado en GET /products")


async def test_two_concurrent_puts_last_wins(client):
    """Dos PUT simultaneos al mismo producto. Uno gana, el otro se pierde.
    No debe quedar un estado corrupto (nombre de uno + precio de otro)."""
    product_id = await _create_product(client, "Cafe", 50.0)

    payload_a = {"name": "Cafe A", "price_mxn": 55.0}
    payload_b = {"name": "Cafe B", "price_mxn": 65.0}

    r1, r2 = await asyncio.gather(
        client.put(f"/api/products/{product_id}", json=payload_a),
        client.put(f"/api/products/{product_id}", json=payload_b),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200

    final = await _get_product(client, product_id)

    # Validacion clave: el estado final es COHERENTE — el par (name, price_mxn)
    # corresponde a uno de los dos payloads completos, no a una mezcla.
    final_pair = (final["name"], final["price_mxn"])
    assert final_pair in (
        (payload_a["name"], payload_a["price_mxn"]),
        (payload_b["name"], payload_b["price_mxn"]),
    ), f"Estado inconsistente: {final_pair} no matchea ningun payload completo"


async def test_sale_snapshot_immune_a_edit_posterior(client):
    """Crear invoice con producto X @ precio P1; editar producto a P2;
    listar ventas del dia; el sale_item conserva P1 (desnormalizacion).
    """
    price_antes = 80.0
    price_despues = 160.0

    product_id = await _create_product(client, "Te", price_antes)

    invoice_resp = await client.post(
        "/api/invoices",
        json={
            "items": [{
                "product_id": product_id,
                "product_name": "Te",
                "price_mxn": price_antes,
                "quantity": 1,
            }],
        },
    )
    assert invoice_resp.status_code == 201
    payment_hash = invoice_resp.json()["payment_hash"]

    webhook = await client.post(
        "/api/webhooks/lnbits", json={"payment_hash": payment_hash}
    )
    assert webhook.json()["status"] == "confirmed"

    edit_resp = await client.put(
        f"/api/products/{product_id}",
        json={"name": "Te", "price_mxn": price_despues},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["price_mxn"] == price_despues

    today = datetime.now(timezone.utc).date().isoformat()
    sales_resp = await client.get(f"/api/sales?date={today}")
    assert sales_resp.status_code == 200

    matching_sales = [
        s for s in sales_resp.json() if s["payment_hash"] == payment_hash
    ]
    assert len(matching_sales) == 1
    sale = matching_sales[0]

    te_items = [i for i in sale["items"] if i["product_name"] == "Te"]
    assert len(te_items) == 1
    assert te_items[0]["price_mxn"] == price_antes, (
        f"sale_item deberia conservar el precio al momento de la venta "
        f"({price_antes}), no el precio actual del producto ({price_despues})"
    )
