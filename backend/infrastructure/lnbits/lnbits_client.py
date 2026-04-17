import httpx

from config import settings
from domain.ports.lightning_service import LightningService, InvoiceResult


class LNbitsClient(LightningService):
    async def create_invoice(self, amount_sats: int, memo: str) -> InvoiceResult:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.lnbits_url}/api/v1/payments",
                headers={"X-Api-Key": settings.lnbits_api_key},
                json={
                    "out": False,
                    "amount": amount_sats,
                    "memo": memo,
                    "expiry": settings.invoice_expiry,
                    "webhook": f"{settings.webhook_base_url}/api/webhooks/lnbits",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return InvoiceResult(
            payment_hash=data["payment_hash"],
            bolt11=data["bolt11"],
            expires_at=data.get("expires_at", 0),
        )

    async def check_invoice(self, payment_hash: str) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.lnbits_url}/api/v1/payments/{payment_hash}",
                headers={"X-Api-Key": settings.lnbits_api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("paid", False)
