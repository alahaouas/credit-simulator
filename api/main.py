"""Credit Simulator API — FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import history, simulate

app = FastAPI(
    title="Credit Simulator API",
    version="1.0.0",
    description="REST API for the credit-simulator mortgage calculator.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev server
        "http://localhost:5173",   # Vite dev server (alternative)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulate.router, prefix="/api")
app.include_router(history.router, prefix="/api")
