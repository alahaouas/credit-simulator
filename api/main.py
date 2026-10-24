"""Credit Simulator API — FastAPI application entry point."""
from __future__ import annotations

import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .constants import DEFAULT_CORS_ORIGINS
from .limiter import limiter
from .routes import alerts, api_keys, history, preferences, profiles, share, simulate

app = FastAPI(
    title="Credit Simulator API",
    version="1.0.0",
    description="REST API for the credit-simulator mortgage calculator.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_extra = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if "*" in _extra:
    raise RuntimeError(
        "ALLOWED_ORIGINS must not contain '*' — this API uses allow_credentials=True, "
        "and a wildcard origin combined with credentials is invalid per the CORS spec "
        "and rejected by browsers. List explicit origins instead."
    )
_origins = list(DEFAULT_CORS_ORIGINS) + _extra

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No CSP here: the API returns JSON, and /api/docs loads Swagger UI from a CDN.
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


# Registered after CORSMiddleware, so it wraps it and also covers preflight responses.
@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response

app.include_router(simulate.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(share.router, prefix="/api")
app.include_router(preferences.router, prefix="/api")
app.include_router(api_keys.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
