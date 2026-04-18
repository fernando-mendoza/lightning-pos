from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from application.auth import (
    verify_pin,
    set_pin,
    is_pin_set,
    check_pin_rate_limit,
    record_pin_attempt,
)

router = APIRouter()


class PinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=6)


class SetupPinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=6)


@router.get("/status")
async def auth_status():
    has_pin = await is_pin_set()
    return {"pin_set": has_pin}


@router.post("/verify-pin")
async def post_verify_pin(body: PinRequest):
    allowed, retry_after = await check_pin_rate_limit()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos. Espera {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
    token = await verify_pin(body.pin)
    await record_pin_attempt(success=bool(token))
    if not token:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {"token": token}


@router.post("/setup-pin", status_code=201)
async def post_setup_pin(body: SetupPinRequest):
    has_pin = await is_pin_set()
    if has_pin:
        raise HTTPException(status_code=409, detail="PIN already set. Use change-pin instead.")
    await set_pin(body.pin)
    return {"status": "ok"}


class ChangePinRequest(BaseModel):
    current_pin: str = Field(min_length=4, max_length=6)
    new_pin: str = Field(min_length=4, max_length=6)


@router.post("/change-pin")
async def post_change_pin(body: ChangePinRequest):
    allowed, retry_after = await check_pin_rate_limit()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos. Espera {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
    token = await verify_pin(body.current_pin)
    await record_pin_attempt(success=bool(token))
    if not token:
        raise HTTPException(status_code=401, detail="Current PIN is incorrect")
    await set_pin(body.new_pin)
    return {"status": "ok"}
