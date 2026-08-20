"""Tests HTTP del alta de wallet BYO (NWC).

Cubren el contrato del endpoint y el camino completo del 503 honesto: un tenant con NWC
conectado cuyo relay no responde debe recibir `lightning_unavailable`, no un 500. El RPC
NIP-47 en sí se prueba en test_nwc_client.py contra un relay en proceso.
"""

import secrets

from .mt_common import BASE, new_client, pair, register

PK = secrets.token_hex(32)
SEC = secrets.token_hex(32)


def _uri(relay: str) -> str:
    return f"nostr+walletconnect://{PK}?relay={relay}&secret={SEC}"


def test_connect_rejects_garbage():
    c = new_client()
    a = register(c)
    r = c.post(BASE + "/wallet/nwc", headers=a["hdr"], json={"connection": "https://no-es-nwc.example/x" * 2})
    assert r.status_code == 400
    assert "nostr+walletconnect" in r.json()["detail"]


def test_connect_requires_relay_and_secret():
    c = new_client()
    a = register(c)
    r = c.post(
        BASE + "/wallet/nwc", headers=a["hdr"],
        json={"connection": f"nostr+walletconnect://{PK}?relay=wss://r.example"},
    )
    assert r.status_code == 400
    assert "secret" in r.json()["detail"]


def test_connect_switches_tenant_to_nwc_and_declares_lightning():
    c = new_client()
    a = register(c)
    _dev, dhdr = pair(c, a["hdr"])

    r = c.post(BASE + "/wallet/nwc", headers=a["hdr"], json={"connection": _uri("ws://127.0.0.1:1")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "nwc"
    assert "lightning" in body["payment_methods"]
    # el secreto no puede volver en la respuesta
    assert SEC not in r.text

    me = c.get(BASE + "/terminal/me", headers=dhdr).json()
    assert "lightning" in me["payment_methods"]


def test_invoice_against_dead_relay_is_honest_503():
    """El camino completo del fallo: NWC conectado, relay muerto → 503, jamás 500."""
    c = new_client()
    a = register(c)
    _dev, dhdr = pair(c, a["hdr"])
    c.post(BASE + "/wallet/nwc", headers=a["hdr"], json={"connection": _uri("ws://127.0.0.1:1")})
    pid = c.post(
        BASE + "/catalog/products", headers=a["hdr"], json={"name": "Cafe", "price_mxn": "50.00"}
    ).json()["id"]
    order = c.post(BASE + "/orders", headers=dhdr, json={"items": [{"product_id": pid, "qty": 1}]}).json()

    r = c.post(BASE + f"/orders/{order['id']}/invoice", headers=dhdr, timeout=30)
    assert r.status_code == 503, f"esperaba 503 honesto, llegó {r.status_code}: {r.text}"
    assert r.json()["detail"] == "lightning_unavailable"


def test_cash_still_works_for_nwc_tenant():
    """El efectivo no depende del relay: sigue cobrando aunque NWC esté conectado y muerto."""
    c = new_client()
    a = register(c)
    _dev, dhdr = pair(c, a["hdr"])
    c.post(BASE + "/wallet/nwc", headers=a["hdr"], json={"connection": _uri("ws://127.0.0.1:1")})
    pid = c.post(
        BASE + "/catalog/products", headers=a["hdr"], json={"name": "Pan", "price_mxn": "30.00"}
    ).json()["id"]
    order = c.post(BASE + "/orders", headers=dhdr, json={"items": [{"product_id": pid, "qty": 1}]}).json()
    r = c.post(BASE + f"/orders/{order['id']}/cash", headers=dhdr)
    assert r.status_code == 200 and r.json()["status"] == "paid"


# ---- alta por sidecar de Lexe ----

def test_connect_lexe_fails_clearly_when_no_sidecar_configured():
    """En el stack de tests no hay sidecar: el error debe decir POR QUÉ, no ser un 500."""
    c = new_client()
    a = register(c)
    r = c.post(BASE + "/wallet/lexe", headers=a["hdr"])
    assert r.status_code == 400, r.text
    assert "sidecar" in r.json()["detail"]


def test_connect_lexe_requires_owner():
    """El punto por donde entra el dinero del negocio no lo cambia un cajero."""
    c = new_client()
    a = register(c)
    _dev, dhdr = pair(c, a["hdr"])
    r = c.post(BASE + "/wallet/lexe", headers=dhdr)  # token de terminal, no de owner
    assert r.status_code in (401, 403), r.text
