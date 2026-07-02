"""Rutas SOLO de test mode (LPOS_TEST_MODE=1). main.py las monta unicamente
cuando settings.test_mode esta activo; nunca existen en produccion."""
from fastapi import APIRouter, HTTPException

from infrastructure.providers import lightning_service

router = APIRouter()


@router.post("/payments/{payment_hash}/pay")
async def mark_invoice_paid(payment_hash: str):
    """Simula que el cliente pago el invoice en el fake de LNbits."""
    ok = lightning_service.mark_paid(payment_hash)
    if not ok:
        raise HTTPException(status_code=404, detail="Invoice not issued")
    return {"payment_hash": payment_hash, "paid": True}
