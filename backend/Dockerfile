FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl unzip \
 && rm -rf /var/lib/apt/lists/*

# Sidecar de Lexe: va DENTRO de esta imagen, no en un servicio aparte, porque la cuenta de
# Railway está en trial y un servicio extra consume crédito. Trade-off explícito: es un
# segundo proceso en el contenedor, y si muere el rail Lightning se cae — por eso el fallo
# sale como 503 `lightning_unavailable` (honesto) y la Fase C lo va a vigilar.
# Versión FIJA a propósito: `latest` haría que dos builds del mismo commit no sean iguales.
ARG LEXE_SIDECAR_VERSION=v0.4.18
RUN curl -fsSL -o /tmp/sc.zip \
      "https://github.com/lexe-app/lexe-sidecar-sdk/releases/download/lexe-sidecar-${LEXE_SIDECAR_VERSION}/lexe-sidecar-linux-x86_64.zip" \
 && unzip -j -o /tmp/sc.zip -d /usr/local/bin \
 && rm /tmp/sc.zip \
 && chmod +x /usr/local/bin/lexe-sidecar \
 && /usr/local/bin/lexe-sidecar --help >/dev/null

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 app \
 && mkdir -p /app/data \
 && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
