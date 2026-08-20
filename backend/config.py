import logging
import secrets
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Lightning POS"
    debug: bool = False

    # Database (legacy SQLite; se mantiene durante la transición a Postgres)
    db_path: str = str(Path(__file__).parent / "data" / "lightning-pos.db")

    # Postgres (Fase 0 multi-tenant). Dev: docker Postgres en el puerto 5433.
    # Prod: DATABASE_URL de Railway (formato postgresql+asyncpg://...).
    database_url: str = "postgresql+asyncpg://lpos:dev@localhost:5433/lightning_pos"

    # URL pública del backend que la app usa (va en el QR de pairing).
    public_base_url: str = "http://localhost:8000"
    # Vida del código de pairing (segundos).
    pairing_code_ttl_seconds: int = 90

    # Rate limits de endpoints públicos ("N/segundos"), por IP, en memoria.
    rate_limit_login: str = "20/60"
    rate_limit_register: str = "10/300"
    rate_limit_redeem: str = "30/60"

    # ¿El alta pública de tenants (POST /api/v2/auth/register) está abierta?
    #
    # DEFAULT False A PROPÓSITO — "fail closed". Cada alta provisiona una wallet LNbits
    # en NUESTRA instancia (ver infrastructure/lnbits/lnbits_wallet_provider.py: "custodial,
    # un wallet por tenant"), o sea que un registro abierto significa custodiar fondos de
    # terceros. Eso contradice lo que prometen las fichas de App Store y Google Play
    # ("no-custodial") y tiene implicaciones regulatorias en MX (Ley Fintech / LFPIORPI).
    #
    # Sólo se abre cuando exista el modelo BYO wallet (NWC), donde el comercio conecta su
    # propia wallet y nosotros no tocamos fondos. Contexto y roadmap:
    # hub → workspaces/runs/2026-08-02-lightning-pos-saas-strategy/
    registration_enabled: bool = False
    # Interruptor del rail Lightning. En falso, /terminal/me deja de ofrecerlo y el endpoint
    # de invoice responde 503 en vez de intentar contra un proveedor que no existe.
    lightning_enabled: bool = True
    # Sidecar de Lexe (rampa self-custodial). Vacío = no hay rail Lexe configurado.
    # OJO: el sidecar toma la credencial por PROCESO, así que hoy sirve a UNA wallet.
    lexe_sidecar_url: str = ""

    # Clave para encriptar at-rest las llaves LNbits por tenant (AES-GCM, enc:v1:).
    # REQUERIDA en producción. Generar: openssl rand -hex 32
    data_encryption_key: str = ""

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
