"""Vectores oficiales NIP-44 v2 (paulmillr/nip44) + propiedades de rechazo.

Los vectores van embebidos como JSON crudo y se parsean con json.loads: un literal de
Python NO re-une pares sustitutos (\ud83e\udec3 quedan como dos surrogates que .encode()
rechaza), pero el parser de JSON sí — ese bug rompió la primera versión de este archivo.
La suite corre offline en el contenedor; no se baja nada en el test.
"""

import base64
import json
import secrets

import pytest

from infrastructure.nwc import nip44
from infrastructure.nwc.nostr import pubkey_xonly

VECTORS = json.loads(r'''
{
 "get_conversation_key": [
  {
   "sec1": "315e59ff51cb9209768cf7da80791ddcaae56ac9775eb25b6dee1234bc5d2268",
   "pub2": "c2f9d9948dc8c7c38321e4b85c8558872eafa0641cd269db76848a6073e69133",
   "conversation_key": "3dfef0ce2a4d80a25e7a328accf73448ef67096f65f79588e358d9a0eb9013f1"
  },
  {
   "sec1": "a1e37752c9fdc1273be53f68c5f74be7c8905728e8de75800b94262f9497c86e",
   "pub2": "03bb7947065dde12ba991ea045132581d0954f042c84e06d8c00066e23c1a800",
   "conversation_key": "4d14f36e81b8452128da64fe6f1eae873baae2f444b02c950b90e43553f2178b"
  },
  {
   "sec1": "98a5902fd67518a0c900f0fb62158f278f94a21d6f9d33d30cd3091195500311",
   "pub2": "aae65c15f98e5e677b5050de82e3aba47a6fe49b3dab7863cf35d9478ba9f7d1",
   "conversation_key": "9c00b769d5f54d02bf175b7284a1cbd28b6911b06cda6666b2243561ac96bad7"
  }
 ],
 "encrypt_decrypt": [
  {
   "sec1": "0000000000000000000000000000000000000000000000000000000000000001",
   "sec2": "0000000000000000000000000000000000000000000000000000000000000002",
   "conversation_key": "c41c775356fd92eadc63ff5a0dc1da211b268cbea22316767095b2871ea1412d",
   "nonce": "0000000000000000000000000000000000000000000000000000000000000001",
   "plaintext": "a",
   "payload": "AgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABee0G5VSK0/9YypIObAtDKfYEAjD35uVkHyB0F4DwrcNaCXlCWZKaArsGrY6M9wnuTMxWfp1RTN9Xga8no+kF5Vsb"
  },
  {
   "sec1": "0000000000000000000000000000000000000000000000000000000000000002",
   "sec2": "0000000000000000000000000000000000000000000000000000000000000001",
   "conversation_key": "c41c775356fd92eadc63ff5a0dc1da211b268cbea22316767095b2871ea1412d",
   "nonce": "f00000000000000000000000000000f00000000000000000000000000000000f",
   "plaintext": "\ud83c\udf55\ud83e\udec3",
   "payload": "AvAAAAAAAAAAAAAAAAAAAPAAAAAAAAAAAAAAAAAAAAAPSKSK6is9ngkX2+cSq85Th16oRTISAOfhStnixqZziKMDvB0QQzgFZdjLTPicCJaV8nDITO+QfaQ61+KbWQIOO2Yj"
  },
  {
   "sec1": "5c0c523f52a5b6fad39ed2403092df8cebc36318b39383bca6c00808626fab3a",
   "sec2": "4b22aa260e4acb7021e32f38a6cdf4b673c6a277755bfce287e370c924dc936d",
   "conversation_key": "3e2b52a63be47d34fe0a80e34e73d436d6963bc8f39827f327057a9986c20a45",
   "nonce": "b635236c42db20f021bb8d1cdff5ca75dd1a0cc72ea742ad750f33010b24f73b",
   "plaintext": "\u8868\u30dd\u3042A\u9dd7\u0152\u00e9\uff22\u900d\u00dc\u00df\u00aa\u0105\u00f1\u4e02\u3400\ud840\udc00",
   "payload": "ArY1I2xC2yDwIbuNHN/1ynXdGgzHLqdCrXUPMwELJPc7s7JqlCMJBAIIjfkpHReBPXeoMCyuClwgbT419jUWU1PwaNl4FEQYKCDKVJz+97Mp3K+Q2YGa77B6gpxB/lr1QgoqpDf7wDVrDmOqGoiPjWDqy8KzLueKDcm9BVP8xeTJIxs="
  },
  {
   "sec1": "8f40e50a84a7462e2b8d24c28898ef1f23359fff50d8c509e6fb7ce06e142f9c",
   "sec2": "b9b0a1e9cc20100c5faa3bbe2777303d25950616c4c6a3fa2e3e046f936ec2ba",
   "conversation_key": "d5a2f879123145a4b291d767428870f5a8d9e5007193321795b40183d4ab8c2b",
   "nonce": "b20989adc3ddc41cd2c435952c0d59a91315d8c5218d5040573fc3749543acaf",
   "plaintext": "ability\ud83e\udd1d\u7684 \u023a\u023e",
   "payload": "ArIJia3D3cQc0sQ1lSwNWakTFdjFIY1QQFc/w3SVQ6yvbG2S0x4Yu86QGwPTy7mP3961I1XqB6SFFTzqDZZavhxoWMj7mEVGMQIsh2RLWI5EYQaQDIePSnXPlzf7CIt+voTD"
  }
 ],
 "calc_padded_len": [
  [
   16,
   32
  ],
  [
   32,
   32
  ],
  [
   33,
   64
  ],
  [
   37,
   64
  ],
  [
   45,
   64
  ],
  [
   49,
   64
  ],
  [
   64,
   64
  ],
  [
   65,
   96
  ],
  [
   100,
   128
  ],
  [
   111,
   128
  ],
  [
   200,
   224
  ],
  [
   250,
   256
  ],
  [
   320,
   320
  ],
  [
   383,
   384
  ],
  [
   384,
   384
  ],
  [
   400,
   448
  ],
  [
   500,
   512
  ],
  [
   512,
   512
  ],
  [
   515,
   640
  ],
  [
   700,
   768
  ],
  [
   800,
   896
  ],
  [
   900,
   1024
  ],
  [
   1020,
   1024
  ],
  [
   65536,
   65536
  ]
 ],
 "invalid_decrypt": [
  {
   "conversation_key": "ca2527a037347b91bea0c8a30fc8d9600ffd81ec00038671e3a0f0cb0fc9f642",
   "nonce": "daaea5ca345b268e5b62060ca72c870c48f713bc1e00ff3fc0ddb78e826f10db",
   "plaintext": "n o b l e",
   "payload": "#Atqupco0WyaOW2IGDKcshwxI9xO8HgD/P8Ddt46CbxDbrhdG8VmJdU0MIDf06CUvEvdnr1cp1fiMtlM/GrE92xAc1K5odTpCzUB+mjXgbaqtntBUbTToSUoT0ovrlPwzGjyp",
   "note": "unknown encryption version"
  },
  {
   "conversation_key": "36f04e558af246352dcf73b692fbd3646a2207bd8abd4b1cd26b234db84d9481",
   "nonce": "ad408d4be8616dc84bb0bf046454a2a102edac937c35209c43cd7964c5feb781",
   "plaintext": "\u26a0\ufe0f",
   "payload": "AK1AjUvoYW3IS7C/BGRUoqEC7ayTfDUgnEPNeWTF/reBZFaha6EAIRueE9D1B1RuoiuFScC0Q94yjIuxZD3JStQtE8JMNacWFs9rlYP+ZydtHhRucp+lxfdvFlaGV/sQlqZz",
   "note": "unknown encryption version 0"
  },
  {
   "conversation_key": "ca2527a037347b91bea0c8a30fc8d9600ffd81ec00038671e3a0f0cb0fc9f642",
   "nonce": "daaea5ca345b268e5b62060ca72c870c48f713bc1e00ff3fc0ddb78e826f10db",
   "plaintext": "n o s t r",
   "payload": "At\u0444upco0WyaOW2IGDKcshwxI9xO8HgD/P8Ddt46CbxDbrhdG8VmJZE0UICD06CUvEvdnr1cp1fiMtlM/GrE92xAc1EwsVCQEgWEu2gsHUVf4JAa3TpgkmFc3TWsax0v6n/Wq",
   "note": "invalid base64"
  },
  {
   "conversation_key": "cff7bd6a3e29a450fd27f6c125d5edeb0987c475fd1e8d97591e0d4d8a89763c",
   "nonce": "09ff97750b084012e15ecb84614ce88180d7b8ec0d468508a86b6d70c0361a25",
   "plaintext": "\u00af\\_(\u30c4)_/\u00af",
   "payload": "Agn/l3ULCEAS4V7LhGFM6IGA17jsDUaFCKhrbXDANholyySBfeh+EN8wNB9gaLlg4j6wdBYh+3oK+mnxWu3NKRbSvQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
   "note": "invalid MAC"
  }
 ]
}
''')


