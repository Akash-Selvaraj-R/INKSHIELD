"""Application configuration for the INKSHIELD backend (M3).

Values are read from environment variables with safe development
defaults so the API runs out of the box. Real deployments override them
via a local ``.env`` file (see ``backend/.env.example``); no secrets
belong in the repository.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the INKSHIELD API."""

    app_name: str = "INKSHIELD API"
    api_version: str = "v1"
    environment: str = "development"


def load_settings() -> Settings:
    """Build settings from the environment, falling back to defaults."""
    defaults = Settings()
    return Settings(
        app_name=os.getenv("INKSHIELD_APP_NAME", defaults.app_name),
        api_version=os.getenv("INKSHIELD_API_VERSION", defaults.api_version),
        environment=os.getenv("INKSHIELD_ENVIRONMENT", defaults.environment),
    )


settings = load_settings()
