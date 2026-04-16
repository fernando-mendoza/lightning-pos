from fastapi import APIRouter, Request

from application.confirm_payment import confirm_payment
from infrastructure.db.sale_repo_sqlite import SaleRepoSQLite

router = APIRouter()
sale_repo = SaleRepoSQLite()


@router.post("/lnbits")
async def lnbits_webhook(request: Request):
    body = await request.json()
    payment_hash = body.get("payment_hash", "")
    if not payment_hash:
        return {"status": "ignored"}

    confirmed = await confirm_payment(payment_hash, sale_repo)
    return {"status": "confirmed" if confirmed else "ignored"}
