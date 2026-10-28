"""INKSHIELD FastAPI application (M3 backend foundation).

Run locally from ``backend/`` with:

    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.services.audit import AuditLog
from app.services.scanner import ScanStore


def create_app() -> FastAPI:
    """Application factory: each app instance gets its own in-memory
    scan store and audit log, which keeps tests isolated from one another."""
    app = FastAPI(title=settings.app_name, version=settings.api_version)
    # Allow the Next.js frontend (local dev or Vercel) to call the API.
    # Origins come from INKSHIELD_CORS_ORIGINS; no credentials are shared.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.scan_store = ScanStore()
    app.state.audit_log = AuditLog()
    app.include_router(api_router)
    return app


# Uvicorn entry point: ``uvicorn app.main:app``.
app = create_app()
