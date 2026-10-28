"""Shared pytest fixtures for the INKSHIELD backend tests."""

import sys
from pathlib import Path

# Make the backend package importable regardless of how pytest is invoked
# (e.g. `python -m pytest backend/tests -q` from the repository root).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    """A fresh app (and fresh in-memory scan store) per test."""
    with TestClient(create_app()) as test_client:
        yield test_client
