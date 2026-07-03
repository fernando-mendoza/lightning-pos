"""Rutas SOLO de test mode (LPOS_TEST_MODE=1). main.py las monta unicamente
cuando settings.test_mode esta activo; nunca existen en produccion."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from infrastructure.db.connection import get_db
from infrastructure.providers import lightning_service

router = APIRouter()


@router.post("/payments/{payment_hash}/pay")
async def mark_invoice_paid(payment_hash: str):
    """Simula que el cliente pago el invoice en el fake de LNbits."""
    ok = lightning_service.mark_paid(payment_hash)
    if not ok:
        raise HTTPException(status_code=404, detail="Invoice not issued")
    return {"payment_hash": payment_hash, "paid": True}


class BackdateRequest(BaseModel):
    seconds: int = Field(gt=0)


@router.post("/sales/{payment_hash}/backdate")
async def backdate_sale(payment_hash: str, body: BackdateRequest):
    """Mueve created_at al pasado para probar expiracion sin esperar."""
    new_created = (
        datetime.now(timezone.utc) - timedelta(seconds=body.seconds)
    ).isoformat()
    db = await get_db()
    cursor = await db.execute(
        "UPDATE sales SET created_at = ? WHERE payment_hash = ?",
        (new_created, payment_hash),
    )
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Sale not found")
    return {"payment_hash": payment_hash, "created_at": new_created}
