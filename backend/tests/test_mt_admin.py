"""Tests de integración: admin del tenant — password, miembros, renames, reportes."""

import uuid

from .mt_common import BASE, new_client, pair, register


def _login(c, email, password):
    return c.post(BASE + "/auth/login", json={"email": email, "password": password})


def test_change_password():
    c = new_client()
    a = register(c)
    hdr = {"Authorization": a["hdr"]["Authorization"]}
    # password actual incorrecto -> 400
    r = c.post(BASE + "/auth/change-password", headers=hdr,
               json={"current_password": "nope-nope-1", "new_password": "newsecret99"})
    assert r.status_code == 400
    # correcto -> 204; el password viejo deja de servir y el nuevo funciona
    r = c.post(BASE + "/auth/change-password", headers=hdr,
               json={"current_password": "supersecret1", "new_password": "newsecret99"})
    assert r.status_code == 204
    assert _login(c, a["email"], "supersecret1").status_code == 401
    assert _login(c, a["email"], "newsecret99").status_code == 200


def test_members_lifecycle():
    c = new_client()
    a = register(c)
    email = f"cajero_{uuid.uuid4().hex[:8]}@t.mx"
    # owner crea cashier
    r = c.post(BASE + "/members", headers=a["hdr"],
               json={"email": email, "password": "cashierpass1", "role": "cashier"})
    assert r.status_code == 201, r.text
    member = r.json()
    assert member["role"] == "cashier"
    # el nuevo miembro puede loguearse y ve la membership del tenant
    r = _login(c, email, "cashierpass1")
    assert r.status_code == 200
    assert any(m["tenant_id"] == a["tenant_id"] for m in r.json()["memberships"])
    # duplicado -> 409
    r = c.post(BASE + "/members", headers=a["hdr"],
               json={"email": email, "password": "cashierpass1", "role": "cashier"})
    assert r.status_code == 409
    # listado incluye owner + cashier
    r = c.get(BASE + "/members", headers=a["hdr"])
    assert r.status_code == 200 and len(r.json()) == 2
    # el cashier no puede administrar miembros (requires_manager)
    ctoken = _login(c, email, "cashierpass1").json()["access_token"]
    chdr = {"Authorization": f"Bearer {ctoken}", "X-Tenant-Id": a["tenant_id"]}
    assert c.get(BASE + "/members", headers=chdr).status_code == 403
    # owner elimina al cashier; no puede eliminarse a sí mismo (owner)
    r = c.delete(BASE + f"/members/{member['user_id']}", headers=a["hdr"])
    assert r.status_code == 204
    me = c.get(BASE + "/me", headers={"Authorization": a["hdr"]["Authorization"]}).json()
    r = c.delete(BASE + f"/members/{me['user_id']}", headers=a["hdr"])
    assert r.status_code == 400


def test_manager_cannot_create_manager():
    c = new_client()
    a = register(c)
    memail = f"mgr_{uuid.uuid4().hex[:8]}@t.mx"
    r = c.post(BASE + "/members", headers=a["hdr"],
               json={"email": memail, "password": "managerpass1", "role": "manager"})
    assert r.status_code == 201
    mtoken = _login(c, memail, "managerpass1").json()["access_token"]
    mhdr = {"Authorization": f"Bearer {mtoken}", "X-Tenant-Id": a["tenant_id"]}
    # manager crea cashier: OK
    r = c.post(BASE + "/members", headers=mhdr,
               json={"email": f"x_{uuid.uuid4().hex[:8]}@t.mx", "password": "cashierpass1",
                     "role": "cashier"})
    assert r.status_code == 201
    # manager crea manager: 403 (solo owner)
    r = c.post(BASE + "/members", headers=mhdr,
               json={"email": f"y_{uuid.uuid4().hex[:8]}@t.mx", "password": "managerpass1",
                     "role": "manager"})
    assert r.status_code == 403


def test_manager_catalog_listing():
    c = new_client()
    a = register(c)
    dev, dhdr = pair(c, a["hdr"])
    pid = c.post(BASE + "/catalog/products", headers=a["hdr"],
                 json={"name": "Cafe", "price_mxn": "50.00"}).json()["id"]
    c.delete(BASE + f"/catalog/products/{pid}", headers=a["hdr"])  # soft-delete
    # el listado manager ve el inactivo si lo pide; el default no
    r = c.get(BASE + "/catalog/manager/products", headers=a["hdr"],
              params={"include_inactive": "true"})
    assert r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["active"] is False
    r = c.get(BASE + "/catalog/manager/products", headers=a["hdr"])
    assert r.status_code == 200 and r.json() == []
    # el device token NO sirve en la ruta manager
    assert c.get(BASE + "/catalog/manager/products", headers=dhdr).status_code == 401


def test_tenant_and_terminal_rename():
    c = new_client()
    a = register(c, "Cafe Viejo")
    # rename tenant (owner)
    r = c.patch(BASE + "/tenants/me", headers=a["hdr"], json={"name": "Cafe Nuevo"})
    assert r.status_code == 200 and r.json()["name"] == "Cafe Nuevo"
    # rename terminal
    pair(c, a["hdr"], name="Barra")
    tid = c.get(BASE + "/terminals", headers=a["hdr"]).json()[0]["id"]
    r = c.patch(BASE + f"/terminals/{tid}", headers=a["hdr"], json={"name": "Caja 2"})
    assert r.status_code == 200 and r.json()["name"] == "Caja 2"
    # cross-tenant -> 404
    b = register(c, "Otro")
    r = c.patch(BASE + f"/terminals/{tid}", headers=b["hdr"], json={"name": "hack"})
    assert r.status_code == 404


def test_reports_summary():
    c = new_client()
    a = register(c)
    dev, dhdr = pair(c, a["hdr"], name="Barra")
    pid = c.post(BASE + "/catalog/products", headers=a["hdr"],
                 json={"name": "Cafe", "price_mxn": "50.00"}).json()["id"]
    oid = c.post(BASE + "/orders", headers=dhdr,
                 json={"items": [{"product_id": pid, "qty": 2},
                                 {"description": "Propina", "qty": 1, "unit_price_mxn": "10.00"}]}
                 ).json()["id"]
    inv = c.post(BASE + f"/orders/{oid}/invoice", headers=dhdr).json()
    fp = c.post(BASE + f"/testing/fake-pay/{inv['id']}").json()
    c.post(BASE + "/webhooks/lnbits", params={"secret": fp["webhook_secret"]},
           json={"payment_hash": fp["payment_hash"]})
    # resumen (rango default: últimos 30 días)
    r = c.get(BASE + "/reports/summary", headers=a["hdr"])
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["totals"] == {"count": 1, "mxn": "110.00", "sats": 5500}
    assert len(s["by_day"]) == 1 and s["by_day"][0]["mxn"] == "110.00"
    assert len(s["by_terminal"]) == 1 and s["by_terminal"][0]["name"] == "Barra"
    # rango sin ventas -> ceros
    r = c.get(BASE + "/reports/summary", headers=a["hdr"],
              params={"from": "2000-01-01", "to": "2000-01-31"})
    assert r.json()["totals"]["count"] == 0
    # el device token NO sirve para reportes (es endpoint de manager/JWT)
    assert c.get(BASE + "/reports/summary", headers=dhdr).status_code == 401
    # rango inválido -> 400
    r = c.get(BASE + "/reports/summary", headers=a["hdr"],
              params={"from": "2026-02-01", "to": "2026-01-01"})
    assert r.status_code == 400
