#!/bin/sh
# Railway ejecuta el startCommand como argv (sin shell), por eso el arranque va en un
# script: aquí sí se expande $PORT. Fallback 8000 para local.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
