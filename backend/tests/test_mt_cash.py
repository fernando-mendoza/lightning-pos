"""Tests de ventas en efectivo (Fase 1).

Lo que se protege acá, en orden de importancia:

1. **Que la venta en efectivo se VEA.** El bug que este trabajo vino a evitar es que el
   cajero cobre y el dueño no lo vea nunca, porque historial y reportes colgaban de la
   invoice. Un test que sólo verificara "el endpoint devuelve 200" no habría detectado eso.
2. **Que no se pueda cobrar dos veces la misma venta.** Una orden con QR vivo, o ya pagada
   por Lightning, no se cierra en efectivo.
3. **Que lo que ya funcionaba siga dando el mismo número.** Reescribimos el agregado de
   `invoices` a `orders`; si una venta Lightning empieza a contar distinto, rompimos algo.
"""

from .mt_common import BASE, new_client, pair, register


def _setup(c):
    a = register(c)
    dev, dhdr = pair(c, a["hdr"])
    return a, dhdr


def _product(c, a, price="50.00", name="Cafe"):
    return c.post(
        BASE + "/catalog/products", headers=a["hdr"], json={"name": name, "price_mxn": price}
    ).json()["id"]


def _order(c, dhdr, items):
    r = c.post(BASE + "/orders", headers=dhdr, json={"items": items})
    assert r.status_code == 201, r.text
    return r.json()


def _pay_lightning(c, dhdr, order_id):
    """Cobra una orden por Lightning de punta a punta (invoice + fake-pay + webhook)."""
    inv = c.post(BASE + f"/orders/{order_id}/invoice", headers=dhdr).json()
    fp = c.post(BASE + f"/testing/fake-pay/{inv['id']}").json()
    r = c.post(
        BASE + "/webhooks/lnbits",
        params={"secret": fp["webhook_secret"]},
        json={"payment_hash": fp["payment_hash"]},
    )
    assert r.json()["status"] == "confirmed"
    return inv


def test_cash_sale_is_visible_in_history_and_reports():
    """El caso que motivó todo: cobrar en efectivo y que el dueño lo vea."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a, price="100.00")
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])

    r = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["status"] == "paid"
    assert o["payment_method"] == "cash"
    assert o["paid_at"] is not None, "sin paid_at la venta no entra en el corte del día"

    # Historial de ventas: aparece, sin datos Lightning.
    sales = c.get(BASE + "/sales", headers=dhdr).json()
    mine = [s for s in sales if s["order_id"] == order["id"]]
    assert len(mine) == 1
    assert mine[0]["payment_method"] == "cash"
    assert mine[0]["amount_sats"] is None and mine[0]["payment_hash"] is None
    assert mine[0]["fx_rate"] is None, "en efectivo no hubo tipo de cambio que aplicar"

    # Reportes del dueño: suma en MXN y aporta 0 sats (no hubo bitcoin).
    s = c.get(BASE + "/reports/summary", headers=a["hdr"]).json()
    assert s["totals"]["count"] == 1
    assert s["totals"]["mxn"] == "100.00"
    assert s["totals"]["sats"] == 0
    assert s["totals"]["cash_mxn"] == "100.00"
    assert s["totals"]["lightning_mxn"] == "0.00"


def test_cash_receipt_survives_a_reload():
    """El recibo en efectivo se relee por `GET /orders/{id}` porque no hay invoice que
    consultar. Sin esto, volver atrás en la app dejaría el recibo en blanco."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a, price="100.00")
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])
    c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)

    r = c.get(BASE + f"/orders/{order['id']}", headers=dhdr)
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["payment_method"] == "cash" and o["status"] == "paid"
    assert o["total_mxn"] == "100.00" and o["paid_at"] is not None

    # Y no se filtra entre tenants.
    _, dhdr2 = _setup(c)
    assert c.get(BASE + f"/orders/{order['id']}", headers=dhdr2).status_code == 404


def test_cash_sale_absent_from_legacy_invoice_history():
    """`GET /invoices` es el contrato que consumen las apps YA PUBLICADAS. Una venta en
    efectivo no es una invoice y no debe aparecer ahí: si se colara, la app vieja
    intentaría leer bolt11/sats de algo que no los tiene."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a)
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])
    c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)

    invoices = c.get(BASE + "/invoices", headers=dhdr).json()
    assert all(i["order_id"] != order["id"] for i in invoices)


def test_cash_is_idempotent():
    """Reintentar por red inestable no puede duplicar la venta ni fallar en falso."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a)
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])

    first = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)
    second = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["paid_at"] == second.json()["paid_at"], "el segundo intento re-selló"

    s = c.get(BASE + "/reports/summary", headers=a["hdr"]).json()
    assert s["totals"]["count"] == 1, "la venta se contó dos veces"


