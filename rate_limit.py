"""
middleware/rate_limit.py
========================
Rate limiting using SlowAPI (built on limits library).

Limits:
    /analyze endpoints   → 10 requests / minute per IP
    /auth endpoints      → 20 requests / minute per IP
    Global fallback      → 100 requests / minute per IP

Usage in routes:
    @router.post("/analyze")
    @limiter.limit("10/minute")
    async def analyze(request: Request, ...):
        ...
"""

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
except ModuleNotFoundError:  # pragma: no cover
    class RateLimitExceeded(Exception):
        retry_after = 60

    def get_remote_address(request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    class Limiter:
        def __init__(self, *args, **kwargs):
            pass

        def limit(self, _value: str):
            def decorator(func):
                return func
            return decorator
from fastapi import Request
from fastapi.responses import JSONResponse

# ── Limiter instance (shared across all route files) ──
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


# ── Custom error handler ───────────────────────────────
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a clean JSON error instead of the default plain-text 429."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded. Retry after {exc.retry_after} seconds.",
            "retry_after": exc.retry_after,
        },
    )
