"""Health check route for the INKSHIELD API."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.scan import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report service health and the API version."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.api_version,
    )
