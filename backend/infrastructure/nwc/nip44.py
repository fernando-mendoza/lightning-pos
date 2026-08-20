"""NIP-44 v2: el cifrado moderno de Nostr (ChaCha20 + HMAC-SHA256, con padding).

Implementado porque Lexe — nuestro proveedor-rampa — sólo habla NIP-44 en su NWC
(verificado en `node/src/nwc.rs`: `decrypt_nip44_request`, sin rastro de nip04).
Verificado contra los vectores oficiales de paulmillr/nip44 en el test.

Diferencias clave con NIP-04 que justifican el esquema:
- la llave de conversación pasa por HKDF (nip04 usa la x de ECDH cruda como llave AES);
- hay MAC: un ciphertext manipulado se rechaza, no se descifra a basura;
- el padding oculta la longitud del mensaje.
"""

from __future__ import annotations

import base64
import hmac as hmac_mod
import os
from hashlib import sha256

from coincurve import PublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

_VERSION = 2


def conversation_key(secret_hex: str, peer_xonly_hex: str) -> bytes:
    """hkdf_extract(salt="nip44-v2", ikm=x-coord del ECDH)."""
    shared_x = (
        PublicKey(bytes.fromhex("02" + peer_xonly_hex))
        .multiply(bytes.fromhex(secret_hex))
        .format(compressed=True)[1:]
    )
    return hmac_mod.new(b"nip44-v2", shared_x, sha256).digest()


def _message_keys(conv_key: bytes, nonce: bytes) -> tuple[bytes, bytes, bytes]:
    okm = HKDFExpand(algorithm=SHA256(), length=76, info=nonce).derive(conv_key)
    return okm[0:32], okm[32:44], okm[44:76]  # chacha_key, chacha_nonce, hmac_key


def _calc_padded_len(unpadded: int) -> int:
    if unpadded <= 32:
        return 32
    next_power = 1 << ((unpadded - 1).bit_length())
    chunk = 32 if next_power <= 256 else next_power // 8
    return chunk * ((unpadded - 1) // chunk + 1)


def _pad(plaintext: bytes) -> bytes:
    n = len(plaintext)
    if not 1 <= n <= 65535:
        raise ValueError(f"longitud de mensaje inválida para nip44: {n}")
    return n.to_bytes(2, "big") + plaintext + b"\x00" * (_calc_padded_len(n) - n)


def _unpad(padded: bytes) -> bytes:
    n = int.from_bytes(padded[:2], "big")
    if n == 0 or len(padded) != 2 + _calc_padded_len(n):
        raise ValueError("padding nip44 inválido")
    return padded[2 : 2 + n]


def _chacha20(key: bytes, nonce12: bytes, data: bytes) -> bytes:
    # ChaCha20 de `cryptography` pide nonce de 16: 4 bytes de contador (0) + los 12 del spec.
    cipher = Cipher(algorithms.ChaCha20(key, b"\x00" * 4 + nonce12), mode=None)
    enc = cipher.encryptor()
    return enc.update(data) + enc.finalize()


def encrypt(secret_hex: str, peer_xonly_hex: str, plaintext: str, *, _nonce: bytes | None = None) -> str:
    """`_nonce` existe SOLO para los vectores de prueba; en producción es aleatorio."""
    conv = conversation_key(secret_hex, peer_xonly_hex)
    nonce = _nonce if _nonce is not None else os.urandom(32)
    ck, cn, hk = _message_keys(conv, nonce)
    ct = _chacha20(ck, cn, _pad(plaintext.encode()))
    mac = hmac_mod.new(hk, nonce + ct, sha256).digest()
    return base64.b64encode(bytes([_VERSION]) + nonce + ct + mac).decode()


def decrypt(secret_hex: str, peer_xonly_hex: str, payload: str) -> str:
    return decrypt_with_conv_key(conversation_key(secret_hex, peer_xonly_hex), payload)


def decrypt_with_conv_key(conv: bytes, payload: str) -> str:
    """Separado para poder verificar los vectores oficiales inválidos, que traen la
    conversation_key directa en vez de las llaves."""
    if payload.startswith("#"):
        raise ValueError("versión nip44 no soportada (payload con prefijo #)")
    raw = base64.b64decode(payload, validate=True)
    if len(raw) < 1 + 32 + 32 + 32 or raw[0] != _VERSION:
        raise ValueError("payload nip44 inválido o versión desconocida")
    nonce, ct, mac = raw[1:33], raw[33:-32], raw[-32:]
    ck, cn, hk = _message_keys(conv, nonce)
    expected = hmac_mod.new(hk, nonce + ct, sha256).digest()
    if not hmac_mod.compare_digest(expected, mac):
        raise ValueError("MAC nip44 inválido: payload manipulado o llaves equivocadas")
    return _unpad(_chacha20(ck, cn, ct)).decode()