def test_conversation_key_vectors():
    for v in VECTORS["get_conversation_key"]:
        assert nip44.conversation_key(v["sec1"], v["pub2"]).hex() == v["conversation_key"]


def test_encrypt_decrypt_vectors_byte_exact():
    for v in VECTORS["encrypt_decrypt"]:
        payload = nip44.encrypt(
            v["sec1"], pubkey_xonly(v["sec2"]), v["plaintext"], _nonce=bytes.fromhex(v["nonce"])
        )
        assert payload == v["payload"], "cifrado no coincide byte a byte con el vector"
        assert nip44.decrypt(v["sec2"], pubkey_xonly(v["sec1"]), v["payload"]) == v["plaintext"]


def test_calc_padded_len_vectors():
    for unpadded, padded in VECTORS["calc_padded_len"]:
        assert nip44._calc_padded_len(unpadded) == padded, (unpadded, padded)


def test_official_invalid_decrypt_vectors():
    """Los vectores inválidos traen la conversation_key directa; todos deben rechazarse."""
    for v in VECTORS["invalid_decrypt"]:
        with pytest.raises(ValueError):
            nip44.decrypt_with_conv_key(bytes.fromhex(v["conversation_key"]), v["payload"])


def test_tampered_payload_is_rejected():
    a, b = secrets.token_hex(32), secrets.token_hex(32)
    payload = nip44.encrypt(a, pubkey_xonly(b), "hola nip44")
    raw = bytearray(base64.b64decode(payload))
    raw[40] ^= 0x01  # un bit del ciphertext
    with pytest.raises(ValueError, match="MAC"):
        nip44.decrypt(b, pubkey_xonly(a), base64.b64encode(bytes(raw)).decode())


def test_roundtrip_unicode_and_sizes():
    a, b = secrets.token_hex(32), secrets.token_hex(32)
    pa, pb = pubkey_xonly(a), pubkey_xonly(b)
    for msg in ["x", "ñandú 🍕 · 表ポあ", "a" * 33, "b" * 65535]:
        assert nip44.decrypt(b, pa, nip44.encrypt(a, pb, msg)) == msg
