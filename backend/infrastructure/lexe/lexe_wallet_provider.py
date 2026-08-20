"""WalletProvider sobre el sidecar de Lexe (self-custodial, nodo en enclave).

Por qué existe si ya tenemos NWC: **Lexe todavía no expone NWC en su app** — está en el
nodo (`node/src/nwc.rs`) pero la UI no lo publica (su propio código: *"TODO: add NWC clients
when NWC is supported"*). Hasta que lo haga, el camino a Lexe es su sidecar REST.

La "invoice key" de este provider es la **credencial SDK** del comercio, con scope
`receive` (+`read_payments`), verificado contra el nodo real: `pay_invoice` responde
*"Client lacks the required permission"*. O sea: podemos cobrar y ver si pagaron, y **no
podemos gastar** aunque nos comprometan.

⚠️ **Limitación estructural, no un detalle:** el sidecar toma la credencial como
**configuración de proceso** (`LEXE_CLIENT_CREDENTIALS`), no por request. Un sidecar = una
wallet ⇒ multi-tenant exige un sidecar por comercio. Por eso NWC sigue siendo la
arquitectura y Lexe la rampa: cuando Lexe publique NWC, estos tenants migran al provider
NWC sin cambiar la lógica de negocio.
"""

from __future__ import annotations

import httpx

from domain.ports.wallet_provider import (
    ProvisionedWallet,
    WalletInvoice,
    WalletProvider,
    WalletProviderUnavailable,
)

# Prefijo de credencial en `invoice_key_enc` que enruta a este provider. La credencial
# real de Lexe es un blob opaco, así que el prefijo lo ponemos nosotros al conectar.
CREDENTIAL_PREFIX = "lexe-sidecar:"


def _unavailable(exc: Exception) -> WalletProviderUnavailable:
    if isinstance(exc, httpx.HTTPStatusError):
        detail = ""
        try:
            detail = str(exc.response.json().get("msg", ""))[:160]
        except Exception:  # noqa: BLE001
            detail = exc.response.text[:160]
        return WalletProviderUnavailable(f"lexe respondió {exc.response.status_code}: {detail}")
    return WalletProviderUnavailable(f"sidecar de lexe inalcanzable ({type(exc).__name__})")


class LexeWalletProvider(WalletProvider):
    def __init__(self, sidecar_url: str, invoice_expiry: int = 300) -> None:
        self._base = sidecar_url.rstrip("/")
        self._expiry = invoice_expiry

    async def provision_wallet(self, name: str) -> ProvisionedWallet:
        # La wallet la crea el comercio en la app de Lexe y nos pasa la credencial. Igual
        # que NWC: no provisionamos, y por eso no puede haber altas a medias.
        raise RuntimeError("Lexe no provisiona wallets: el comercio crea la suya en la app")

    async def create_invoice(
        self, invoice_key: str, amount_sats: int, memo: str, webhook_url: str | None = None
    ) -> WalletInvoice:
        # webhook_url se ignora: el sidecar entrega webhooks por configuración de proceso,
        # no por invoice. La confirmación va por el polling ya existente de GET /invoices/{id}.
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.post(
                    f"{self._base}/v1/node/create_invoice",
                    json={
                        "amount": amount_sats,
                        "description": memo,
                        "expiration_secs": self._expiry,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise _unavailable(e) from e
        if not data.get("invoice") or not data.get("payment_hash"):
            raise WalletProviderUnavailable("lexe devolvió una invoice incompleta")
        return WalletInvoice(
            payment_hash=data["payment_hash"],
            bolt11=data["invoice"],
            # Lexe da milisegundos; nuestro contrato es segundos unix.
            expires_at=int(data.get("expires_at", 0)) // 1000,
            # SU índice es la única llave con la que se puede consultar el pago después.
            provider_ref=data.get("index"),
        )

    async def check_invoice(
        self, invoice_key: str, payment_hash: str, provider_ref: str | None = None
    ) -> bool:
        """Consulta por el `index` de Lexe, que es lo ÚNICO que acepta su API.

        Sondeado contra el sidecar real: `payment?hash=` y `payment?payment_hash=` responden
        *"missing field index"*, y no existe endpoint de listado (`payments`,
        `list_payments`, `get_payment` → 400 "non-existent endpoint"). Por eso el index se
        persiste en `Invoice.provider_ref` al emitir.
        """
        if not provider_ref:
            # Sin referencia no hay forma de preguntar. Devolver False confirmaría "no
            # pagada" sobre una invoice que quizá SÍ se pagó — el error que más daño hace.
            raise WalletProviderUnavailable(
                "invoice de Lexe sin provider_ref: no se puede consultar su estado"
            )
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.get(
                    f"{self._base}/v1/node/payment", params={"index": provider_ref}
                )
                resp.raise_for_status()
                payment = resp.json().get("payment") or {}
        except httpx.HTTPError as e:
            raise _unavailable(e) from e
        return payment.get("status") == "completed"
