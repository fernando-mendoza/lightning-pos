"""Tests del cliente NIP-47 contra un relay+wallet EN PROCESO.

No es un mock del cliente: es la contraparte real del protocolo (relay websocket mínimo +
wallet service que descifra, ejecuta y responde firmado), construida con las mismas
primitivas. Si la firma, el cifrado, el id de evento o la suscripción están mal, esto NO
pasa. Lo que no cubre: un relay público real y una wallet comercial real — eso es la
verificación de la Fase B con una wallet de verdad, y está dicho en el run.
"""

from __future__ import annotations

import asyncio
import json
import secrets

import pytest
import websockets

from infrastructure.nwc import nip44
from infrastructure.nwc.client import NWCError, rpc
from infrastructure.nwc.nostr import (
    KIND_INFO,
    KIND_REQUEST,
    event_id,
    nip04_decrypt,
    nip04_encrypt,
    pubkey_xonly,
    sign_event,
)
from infrastructure.nwc.uri import NWCConnection, NWCUriError, parse_nwc_uri
from domain.ports.wallet_provider import WalletProviderUnavailable


# ---------- primitivas ----------

def test_event_id_matches_nip01_vector():
    """Vector conocido: el id es el sha256 de la serialización canónica NIP-01."""
    # Vector construido con la serialización de referencia (verificable a mano):
    # [0,"a"*64,1700000000,1,[],"hola"]
    eid = event_id("a" * 64, 1700000000, 1, [], "hola")
    import hashlib

    expected = hashlib.sha256(
        '[0,"' + "a" * 64 + '",1700000000,1,[],"hola"]'.encode().decode()
    ).hexdigest() if False else hashlib.sha256(
        json.dumps([0, "a" * 64, 1700000000, 1, [], "hola"], separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert eid == expected


def test_sign_event_verifies_with_schnorr():
    from coincurve import PublicKeyXOnly

    sk = secrets.token_hex(32)
    ev = sign_event(sk, KIND_REQUEST, [["p", "b" * 64]], "contenido")
    assert ev["pubkey"] == pubkey_xonly(sk)
    assert PublicKeyXOnly(bytes.fromhex(ev["pubkey"])).verify(
        bytes.fromhex(ev["sig"]), bytes.fromhex(ev["id"])
    )


def test_nip04_roundtrip_both_directions():
    a, b = secrets.token_hex(32), secrets.token_hex(32)
    pa, pb = pubkey_xonly(a), pubkey_xonly(b)
    msg = '{"method":"make_invoice","params":{"amount":10000}} · acentos y ñ'
    assert nip04_decrypt(b, pa, nip04_encrypt(a, pb, msg)) == msg
    assert nip04_decrypt(a, pb, nip04_encrypt(b, pa, msg)) == msg


def test_parse_uri_valid_and_invalid():
    pk, sec = "c" * 64, "d" * 64
    conn = parse_nwc_uri(f"nostr+walletconnect://{pk}?relay=wss://r.example&secret={sec}")
    assert (conn.wallet_pubkey, conn.relay_url, conn.secret) == (pk, "wss://r.example", sec)
    assert conn.redacted().startswith("nwc:cccccccc")
    assert sec not in conn.redacted(), "el secreto no puede aparecer en logs"

    for bad in [
        "https://no-es-nwc.example",
        f"nostr+walletconnect://corto?relay=wss://r&secret={sec}",
        f"nostr+walletconnect://{pk}?secret={sec}",  # sin relay
        f"nostr+walletconnect://{pk}?relay=wss://r",  # sin secret
        f"nostr+walletconnect://{pk}?relay=ws://inseguro&secret={sec}",  # ws:// sin permitir
    ]:
        with pytest.raises(NWCUriError):
            parse_nwc_uri(bad)

    # ws:// sí pasa cuando se permite explícitamente (tests / relay local)
    parse_nwc_uri(f"nostr+walletconnect://{pk}?relay=ws://local&secret={sec}", allow_insecure_relay=True)


# ---------- relay + wallet service en proceso ----------

class FakeWalletRelay:
    """Relay websocket mínimo + wallet service NIP-47 en el mismo proceso.

    `encryption_advertised`: contenido del tag `encryption` del info event (None = sin tag,
    que es el caso legado). `settled` marca qué payment_hash responde como pagado.
    """

    def __init__(
        self,
        *,
        encryption_advertised: str | None = "nip04 nip44_v2",
        wallet_speaks: str | None = None,
    ):
        self.wallet_secret = secrets.token_hex(32)
        self.wallet_pubkey = pubkey_xonly(self.wallet_secret)
        self.encryption_advertised = encryption_advertised
        # Un wallet real habla lo mejor que anuncia; el fake se mantiene consistente salvo
        # que el test fuerce otra cosa.
        if wallet_speaks is None:
            adv = encryption_advertised or "nip04"
            wallet_speaks = "nip44_v2" if "nip44_v2" in adv else "nip04"
        self.wallet_speaks = wallet_speaks
        self.settled: set[str] = set()
        self.requests_seen: list[dict] = []
        self._server = None
        self.port = None

    async def __aenter__(self):
        self._server = await websockets.serve(self._handler, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        await self._server.wait_closed()

    def connection_uri(self, client_secret: str) -> str:
        return (
            f"nostr+walletconnect://{self.wallet_pubkey}"
            f"?relay=ws://127.0.0.1:{self.port}&secret={client_secret}"
        )

    def _info_event(self) -> dict:
        tags = [["encryption", self.encryption_advertised]] if self.encryption_advertised else []
        return sign_event(self.wallet_secret, KIND_INFO, tags, "make_invoice lookup_invoice")

    async def _handler(self, ws):
        async for raw in ws:
            msg = json.loads(raw)
            if msg[0] == "REQ":
                sub, filt = msg[1], msg[2]
                if KIND_INFO in filt.get("kinds", []):
                    await ws.send(json.dumps(["EVENT", sub, self._info_event()]))
                    await ws.send(json.dumps(["EOSE", sub]))
                else:
                    # suscripción a respuestas: se sirven al llegar el EVENT del request
                    await ws.send(json.dumps(["EOSE", sub]))
                    self._resp_sub = (sub, filt)
            elif msg[0] == "EVENT":
                ev = msg[1]
                await ws.send(json.dumps(["OK", ev["id"], True, ""]))
                if ev["kind"] != KIND_REQUEST:
                    continue
                if self.wallet_speaks == "nip44_v2":
                    body = json.loads(nip44.decrypt(self.wallet_secret, ev["pubkey"], ev["content"]))
                else:
                    body = json.loads(nip04_decrypt(self.wallet_secret, ev["pubkey"], ev["content"]))
                self.requests_seen.append(body)
                reply = self._dispatch(body)
                if self.wallet_speaks == "nip44_v2":
                    content = nip44.encrypt(self.wallet_secret, ev["pubkey"], json.dumps(reply))
                else:
                    content = nip04_encrypt(self.wallet_secret, ev["pubkey"], json.dumps(reply))
                resp = sign_event(
                    self.wallet_secret, 23195, [["p", ev["pubkey"]], ["e", ev["id"]]], content
                )
                sub, _f = self._resp_sub
                await ws.send(json.dumps(["EVENT", sub, resp]))

    def _dispatch(self, body: dict) -> dict:
        m, p = body["method"], body.get("params", {})
        if m == "make_invoice":
            return {
                "result_type": m,
                "error": None,
                "result": {
                    "type": "incoming",
                    "invoice": f"lnbc_fake_{p['amount']}",
                    "payment_hash": "e" * 64,
                    "amount": p["amount"],
                    "created_at": 1700000000,
                    "expires_at": 1700000000 + p.get("expiry", 300),
                },
            }
        if m == "lookup_invoice":
            h = p.get("payment_hash", "")
            if h in self.settled:
                return {"result_type": m, "error": None,
                        "result": {"payment_hash": h, "settled_at": 1700000100, "preimage": "f" * 64}}
            if h == "e" * 64:
                return {"result_type": m, "error": None,
                        "result": {"payment_hash": h, "settled_at": None, "preimage": None}}
            return {"result_type": m, "error": {"code": "NOT_FOUND", "message": "no such invoice"}, "result": None}
        return {"result_type": m, "error": {"code": "NOT_IMPLEMENTED", "message": m}, "result": None}


async def _conn_for(relay: FakeWalletRelay) -> NWCConnection:
    return parse_nwc_uri(relay.connection_uri(secrets.token_hex(32)), allow_insecure_relay=True)


async def test_rpc_make_invoice_end_to_end():
    async with FakeWalletRelay() as relay:
        conn = await _conn_for(relay)
        result = await rpc(conn, "make_invoice", {"amount": 10000, "description": "cafe", "expiry": 300})
        assert result["invoice"].startswith("lnbc_fake_")
        assert result["payment_hash"] == "e" * 64
        # el wallet recibió lo que mandamos, descifrado con NUESTRA llave de conexión
        assert relay.requests_seen[0]["params"]["amount"] == 10000


async def test_rpc_lookup_pending_and_settled():
    async with FakeWalletRelay() as relay:
        conn = await _conn_for(relay)
        pending = await rpc(conn, "lookup_invoice", {"payment_hash": "e" * 64})
        assert not pending.get("settled_at")
        relay.settled.add("e" * 64)
        settled = await rpc(conn, "lookup_invoice", {"payment_hash": "e" * 64})
        assert settled["settled_at"] and settled["preimage"]


async def test_rpc_error_surfaces_with_code():
    async with FakeWalletRelay() as relay:
        conn = await _conn_for(relay)
        with pytest.raises(NWCError) as ei:
            await rpc(conn, "lookup_invoice", {"payment_hash": "0" * 64})
        assert ei.value.code == "NOT_FOUND"


async def test_nip44_only_wallet_now_works():
    """El caso Lexe: wallet que SÓLO habla nip44_v2. Antes fallaba con nombre; ahora cobra."""
    async with FakeWalletRelay(encryption_advertised="nip44_v2", wallet_speaks="nip44_v2") as relay:
        conn = await _conn_for(relay)
        result = await rpc(conn, "make_invoice", {"amount": 5000, "description": "cafe"})
        assert result["payment_hash"]
        assert relay.requests_seen[0]["params"]["amount"] == 5000


async def test_nip44_preferred_when_both_advertised():
    """Con ambos esquemas anunciados se negocia hacia arriba (nip44), no hacia nip04."""
    async with FakeWalletRelay(encryption_advertised="nip04 nip44_v2", wallet_speaks="nip44_v2") as relay:
        conn = await _conn_for(relay)
        result = await rpc(conn, "make_invoice", {"amount": 7000})
        assert result["payment_hash"]


async def test_nip04_only_wallet_still_works():
    """Regresión: un wallet que sólo anuncia nip04 sigue cobrando (Coinos y wallets legadas)."""
    async with FakeWalletRelay(encryption_advertised="nip04") as relay:
        conn = await _conn_for(relay)
        result = await rpc(conn, "make_invoice", {"amount": 3000})
        assert result["payment_hash"]
        assert relay.wallet_speaks == "nip04"


async def test_no_common_scheme_fails_loud():
    """Un wallet con esquemas desconocidos debe fallar CON NOMBRE, no degradarse en silencio."""
    async with FakeWalletRelay(encryption_advertised="nip99_experimental") as relay:
        conn = await _conn_for(relay)
        with pytest.raises(WalletProviderUnavailable, match="esquema"):
            await rpc(conn, "make_invoice", {"amount": 1000})


async def test_legacy_wallet_without_encryption_tag_works():
    """Sin tag `encryption` (wallets viejos) se asume nip04 y funciona."""
    async with FakeWalletRelay(encryption_advertised=None) as relay:
        conn = await _conn_for(relay)
        result = await rpc(conn, "make_invoice", {"amount": 2000})
        assert result["payment_hash"]


async def test_unreachable_relay_is_provider_unavailable():
    conn = parse_nwc_uri(
        f"nostr+walletconnect://{'a' * 64}?relay=ws://127.0.0.1:1&secret={'b' * 64}",
        allow_insecure_relay=True,
    )
    with pytest.raises(WalletProviderUnavailable):
        await rpc(conn, "make_invoice", {"amount": 1000}, timeout=3)
