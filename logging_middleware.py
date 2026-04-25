"""
middleware/logging_middleware.py
================================
Logs every incoming request and its response status + duration.
Attaches a unique request_id to each request for tracing.
"""

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Attach unique ID to each request
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        logger.info(
            f"[REQ {request_id}] {request.method} {request.url.path} "
            f"client={request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(f"[REQ {request_id}] Unhandled exception: {exc}")
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"[RES {request_id}] status={response.status_code} "
            f"duration={duration_ms:.1f}ms"
        )

        # Expose request ID in response headers for debugging
        response.headers["X-Request-ID"] = request_id
        return response
