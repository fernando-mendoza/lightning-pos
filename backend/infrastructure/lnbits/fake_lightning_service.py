import secrets
import time

from domain.ports.lightning_service import InvoiceResult, LightningService


class FakeLightningService(LightningService):
    """In-memory fake para tests. Genera invoices deterministicas con payment_hash
    aleatorio, sin comunicarse con Phoenixd ni LNbits. Se activa cuando
    LPOS_TEST_MODE=1."""

    async def create_invoice(self, amount_sats: int, memo: str) -> InvoiceResult:
        payment_hash = secrets.token_hex(32)
        bolt11 = f"lntest_fake_{payment_hash}_{amount_sats}"
        expires_at = int(time.time()) + 300
        return InvoiceResult(
            payment_hash=payment_hash, bolt11=bolt11, expires_at=expires_at
        )

    async def check_invoice(self, payment_hash: str) -> bool:
        return False
