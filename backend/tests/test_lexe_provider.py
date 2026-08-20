"""Tests del LexeWalletProvider contra un sidecar FALSO que imita el real.

El doble replica la API tal como se sondeó contra el sidecar de verdad (v0.10.2), incluidos
sus rechazos: sólo `payment?index=`, sin consulta por hash y sin endpoint de listado. Ese
comportamiento es la razón de existir de `provider_ref`, así que el test lo modela en vez de
asumir una API cómoda que no existe.

Lo verificado contra el sidecar REAL (no acá; queda en el run doc 05):
  - create_invoice de 5 sats → pagada, canal JIT abierto, preimage presente
  - pay_invoice con credencial `receive` → "Client lacks the required permission: pay_invoice"
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from domain.ports.wallet_provider import WalletProviderUnavailable
from infrastructure.lexe.lexe_wallet_provider import LexeWalletProvider

INDEX = "0000001787102161647-ln_69d3cebd937845e92e523866de473fcc03d0c9aca3e9597e9e9970360af70f31"
HASH = "69d3cebd937845e92e523866de473fcc03d0c9aca3e9597e9e9970360af70f31"


class FakeSidecar:
    """Imita al sidecar real, incluidos sus 400 cuando se pregunta de otra forma."""

    def __init__(self):
        self.completed: set[str] = set()
        self._server = None
        self.port = None

    def __enter__(self):
        outer = self

        class H(BaseHTTPRequestHandler):
            def _json(self, code, body):
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                path = urlparse(self.path).path
                n = int(self.headers.get("content-length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                if path == "/v1/node/create_invoice":
                    return self._json(200, {
                        "index": INDEX,
                        "invoice": f"lnbc{body['amount']}n1fake",
                        "payment_hash": HASH,
                        "amount": str(body["amount"]),
                        "created_at": 1787102161000,
                        "expires_at": 1787105761000,
                    })
                if path == "/v1/node/pay_invoice":
                    # Scope receive: el nodo real rechaza exactamente así.
                    return self._json(500, {
                        "code": 100,
                        "msg": "Failed to pay invoice: Unknown error: Client lacks the "
                               "required permission: pay_invoice",
                    })
                self._json(400, {"code": 7, "msg": "non-existent endpoint"})

            def do_GET(self):
                u = urlparse(self.path)
                q = parse_qs(u.query)
                if u.path != "/v1/node/payment":
                    # list_payments, payments, get_payment… todos 400 en el sidecar real
                    return self._json(400, {"code": 7, "msg": "non-existent endpoint"})
                if "index" not in q:
                    return self._json(400, {"code": 7, "msg": "index: Missing field"})
                idx = q["index"][0]
                status = "completed" if idx in outer.completed else "pending"
                self._json(200, {"payment": {"index": idx, "status": status,
                                             "status_msg": status, "amount": "5"}})

            def log_message(self, *a):
                pass

        self._server = HTTPServer(("127.0.0.1", 0), H)
        self.port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


async def test_create_invoice_maps_fields_and_keeps_the_index():
    with FakeSidecar() as sc:
        p = LexeWalletProvider(sc.url, invoice_expiry=3600)
        inv = await p.create_invoice("lexe-sidecar:cred", 5, "Cafe")
        assert inv.payment_hash == HASH
        assert inv.bolt11.startswith("lnbc")
        # Lexe da ms; nuestro contrato es segundos. Sin la división, la invoice parecería
        # vencer en el año 58000 y nunca expiraría.
        assert inv.expires_at == 1787105761
        assert inv.provider_ref == INDEX, "sin el index no se puede reconciliar después"


async def test_check_invoice_uses_the_index():
    with FakeSidecar() as sc:
        p = LexeWalletProvider(sc.url)
        assert await p.check_invoice("k", HASH, INDEX) is False
        sc.completed.add(INDEX)
        assert await p.check_invoice("k", HASH, INDEX) is True


async def test_check_without_provider_ref_fails_instead_of_saying_unpaid():
    """Devolver False sin poder preguntar diría 'no pagada' sobre una venta quizá cobrada."""
    with FakeSidecar() as sc:
        p = LexeWalletProvider(sc.url)
        with pytest.raises(WalletProviderUnavailable, match="provider_ref"):
            await p.check_invoice("k", HASH, None)


async def test_dead_sidecar_is_provider_unavailable():
    p = LexeWalletProvider("http://127.0.0.1:1")
    with pytest.raises(WalletProviderUnavailable):
        await p.create_invoice("k", 5, "Cafe")


async def test_lexe_never_provisions():
    """Igual que NWC: la wallet la crea el comercio. Así no hay altas a medias."""
    p = LexeWalletProvider("http://127.0.0.1:1")
    with pytest.raises(RuntimeError, match="no provisiona"):
        await p.provision_wallet("Cafe")
