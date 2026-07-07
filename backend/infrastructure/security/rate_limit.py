"""Rate limiting en memoria (sliding window) para endpoints públicos.

Por proceso: suficiente para el despliegue actual (una instancia en Railway).
Si algún día hay réplicas, migrar el estado a Redis — el punto de entrada
(`rate_limit()`) no cambia.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    """max_requests por window_seconds, por llave (sliding window)."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        cutoff = now - self.window_seconds
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.max_requests:
            return False
        q.append(now)
        # poda ocasional para que llaves viejas no crezcan sin límite
        if len(self._hits) > 10_000:
            for k in [k for k, v in self._hits.items() if not v]:
                del self._hits[k]
        return True


def parse_limit(spec: str) -> tuple[int, float]:
    """'20/60' → (20 requests, 60 segundos)."""
    n, _, secs = spec.partition("/")
    return int(n), float(secs or 60)


def client_ip(request: Request) -> str:
    """IP real del cliente. Detrás del proxy de Railway llega en X-Forwarded-For."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, spec: str):
    """Dependencia FastAPI: 429 si la IP excede el límite para este endpoint."""
    max_requests, window = parse_limit(spec)
    limiter = RateLimiter(max_requests, window)

    async def dependency(request: Request) -> None:
        if not limiter.allow(f"{name}:{client_ip(request)}"):
            raise HTTPException(status_code=429, detail="rate_limited")

    return dependency
