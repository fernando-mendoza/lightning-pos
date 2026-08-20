"""Cliente NIP-47: una llamada RPC = una conexión al relay del comercio.

Stateless a propósito (misma filosofía que el `httpx.AsyncClient` por request del adaptador
LNbits): el POS hace pocas llamadas y esporádicas; mantener websockets vivos por tenant es
un pool de conexiones que se degrada en silencio. Si el volumen lo pide, se optimiza después.

Flujo de una llamada:
  1. conectar al relay de la cadena de conexión
  2. leer el info event (kind 13194) del wallet → verificar que soporta nip04
  3. suscribirse a la respuesta ANTES de publicar (si no, hay carrera con relays rápidos)
  4. publicar el request (kind 23194, contenido cifrado nip04)
  5. esperar la respuesta (kind 23195 con e-tag del request), descifrar, devolver result
"""

from __future__ import annotations

import asyncio
import json
import secrets as _secrets

import websockets

from domain.ports.wallet_provider import WalletProviderUnavailable

from . import nip44
from .nostr import (
    KIND_INFO,
    KIND_REQUEST,
    KIND_RESPONSE,
    nip04_decrypt,
    nip04_encrypt,
    pubkey_xonly,
    sign_event,
)
from .uri import NWCConnection

# Esquemas que hablamos, en orden de preferencia. nip44_v2 primero: es el moderno y el
# ÚNICO que acepta Lexe; nip04 queda para wallets legadas que no publican el tag.
_SUPPORTED_SCHEMES = ("nip44_v2", "nip04")


class NWCError(Exception):
    """Error devuelto por el wallet service (con código NIP-47)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


async def rpc(conn: NWCConnection, method: str, params: dict, *, timeout: float = 12.0) -> dict:
    """Ejecuta un método NIP-47 y devuelve su `result`.

    Lanza `NWCError` si el wallet respondió con error, `WalletProviderUnavailable` si el
    relay/wallet no respondió a tiempo o el transporte falló.
    """
    try:
        return await asyncio.wait_for(_rpc(conn, method, params), timeout)
    except (NWCError, WalletProviderUnavailable):
        raise
    except asyncio.TimeoutError:
        raise WalletProviderUnavailable(
            f"el wallet no respondió {method} en {timeout:.0f}s ({conn.redacted()})"
        )
    except Exception as e:  # transporte: DNS, TLS, refused, protocolo
        raise WalletProviderUnavailable(
            f"no se pudo hablar con el relay ({type(e).__name__}) ({conn.redacted()})"
        ) from e


async def _recv_json(ws) -> list:
    raw = await ws.recv()
    return json.loads(raw)


async def _rpc(conn: NWCConnection, method: str, params: dict) -> dict:
    client_pub = pubkey_xonly(conn.secret)
    async with websockets.connect(conn.relay_url, open_timeout=8, close_timeout=2) as ws:
        # --- info event: ¿este wallet habla nip04? ---
        info_sub = _secrets.token_hex(8)
        await ws.send(json.dumps(["REQ", info_sub, {"kinds": [KIND_INFO], "authors": [conn.wallet_pubkey], "limit": 1}]))
        encryption_schemes: list[str] | None = None
        while True:
            msg = await _recv_json(ws)
            if msg[0] == "EVENT" and msg[1] == info_sub:
                tags = msg[2].get("tags", [])
                enc_tag = next((t for t in tags if t and t[0] == "encryption"), None)
                if enc_tag and len(enc_tag) > 1:
                    encryption_schemes = enc_tag[1].split()
            elif msg[0] == "EOSE" and msg[1] == info_sub:
                break
            # OK/NOTICE/otros: ignorar
        await ws.send(json.dumps(["CLOSE", info_sub]))
        # Negociación: el mejor esquema común. Sin tag `encryption` (wallets viejas) se asume
        # nip04, que era lo único que existía cuando ese tag no se publicaba.
        if encryption_schemes is None:
            scheme = "nip04"
        else:
            scheme = next((s for s in _SUPPORTED_SCHEMES if s in encryption_schemes), None)
            if scheme is None:
                # Fallar fuerte y con nombre: degradarse en silencio dejaría "Algo salió mal".
                raise WalletProviderUnavailable(
                    f"sin esquema de cifrado común: el wallet acepta {encryption_schemes}, "
                    f"nosotros {list(_SUPPORTED_SCHEMES)}"
                )
        _enc = nip44.encrypt if scheme == "nip44_v2" else nip04_encrypt
        _dec = nip44.decrypt if scheme == "nip44_v2" else nip04_decrypt

        # --- request cifrado ---
        body = json.dumps({"method": method, "params": params})
        event = sign_event(
            conn.secret,
            KIND_REQUEST,
            [["p", conn.wallet_pubkey], ["encryption", scheme]],
            _enc(conn.secret, conn.wallet_pubkey, body),
        )

        # Suscripción a la respuesta ANTES de publicar (carrera con relays rápidos).
        resp_sub = _secrets.token_hex(8)
        await ws.send(
            json.dumps(
                ["REQ", resp_sub, {"kinds": [KIND_RESPONSE], "authors": [conn.wallet_pubkey], "#e": [event["id"]]}]
            )
        )
        await ws.send(json.dumps(["EVENT", event]))

        while True:
            msg = await _recv_json(ws)
            if msg[0] == "OK" and msg[1] == event["id"] and not msg[2]:
                raise WalletProviderUnavailable(f"el relay rechazó el request: {msg[3] if len(msg) > 3 else ''}")
            if msg[0] == "EVENT" and msg[1] == resp_sub:
                reply = msg[2]
                if reply.get("pubkey") != conn.wallet_pubkey:
                    continue  # no es del wallet: ignorar
                payload = json.loads(_dec(conn.secret, conn.wallet_pubkey, reply["content"]))
                err = payload.get("error")
                if err:
                    raise NWCError(err.get("code", "INTERNAL"), err.get("message", ""))
                return payload.get("result") or {}
            # EOSE de resp_sub / NOTICE / OK exitoso: seguir esperando
