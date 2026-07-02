import secrets
import time

from domain.ports.lightning_service import InvoiceResult, LightningService


class FakeLightningService(LightningService):
    """In-memory fake para tests. Genera invoices deterministicas con payment_hash
    aleatorio, sin comunicarse con Phoenixd ni LNbits. Se activa cuando
    LPOS_TEST_MODE=1.

    Es stateful: un invoice emitido NO esta pagado hasta que un test lo marque
    via mark_paid() (expuesto por POST /api/test/payments/{hash}/pay). Asi
    check_invoice() modela a LNbits real: solo responde True si hubo pago."""

    def __init__(self) -> None:
        self._issued: set[str] = set()
        self._paid: set[str] = set()

    async def create_invoice(self, amount_sats: int, memo: str) -> InvoiceResult:
        payment_hash = secrets.token_hex(32)
        self._issued.add(payment_hash)
        bolt11 = f"lntest_fake_{payment_hash}_{amount_sats}"
        expires_at = int(time.time()) + 300
        return InvoiceResult(
            payment_hash=payment_hash, bolt11=bolt11, expires_at=expires_at
        )

    async def check_invoice(self, payment_hash: str) -> bool:
        return payment_hash in self._paid

    def mark_paid(self, payment_hash: str) -> bool:
        if payment_hash not in self._issued:
            return False
        self._paid.add(payment_hash)
        return True
