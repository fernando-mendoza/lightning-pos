from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Lightning POS"
    debug: bool = False

    # Database
    db_path: str = str(Path(__file__).parent / "data" / "lightning-pos.db")

    # LNbits
    lnbits_url: str = "http://localhost:5000"
    lnbits_api_key: str = ""
    lnbits_webhook_secret: str = ""

    # Bitso
    bitso_api_url: str = "https://api.bitso.com/v3"
    exchange_rate_ttl: int = 45  # seconds

    # Auth
    pin_hash: str = ""

    # Invoice
    invoice_expiry: int = 300  # seconds

    model_config = {"env_file": ".env", "env_prefix": "LPOS_"}


settings = Settings()
