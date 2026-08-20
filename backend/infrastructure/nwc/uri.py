"""Parseo y validación de cadenas de conexión NWC (NIP-47).

Formato: nostr+walletconnect://<wallet-pubkey-hex>?relay=wss://…&secret=<hex>[&lud16=…]

La cadena ES la credencial: el `secret` es la llave privada de ESTA conexión (no la de la
wallet del comercio), y el comercio la revoca desde su wallet cuando quiera. Por eso se
guarda cifrada at-rest igual que una invoice key, y por eso NUNCA se loguea completa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCHEME = "nostr+walletconnect"


class NWCUriError(ValueError):
    """Cadena de conexión inválida. El mensaje es apto para mostrarse al usuario."""


@dataclass(frozen=True)
class NWCConnection:
    wallet_pubkey: str  # x-only, 64 hex
    relay_url: str
    secret: str  # llave privada de la conexión, 64 hex

    def redacted(self) -> str:
        """Para logs: identifica la conexión sin filtrar el secreto."""
        return f"nwc:{self.wallet_pubkey[:8]}…@{self.relay_url}"


def parse_nwc_uri(uri: str, *, allow_insecure_relay: bool = False) -> NWCConnection:
    uri = uri.strip()
    parsed = urlparse(uri)
    if parsed.scheme != SCHEME:
        raise NWCUriError("la cadena no empieza con nostr+walletconnect://")
    # urlparse puede dejar el pubkey en netloc o en path según cómo venga pegada.
    pubkey = (parsed.netloc or parsed.path.lstrip("/")).lower()
    if not _HEX64.match(pubkey):
        raise NWCUriError("pubkey de wallet inválida (se esperan 64 caracteres hex)")
    q = parse_qs(parsed.query)
    relays = q.get("relay", [])
    secrets_ = q.get("secret", [])
    if not relays or not relays[0]:
        raise NWCUriError("falta el parámetro relay")
    if not secrets_ or not _HEX64.match(secrets_[0].lower()):
        raise NWCUriError("falta el parámetro secret o no son 64 caracteres hex")
    relay = relays[0]
    if not relay.startswith("wss://"):
        if not (allow_insecure_relay and relay.startswith("ws://")):
            raise NWCUriError("el relay debe ser wss:// (cifrado)")
    return NWCConnection(wallet_pubkey=pubkey, relay_url=relay, secret=secrets_[0].lower())
