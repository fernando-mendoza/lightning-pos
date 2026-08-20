"""Tests de capacidades de cobro por tenant.

El bug que esto viene a evitar ya ocurrió dos veces, de formas distintas:

1. **AgentykCo**: dado de alta con `lnbits_wallet_id` en NULL. El alta "funcionó", el tenant
   creía que podía cobrar con bitcoin, y nunca pudo. Nadie se enteró hasta el censo.
2. **La instancia caída**: cuando LNbits dejó de existir, cada intento de cobro salía como
   500 y el cajero leía "Algo salió mal" — culpando a la app por un fallo del proveedor.

Lo que se protege: que el backend declare lo que el tenant puede cobrar DE VERDAD, y que un
proveedor ausente nunca se disfrace de error nuestro.
"""

from domain.capabilities import wallet_is_usable

from .mt_common import BASE, new_client, pair, register


def _wallet(provider="lnbits", wallet_id="w123", key="enc:v1:xxx"):
    return wallet_is_usable(provider, wallet_id, key)


# ---- unit: qué cuenta como wallet utilizable ----

def test_wallet_without_id_is_not_usable():
    """El caso AgentykCo: llave guardada, wallet_id en NULL. No puede cobrar."""
    assert _wallet(wallet_id=None) is False


def test_wallet_without_key_is_not_usable():
    assert _wallet(key="") is False


def test_wallet_with_nothing_is_not_usable():
    assert _wallet(provider=None, wallet_id=None, key=None) is False


def test_complete_wallet_is_usable():
    assert _wallet() is True


# ---- integración: lo que la app lee para decidir qué ofrecer ----

def test_terminal_me_declares_payment_methods():
    c = new_client()
    a = register(c)
    _dev, dhdr = pair(c, a["hdr"])

    r = c.get(BASE + "/terminal/me", headers=dhdr)
    assert r.status_code == 200, r.text
    body = r.json()

    assert "payment_methods" in body, (
        "sin este campo la app no tiene cómo saber qué ofrecer y vuelve a prometer "
        "cobro con bitcoin cuando no hay proveedor"
    )
    assert "cash" in body["payment_methods"], "el efectivo no depende de nadie externo"
    # En tests el wallet fake provisiona wallet_id, así que Lightning sí está disponible.
    assert "lightning" in body["payment_methods"]


def test_lightning_path_still_works_when_available():
    """Regresión: la compuerta nueva no debe romper el camino feliz."""
    c = new_client()
    a = register(c)
    _dev, dhdr = pair(c, a["hdr"])
    pid = c.post(
        BASE + "/catalog/products", headers=a["hdr"], json={"name": "Cafe", "price_mxn": "50.00"}
    ).json()["id"]
    order = c.post(BASE + "/orders", headers=dhdr, json={"items": [{"product_id": pid, "qty": 1}]}).json()

    r = c.post(BASE + f"/orders/{order['id']}/invoice", headers=dhdr)
    assert r.status_code == 201, r.text
    assert r.json()["bolt11"]
