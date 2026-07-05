"""Helpers para los tests del API multi-tenant (/api/v2). No es un archivo de tests."""

import os
import uuid

import httpx

BASE = os.environ.get("BACKEND_URL", "http://backend:8000") + "/api/v2"


def new_client() -> httpx.Client:
    return httpx.Client(timeout=20)


def register(c: httpx.Client, tenant_name: str = "Cafe") -> dict:
    sfx = uuid.uuid4().hex[:10]
    email = f"u_{sfx}@t.mx"
    r = c.post(
        BASE + "/auth/register",
        json={"email": email, "password": "supersecret1", "name": "U", "tenant_name": tenant_name},
    )
    r.raise_for_status()
    d = r.json()
    return {
        "email": email,
        "token": d["access_token"],
        "tenant_id": d["tenant_id"],
        "hdr": {"Authorization": f"Bearer {d['access_token']}", "X-Tenant-Id": d["tenant_id"]},
    }


def pair(c: httpx.Client, hdr: dict, name: str = "Barra", role: str = "cashier"):
    code = c.post(BASE + "/pairing-codes", headers=hdr, json={"name": name, "role": role}).json()["code"]
    dev = c.post(BASE + "/pairing/redeem", json={"code": code}).json()["device_token"]
    return dev, {"Authorization": f"Bearer {dev}"}
