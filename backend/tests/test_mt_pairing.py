"""Tests de integración del API multi-tenant: cuentas + pairing + aislamiento."""

from .mt_common import BASE, new_client, pair, register


def test_register_login_me():
    c = new_client()
    a = register(c)
    # me
    r = c.get(BASE + "/me", headers={"Authorization": f"Bearer {a['token']}"})
    assert r.status_code == 200
    assert len(r.json()["memberships"]) == 1
    assert r.json()["memberships"][0]["role"] == "owner"
    # login
    r = c.post(BASE + "/auth/login", json={"email": a["email"], "password": "supersecret1"})
    assert r.status_code == 200 and r.json()["access_token"]
    # bad password
    r = c.post(BASE + "/auth/login", json={"email": a["email"], "password": "nope"})
    assert r.status_code == 401


def test_duplicate_email():
    c = new_client()
    a = register(c)
    r = c.post(BASE + "/auth/register",
               json={"email": a["email"], "password": "supersecret1", "tenant_name": "dup"})
    assert r.status_code == 409


def test_pairing_and_terminal():
    c = new_client()
    a = register(c)
    r = c.post(BASE + "/pairing-codes", headers=a["hdr"], json={"name": "Mesa 1", "role": "cashier"})
    assert r.status_code == 201
    pc = r.json()
    assert pc["pairing_payload"]["server_url"] and pc["pairing_payload"]["code"] == pc["code"]
    # redeem
    r = c.post(BASE + "/pairing/redeem", json={"code": pc["code"], "device_name": "iPhone"})
    assert r.status_code == 200
    dev = r.json()
    assert dev["tenant"]["id"] == a["tenant_id"] and dev["terminal"]["role"] == "cashier"
    # el nombre del pairing code (elegido por el manager) gana sobre device_name
    assert dev["terminal"]["name"] == "Mesa 1"
    # terminal/me
    r = c.get(BASE + "/terminal/me", headers={"Authorization": f"Bearer {dev['device_token']}"})
    assert r.status_code == 200 and r.json()["tenant_id"] == a["tenant_id"]
    # single-use: re-redeem blocked
    r = c.post(BASE + "/pairing/redeem", json={"code": pc["code"]})
    assert r.status_code == 400


def test_tenant_isolation_admin():
    c = new_client()
    a = register(c, "Cafe A")
    b = register(c, "Cafe B")
    # owner B intenta crear pairing-code en tenant A -> 403
    r = c.post(BASE + "/pairing-codes",
               headers={"Authorization": f"Bearer {b['token']}", "X-Tenant-Id": a["tenant_id"]},
               json={"name": "x", "role": "cashier"})
    assert r.status_code == 403


def test_revoke_terminal_invalidates_token():
    c = new_client()
    a = register(c)
    dev, dhdr = pair(c, a["hdr"])
    # terminal activa
    assert c.get(BASE + "/terminal/me", headers=dhdr).status_code == 200
    # revoca
    tid = c.get(BASE + "/terminals", headers=a["hdr"]).json()[0]["id"]
    assert c.post(BASE + f"/terminals/{tid}/revoke", headers=a["hdr"]).status_code == 200
    # device token ahora inválido
    assert c.get(BASE + "/terminal/me", headers=dhdr).status_code == 401
