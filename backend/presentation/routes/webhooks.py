import secrets

from fastapi import APIRouter, HTTPException, Request

from application.confirm_payment import confirm_payment
from config import settings
from infrastructure.db.sale_repo_sqlite import SaleRepoSQLite
from infrastructure.providers import lightning_service

router = APIRouter()
sale_repo = SaleRepoSQLite()


@router.post("/lnbits")
async def lnbits_webhook(request: Request, secret: str = ""):
    # Capa 1: el webhook que registramos en LNbits incluye ?secret=...; el
    # payment_hash solo NO autentica (el cliente lo conoce via el bolt11 del QR).
    if settings.lnbits_webhook_secret and not secrets.compare_digest(
        secret, settings.lnbits_webhook_secret
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    body = await request.json()
    payment_hash = body.get("payment_hash", "")
    if not payment_hash:
        return {"status": "ignored"}

    # Capa 2: nunca confiar en el body — confirmar contra LNbits que el
    # invoice realmente esta pagado. Si LNbits no responde, el poll de
    # /invoices/{hash}/status reconcilia despues.
    try:
        paid = await lightning_service.check_invoice(payment_hash)
    except Exception:
        paid = False
    if not paid:
        return {"status": "ignored"}

    confirmed = await confirm_payment(payment_hash, sale_repo)
    return {"status": "confirmed" if confirmed else "ignored"}
