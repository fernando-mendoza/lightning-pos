#!/bin/sh
# Railway ejecuta el startCommand como argv (sin shell), por eso el arranque va en un
# script: aquí sí se expande $PORT. Fallback 8000 para local.

# Sidecar de Lexe: sólo si hay credencial. Es config de PROCESO (una wallet por sidecar),
# así que el tenant que use `provider=lexe` cobra CONTRA ESTA wallet. Si el sidecar no
# levanta, el backend igual arranca y el cobro con bitcoin devuelve 503 `lightning_unavailable`
# — preferimos un POS que cobra en efectivo a un POS que no arranca.
if [ -n "$LEXE_CLIENT_CREDENTIALS" ]; then
  echo "LEXE_CLIENT_CREDENTIALS presente -> levantando lexe-sidecar en 127.0.0.1:5393"
  mkdir -p /app/data/lexe
  LEXE_DATA_DIR=/app/data/lexe \
  /usr/local/bin/lexe-sidecar --listen-addr 127.0.0.1:5393 --data-dir /app/data/lexe &
else
  echo "sin LEXE_CLIENT_CREDENTIALS -> sin sidecar de Lexe"
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
