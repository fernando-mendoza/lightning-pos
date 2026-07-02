import logging
import secrets
from pathlib import Path

from pydantic import model_validator
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

    # Base URL publica donde LNbits puede alcanzar a ESTE backend para webhooks.
    # En docker-compose dev: http://backend:8000 (red interna).
    # En produccion: el dominio publico del backend (ej: https://pos.dominio.com).
    webhook_base_url: str = "http://localhost:8000"

    # Bitso
    bitso_api_url: str = "https://api.bitso.com/v3"
    exchange_rate_ttl: int = 45  # seconds

    # Auth
    pin_hash: str = ""
    # Secret para firmar JWT. REQUERIDO en produccion.
    # Generar con: openssl rand -hex 32
    jwt_secret: str = ""
    jwt_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 dias
    # Rate limit de verify-pin: max_pin_attempts fallidos en la ventana -> lockout.
    max_pin_attempts: int = 5
    pin_lockout_window_seconds: int = 15 * 60  # 15 minutos

    # CORS: lista de origenes permitidos separados por coma.
    # Dev: http://localhost:8080,http://localhost:8090
    # Produccion: dominios explicitos del frontend.
    allowed_origins: str = "http://localhost:8080,http://localhost:8090"

    # Invoice
    invoice_expiry: int = 300  # seconds

    # Test mode: reemplaza LightningService y ExchangeRateService por fakes
    # deterministicos. NUNCA activar en produccion.
    test_mode: bool = False

    model_config = {"env_file": ".env", "env_prefix": "LPOS_"}

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _generate_jwt_secret_if_empty(self):
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_hex(32)
            logging.getLogger(__name__).warning(
                "LPOS_JWT_SECRET no esta seteado. Se genero un secret efimero para "
                "este boot; todos los tokens se invalidan al reiniciar. Para "
                "produccion, setea LPOS_JWT_SECRET con: openssl rand -hex 32"
            )
        return self

    @model_validator(mode="after")
    def _warn_if_webhook_secret_empty(self):
        if not self.lnbits_webhook_secret and not self.test_mode:
            logging.getLogger(__name__).warning(
                "LPOS_LNBITS_WEBHOOK_SECRET no esta seteado. El endpoint de webhook "
                "acepta requests sin autenticar (la verificacion contra LNbits sigue "
                "activa). Para produccion, setealo con: openssl rand -hex 32"
            )
        return self


settings = Settings()