def test_cash_rejected_while_invoice_is_live():
    """Guarda de doble cobro: hay un QR vivo que el cliente todavía puede pagar."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a)
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])
    c.post(BASE + f"/orders/{order['id']}/invoice", headers=dhdr)

    r = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)
    assert r.status_code == 400
    assert r.json()["detail"] == "order_not_open"


def test_cash_rejected_after_lightning_payment():
    """Ya se cobró por Lightning: cerrarla en efectivo sería cobrarla dos veces."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a)
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])
    _pay_lightning(c, dhdr, order["id"])

    r = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)
    assert r.status_code == 409
    assert r.json()["detail"] == "order_already_paid"

    s = c.get(BASE + "/reports/summary", headers=a["hdr"]).json()
    assert s["totals"]["count"] == 1 and s["totals"]["cash_mxn"] == "0.00"


def test_cash_rejected_on_zero_total():
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a, price="0.00", name="Gratis")
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])

    r = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)
    assert r.status_code == 400 and r.json()["detail"] == "empty_order"


def test_cash_cross_tenant_is_invisible():
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a)
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])

    _, dhdr2 = _setup(c)
    r = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr2)
    assert r.status_code == 404, "otro tenant no puede cerrar una orden ajena"


def test_reports_mix_cash_and_lightning():
    """El corte del día con las dos cosas: MXN suma todo, sats sólo la parte Lightning."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a, price="100.00")

    cash_order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])
    c.post(BASE + f"/orders/{cash_order['id']}/cash", headers=dhdr)

    ln_order = _order(c, dhdr, [{"description": "Libre", "qty": 1, "unit_price_mxn": "50.00"}])
    inv = _pay_lightning(c, dhdr, ln_order["id"])

    s = c.get(BASE + "/reports/summary", headers=a["hdr"]).json()
    t = s["totals"]
    assert t["count"] == 2
    assert t["mxn"] == "150.00", "el total en MXN es TODO lo cobrado"
    assert t["sats"] == inv["amount_sats"], "los sats son sólo lo cobrado por Lightning"
    assert t["cash_count"] == 1 and t["cash_mxn"] == "100.00"
    assert t["lightning_count"] == 1 and t["lightning_mxn"] == "50.00"

    # El desglose también baja al día y a la terminal, o el dueño ve el total y no puede
    # explicarlo.
    assert len(s["by_day"]) == 1
    assert s["by_day"][0]["cash_mxn"] == "100.00"
    assert s["by_day"][0]["lightning_mxn"] == "50.00"
    assert len(s["by_terminal"]) == 1
    assert s["by_terminal"][0]["mxn"] == "150.00"
    assert s["by_terminal"][0]["sats"] == inv["amount_sats"]


def test_reports_lightning_only_unchanged():
    """REGRESIÓN: el agregado pasó de `invoices` a `orders`. Una venta Lightning tiene que
    dar exactamente lo mismo que antes del cambio."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a, price="50.00")
    order = _order(
        c,
        dhdr,
        [
            {"product_id": pid, "qty": 2},
            {"description": "Propina", "qty": 1, "unit_price_mxn": "10.00"},
        ],
    )
    inv = _pay_lightning(c, dhdr, order["id"])

    s = c.get(BASE + "/reports/summary", headers=a["hdr"]).json()
    assert s["totals"]["count"] == 1
    assert s["totals"]["mxn"] == "110.00"
    assert s["totals"]["sats"] == 5500 == inv["amount_sats"]
    assert s["totals"]["cash_count"] == 0 and s["totals"]["cash_mxn"] == "0.00"


def test_unpaid_orders_never_count():
    """Un carrito abierto no es una venta. Si contara, el corte del día inflaría el
    ingreso con carritos que nadie pagó — y tampoco es ruido para el historial."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a, price="77.00")
    _order(c, dhdr, [{"product_id": pid, "qty": 1}])  # queda open, sin cobrar

    s = c.get(BASE + "/reports/summary", headers=a["hdr"]).json()
    assert s["totals"]["count"] == 0 and s["totals"]["mxn"] == "0.00"
    assert c.get(BASE + "/sales", headers=dhdr).json() == []


def test_history_keeps_showing_unpaid_attempts():
    """El historial de la app hoy muestra los intentos con QR que no se pagaron. El
    listado nuevo tiene que seguir mostrándolos: el cajero usa esa vista para responder
    '¿esa venta sí pasó?'. Quitarlos habría sido perder una función sin avisar."""
    c = new_client()
    a, dhdr = _setup(c)
    pid = _product(c, a, price="60.00")
    order = _order(c, dhdr, [{"product_id": pid, "qty": 1}])
    inv = c.post(BASE + f"/orders/{order['id']}/invoice", headers=dhdr).json()

    sales = c.get(BASE + "/sales", headers=dhdr).json()
    row = next(s for s in sales if s["order_id"] == order["id"])
    assert row["status"] == "invoiced", "el intento con QR vivo tiene que aparecer"
    assert row["paid_at"] is None
    assert row["amount_sats"] == inv["amount_sats"], "y con su dato Lightning"
    # El tipo de cambio viaja en el listado porque el historial REIMPRIME el recibo: sin
    # él, el ticket reimpreso saldría con "0 MXN/BTC".
    assert row["fx_rate"] is not None

    # Pero no cuenta como dinero cobrado.
    s = c.get(BASE + "/reports/summary", headers=a["hdr"]).json()
    assert s["totals"]["count"] == 0
