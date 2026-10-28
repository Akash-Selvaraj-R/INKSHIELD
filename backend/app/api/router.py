"""Versioned API router assembly."""

from fastapi import APIRouter

from app.api.routes import audit, health, scans

# All M3 endpoints live under this prefix.
API_PREFIX = "/api/v1"

api_router = APIRouter()
api_router.include_router(health.router, prefix=API_PREFIX)
api_router.include_router(scans.router, prefix=API_PREFIX)
api_router.include_router(audit.router, prefix=API_PREFIX)
