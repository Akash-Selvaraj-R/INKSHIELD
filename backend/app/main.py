"""INKSHIELD FastAPI application (M3 backend foundation).

Run locally from ``backend/`` with:

    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.services.scanner import ScanStore


def create_app() -> FastAPI:
    """Application factory: each app instance gets its own in-memory
    scan store, which keeps tests isolated from one another."""
    app = FastAPI(title=settings.app_name, version=settings.api_version)
    app.state.scan_store = ScanStore()
    app.include_router(api_router)
    return app


# Uvicorn entry point: ``uvicorn app.main:app``.
app = create_app()
