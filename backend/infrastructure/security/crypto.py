"""Cifrado at-rest de secretos por tenant (llaves LNbits) con AES-GCM.

Formato: `enc:v1:<base64(nonce(12) || ciphertext)>`. La clave se deriva por sha256 del
`LPOS_DATA_ENCRYPTION_KEY`. En dev, si no está seteada, se usa una clave insegura fija
(con warning) para que el entorno funcione; en producción DEBE setearse.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import settings

_PREFIX = "enc:v1:"
_DEV_KEY = "lpos-dev-insecure-encryption-key-do-not-use-in-prod"

_logger = logging.getLogger(__name__)


def _key() -> bytes:
    raw = settings.data_encryption_key
    if not raw:
        _logger.warning(
            "LPOS_DATA_ENCRYPTION_KEY no seteada: usando clave de dev insegura. "
            "Setéala en producción (openssl rand -hex 32)."
        )
        raw = _DEV_KEY
    return hashlib.sha256(raw.encode()).digest()  # 32 bytes


def encrypt(plaintext: str) -> str:
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode(), None)
    return _PREFIX + base64.b64encode(nonce + ct).decode()


def decrypt(token: str) -> str:
    if not token.startswith(_PREFIX):
        raise ValueError("ciphertext inválido (prefijo faltante)")
    raw = base64.b64decode(token[len(_PREFIX):])
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(_key())
    return aes.decrypt(nonce, ct, None).decode()
