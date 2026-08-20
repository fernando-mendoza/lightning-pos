"""El alta pública de tenants está cerrada salvo que se habilite explícitamente.

Por qué existe este test: `POST /api/v2/auth/register` provisiona una wallet LNbits en
NUESTRA instancia (custodial, un wallet por tenant). Dejarlo abierto = custodiar fondos de
terceros, lo cual contradice el "no-custodial" publicado en App Store y Google Play y tiene
implicaciones regulatorias en MX.

Es un control de cumplimiento, no una feature: si alguien invierte el default sin querer,
esto tiene que ponerse rojo.

Corre en `docker-compose.test.yml`, cuyo backend **no** setea `LPOS_REGISTRATION_ENABLED`
→ toma el default de `config.py`, que es `False`. Ese es justamente el caso bajo prueba.
El camino contrario (alta habilitada y funcionando) lo cubren los `test_mt_*` en
`docker-compose.test-mt.yml`, que sí lo setean a "1".

Contexto: hub → workspaces/runs/2026-08-02-lightning-pos-saas-strategy/05-fase-0-y-feature-flags.md
"""

import httpx
import pytest

from tests.conftest import BACKEND_URL

ALTA = {
    "email": "gate-test@example.com",
    "password": "unaContraseñaLarga123",
    "name": "Gate Test",
    "tenant_name": "Comercio Gate Test",
}


@pytest.mark.asyncio
async def test_alta_cerrada_responde_403():
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as c:
        r = await c.post("/api/v2/auth/register", json=ALTA)
    assert r.status_code == 403, f"esperaba 403, llegó {r.status_code}: {r.text}"
    assert r.json()["detail"] == "registration_disabled"


@pytest.mark.asyncio
async def test_el_gate_corta_antes_de_validar_el_body():
    """Un body inválido igual debe dar 403, no 422.

    Prueba que el gate corre en `dependencies=[...]` y no dentro del handler: si diera 422
    significaría que FastAPI ya resolvió el body —y con él `get_session` y `get_wallet`—
    antes de rechazar, o sea que abrió transacción y habló con LNbits para nada.
    """
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as c:
        r = await c.post("/api/v2/auth/register", json={})
    assert r.status_code == 403, f"esperaba 403 (gate antes del body), llegó {r.status_code}"


@pytest.mark.asyncio
async def test_el_gate_no_rompe_el_resto_de_la_api():
    """Cerrar el alta no afecta a los demás endpoints."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as c:
        r = await c.get("/api/health")
    assert r.status_code == 200, f"esperaba 200, llegó {r.status_code}: {r.text}"


# Nota para quien venga después: acá NO se puede afirmar nada sobre
# `POST /api/v2/auth/login`. Este compose levanta el stack single-tenant sobre SQLite y las
# rutas /api/v2 necesitan las tablas multi-tenant de Postgres → responden 500. Es una
# condición preexistente del entorno de test, no del gate. Para probar el camino v2 completo
# están los `test_mt_*` en docker-compose.test-mt.yml.
#
# De paso, ese contraste es evidencia a favor del diseño: en el MISMO stack donde
# `/api/v2/auth/login` da 500 por falta de DB, `/api/v2/auth/register` responde 403 limpio.
# O sea que el gate corta de verdad antes de resolver `get_session`.
