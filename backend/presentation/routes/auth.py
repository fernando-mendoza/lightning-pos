from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from application.auth import verify_pin, set_pin, is_pin_set

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
    token = await verify_pin(body.pin)
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
    token = await verify_pin(body.current_pin)
    if not token:
        raise HTTPException(status_code=401, detail="Current PIN is incorrect")
    await set_pin(body.new_pin)
    return {"status": "ok"}
