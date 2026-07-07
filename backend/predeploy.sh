#!/bin/sh
# Pre-deploy universal: migra Postgres solo si el servicio lo usa.
# El servicio prod single-tenant (SQLite, sin LPOS_DATABASE_URL) debe poder
# desplegar main sin que alembic truene contra un Postgres inexistente.
if [ -n "$LPOS_DATABASE_URL" ]; then
  echo "LPOS_DATABASE_URL presente -> alembic upgrade head"
  exec alembic upgrade head
fi
echo "sin LPOS_DATABASE_URL (single-tenant SQLite) -> sin migraciones"
