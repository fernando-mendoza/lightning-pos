"""Tests de integración: catálogo + órdenes + invoice + webhook endurecido (tenant-scoped)."""

from .mt_common import BASE, new_client, pair, register


def _setup(c):
    a = register(c)
    dev, dhdr = pair(c, a["hdr"])
    return a, dhdr


def test_catalog_crud_and_lookup():
    c = new_client()
    a, dhdr = _setup(c)
    # crear producto (manager)
    r = c.post(BASE + "/catalog/products", headers=a["hdr"],
               json={"name": "Cafe", "price_mxn": "50.00", "barcode": "750111"})
    assert r.status_code == 201
    # barcode duplicado -> 409
    r = c.post(BASE + "/catalog/products", headers=a["hdr"],
               json={"name": "Otro", "price_mxn": "1.00", "barcode": "750111"})
    assert r.status_code == 409
    # lookup por barcode (device token)
    r = c.get(BASE + "/catalog/products", params={"barcode": "750111"}, headers=dhdr)
    assert r.status_code == 200 and len(r.json()) == 1


def test_order_invoice_payment_flow():
    c = new_client()
    a, dhdr = _setup(c)
    pid = c.post(BASE + "/catalog/products", headers=a["hdr"],
                 json={"name": "Cafe", "price_mxn": "50.00"}).json()["id"]
    # orden: producto x2 + línea libre 10 => 110 MXN
    r = c.post(BASE + "/orders", headers=dhdr, json={"items": [
        {"product_id": pid, "qty": 2},
        {"description": "Propina", "qty": 1, "unit_price_mxn": "10.00"},
    ]})
    assert r.status_code == 201
    order = r.json()
    assert float(order["total_mxn"]) == 110.0
    # invoice: FX fake 2,000,000 MXN/BTC => 50 sats/MXN => 5500 sats
    r = c.post(BASE + f"/orders/{order['id']}/invoice", headers=dhdr)
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["amount_sats"] == 5500 and inv["status"] == "pending"
    # re-invoice de la misma orden -> 400
    assert c.post(BASE + f"/orders/{order['id']}/invoice", headers=dhdr).status_code == 400
    # simular pago
    fp = c.post(BASE + f"/testing/fake-pay/{inv['id']}").json()
    # webhook secret incorrecto -> 403
    assert c.post(BASE + "/webhooks/lnbits", params={"secret": "wrong"},
                  json={"payment_hash": fp["payment_hash"]}).status_code == 403
    # webhook correcto -> confirmed
    r = c.post(BASE + "/webhooks/lnbits", params={"secret": fp["webhook_secret"]},
               json={"payment_hash": fp["payment_hash"]})
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    # webhook idempotente
    assert c.post(BASE + "/webhooks/lnbits", params={"secret": fp["webhook_secret"]},
                  json={"payment_hash": fp["payment_hash"]}).json()["status"] == "confirmed"
    # invoice pagada
    assert c.get(BASE + f"/invoices/{inv['id']}", headers=dhdr).json()["status"] == "paid"


def test_cross_tenant_invoice_hidden():
    c = new_client()
    a, dhdr = _setup(c)
    pid = c.post(BASE + "/catalog/products", headers=a["hdr"],
                 json={"name": "X", "price_mxn": "5.00"}).json()["id"]
    oid = c.post(BASE + "/orders", headers=dhdr, json={"items": [{"product_id": pid, "qty": 1}]}).json()["id"]
    iid = c.post(BASE + f"/orders/{oid}/invoice", headers=dhdr).json()["id"]
    # otro tenant no puede ver la invoice
    _, dhdr2 = _setup(c)
    assert c.get(BASE + f"/invoices/{iid}", headers=dhdr2).status_code == 404
