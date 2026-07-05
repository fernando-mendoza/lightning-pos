"""Seed del tenant #0 (el comercio actual) en el backend multi-tenant.

Crea usuario owner + tenant + provisiona wallet (idempotente por email). Uso:

    # Local (wallet fake):
    LPOS_TEST_MODE=1 python scripts/seed_tenant_zero.py

    # Staging/prod (wallet LNbits real): setear LPOS_* de la DB/LNbits y:
    SEED_EMAIL=owner@lightningnetwork.tf SEED_PASSWORD=... SEED_TENANT="Lightning POS" \
      python scripts/seed_tenant_zero.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.multitenant.accounts import AccountError, register_account  # noqa: E402
from infrastructure.db.base import SessionLocal  # noqa: E402
from infrastructure.providers import wallet_provider  # noqa: E402


async def main() -> None:
    email = os.environ.get("SEED_EMAIL", "owner@lightningnetwork.tf")
    password = os.environ.get("SEED_PASSWORD", "change-me-please-123")
    tenant_name = os.environ.get("SEED_TENANT", "Lightning POS")
    async with SessionLocal() as session:
        try:
            user, tenant = await register_account(
                session,
                wallet_provider,
                email=email,
                password=password,
                name="Owner",
                tenant_name=tenant_name,
            )
            print(f"OK: tenant {tenant.id} ({tenant.name}) · owner {user.email}")
        except AccountError as e:
            print(f"SKIP ({e}): el owner/tenant probablemente ya existe.")


if __name__ == "__main__":
    asyncio.run(main())
