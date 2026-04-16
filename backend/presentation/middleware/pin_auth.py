from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from application.auth import is_pin_set, is_valid_token

# Routes that don't require auth
PUBLIC_PREFIXES = ("/api/auth/", "/api/health", "/api/webhooks/")


class PinAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public routes and non-API routes
        if not path.startswith("/api/") or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Skip auth if no PIN has been set yet (first-time setup)
        if not await is_pin_set():
            return await call_next(request)

        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token or not is_valid_token(token):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        return await call_next(request)
