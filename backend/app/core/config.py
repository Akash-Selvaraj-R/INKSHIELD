"""Application configuration for the INKSHIELD backend (M3).

Values are read from environment variables with safe development
defaults so the API runs out of the box. Real deployments override them
via a local ``.env`` file (see ``backend/.env.example``); no secrets
belong in the repository.
"""

import os
from dataclasses import dataclass

# Local Next.js dev servers allowed to call the API out of the box.
# Production deployments must set INKSHIELD_CORS_ORIGINS to their real
# frontend origin(s), e.g. the Vercel app URL (comma-separated).
DEFAULT_CORS_ORIGINS: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the INKSHIELD API."""

    app_name: str = "INKSHIELD API"
    api_version: str = "v1"
    environment: str = "development"
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS


def _parse_origins(raw: str) -> tuple[str, ...]:
    origins = tuple(origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip())
    return origins or DEFAULT_CORS_ORIGINS


def load_settings() -> Settings:
    """Build settings from the environment, falling back to defaults."""
    defaults = Settings()
    return Settings(
        app_name=os.getenv("INKSHIELD_APP_NAME", defaults.app_name),
        api_version=os.getenv("INKSHIELD_API_VERSION", defaults.api_version),
        environment=os.getenv("INKSHIELD_ENVIRONMENT", defaults.environment),
        cors_origins=_parse_origins(os.getenv("INKSHIELD_CORS_ORIGINS", "")),
    )


settings = load_settings()
