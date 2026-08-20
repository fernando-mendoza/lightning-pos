"""Primitivas Nostr mínimas para NIP-47: eventos, firma BIP-340 y cifrado NIP-04.

Implementado en casa a propósito: no existe librería NWC madura en Python (el SDK de
referencia es JS/TS), y un sidecar Node sería un proceso más que puede caerse en silencio —
exactamente el modo de falla del sidecar de Spark que mató el rail anterior.

NIP-04 y no NIP-44 (por ahora): NIP-04 es el esquema legado que todo wallet service NWC
acepta; NIP-44 es el moderno. El cliente lee el info event del wallet y FALLA FUERTE si el
wallet exige sólo nip44, en vez de degradarse en silencio. Cuando NIP-44 se implemente, se
negocia hacia arriba.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time

from coincurve import PrivateKey, PublicKey
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KIND_INFO = 13194
KIND_REQUEST = 23194
KIND_RESPONSE = 23195
KIND_NOTIFICATION = 23196


def pubkey_xonly(secret_hex: str) -> str:
    """Pubkey x-only (64 hex) de una llave privada."""
    return PrivateKey(bytes.fromhex(secret_hex)).public_key.format(compressed=True)[1:].hex()


def event_id(pubkey: str, created_at: int, kind: int, tags: list, content: str) -> str:
    """Id canónico NIP-01: sha256 del array serializado sin espacios."""
    payload = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def sign_event(secret_hex: str, kind: int, tags: list, content: str, created_at: int | None = None) -> dict:
    created = created_at if created_at is not None else int(time.time())
    pk = pubkey_xonly(secret_hex)
    eid = event_id(pk, created, kind, tags, content)
    sig = PrivateKey(bytes.fromhex(secret_hex)).sign_schnorr(bytes.fromhex(eid))
    return {
        "id": eid,
        "pubkey": pk,
        "created_at": created,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": sig.hex(),
    }


def _shared_key(secret_hex: str, peer_xonly_hex: str) -> bytes:
    """ECDH de NIP-04: coordenada x del punto compartido, SIN hashear (así lo define nostr)."""
    peer = PublicKey(bytes.fromhex("02" + peer_xonly_hex))
    return peer.multiply(bytes.fromhex(secret_hex)).format(compressed=True)[1:]


def nip04_encrypt(secret_hex: str, peer_xonly_hex: str, plaintext: str) -> str:
    key = _shared_key(secret_hex, peer_xonly_hex)
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    data = padder.update(plaintext.encode()) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ct = enc.update(data) + enc.finalize()
    return f"{base64.b64encode(ct).decode()}?iv={base64.b64encode(iv).decode()}"


def nip04_decrypt(secret_hex: str, peer_xonly_hex: str, payload: str) -> str:
    key = _shared_key(secret_hex, peer_xonly_hex)
    ct_b64, _, iv_b64 = payload.partition("?iv=")
    if not iv_b64:
        raise ValueError("payload nip04 sin iv")
    dec = Cipher(algorithms.AES(key), modes.CBC(base64.b64decode(iv_b64))).decryptor()
    padded = dec.update(base64.b64decode(ct_b64)) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode()
