"""ORM models — Fase 0 multi-tenant (Postgres).

Reglas del proyecto: montos MXN = Numeric(12,2); sats = BigInteger. Toda tabla de negocio
lleva `tenant_id` para aislamiento (forzado en la capa de repos; el cliente nunca lo envía).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


# ---------- enums ----------
class Role(str, enum.Enum):
    owner = "owner"
    manager = "manager"
    cashier = "cashier"


class TerminalRole(str, enum.Enum):
    manager = "manager"
    cashier = "cashier"


class TerminalStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"


class OrderStatus(str, enum.Enum):
    open = "open"
    invoiced = "invoiced"
    paid = "paid"
    expired = "expired"
    cancelled = "cancelled"


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    expired = "expired"
    cancelled = "cancelled"


class PaymentMethod(str, enum.Enum):
    """Cómo se cobró la orden. La invoice es el artefacto de UN método, no la venta."""

    lightning = "lightning"
    cash = "cash"


class WalletProviderKind(str, enum.Enum):
    lnbits = "lnbits"
    # BYO wallet vía NIP-47: la credencial es la cadena de conexión (en invoice_key_enc),
    # no custodiamos fondos y no hay provisión. native_enum=False ⇒ sin migración de DB.
    nwc = "nwc"
    # Nodo self-custodial en enclave, vía su sidecar REST. Rampa para el comercio sin
    # wallet, hasta que Lexe exponga NWC en su app y estos tenants migren a `nwc`.
    lexe = "lexe"


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ---------- tenancy / auth ----------
class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MXN")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = _created_at()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = _created_at()


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_membership"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, native_enum=False, length=20), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()


# ---------- terminals / pairing ----------
class Terminal(Base):
    __tablename__ = "terminals"

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[TerminalRole] = mapped_column(
        SAEnum(TerminalRole, native_enum=False, length=20), nullable=False
    )
    status: Mapped[TerminalStatus] = mapped_column(
        SAEnum(TerminalStatus, native_enum=False, length=20),
        nullable=False,
        default=TerminalStatus.active,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = _created_at()


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    terminal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = _created_at()


class PairingCode(Base):
    __tablename__ = "pairing_codes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    terminal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("terminals.id", ondelete="CASCADE"), nullable=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role: Mapped[TerminalRole] = mapped_column(
        SAEnum(TerminalRole, native_enum=False, length=20), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = _created_at()


# ---------- wallet por tenant ----------
class TenantWallet(Base):
    __tablename__ = "tenant_wallets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[WalletProviderKind] = mapped_column(
        SAEnum(WalletProviderKind, native_enum=False, length=20),
        nullable=False,
        default=WalletProviderKind.lnbits,
    )
    lnbits_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lnbits_wallet_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Llaves encriptadas at-rest (AES-GCM, formato enc:v1:).
    invoice_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    admin_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _created_at()


# ---------- catálogo ----------
class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index(
            "uq_products_tenant_barcode",
            "tenant_id",
            "barcode",
            unique=True,
            postgresql_where=text("barcode IS NOT NULL"),
        ),
        Index("ix_products_tenant_name", "tenant_id", "name"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    price_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = _created_at()


# ---------- órdenes / invoices ----------
class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_tenant_paid_at", "tenant_id", "paid_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    terminal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("terminals.id", ondelete="SET NULL"), index=True, nullable=True
    )
    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, native_enum=False, length=20),
        nullable=False,
        default=OrderStatus.open,
    )
    # Cómo se cobró. Default lightning: es lo único que existía antes de este campo.
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, native_enum=False, length=20),
        nullable=False,
        default=PaymentMethod.lightning,
        server_default=PaymentMethod.lightning.value,
    )
    subtotal_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = _created_at()
    # Cuándo entró el dinero. NO es created_at: la orden se crea al armar el carrito y el
    # corte del día se hace por cuándo se cobró.
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # product_id null = línea de monto libre. Se desnormaliza description + precio.
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(160), nullable=False)
    qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    unit_price_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[WalletProviderKind] = mapped_column(
        SAEnum(WalletProviderKind, native_enum=False, length=20),
        nullable=False,
        default=WalletProviderKind.lnbits,
    )
    provider_wallet_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Referencia con la que el PROVEEDOR identifica este pago, cuando no le alcanza el hash.
    # Lexe indexa por `<created_ms>-ln_<hash>` y no ofrece consulta por hash: sin esto, sus
    # invoices se emitirían pero jamás se podrían reconciliar.
    provider_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bolt11: Mapped[str] = mapped_column(Text, nullable=False)
    payment_hash: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    amount_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, native_enum=False, length=20),
        nullable=False,
        default=InvoiceStatus.pending,
    )
    webhook_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = _created_at()


# ---------- auditoría ----------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"), index=True, nullable=True
    )
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = _created_at()
