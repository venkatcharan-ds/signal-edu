"""
Request-ID middleware — stamps every request with a UUID and propagates it
through structlog context so all log lines for a single request share an ID.
"""
from __future__ import annotations

import uuid
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            log.exception("request.unhandled_error", method=request.method, path=request.url.path)
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            log.info(
                "request.complete",
                method=request.method,
                path=request.url.path,
                status=getattr(response, "status_code", None),
                duration_ms=duration_ms,
            )

        response.headers["X-Request-ID"] = request_id
        return response
