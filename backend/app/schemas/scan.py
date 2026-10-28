"""Pydantic request/response models for the scan API (M3).

The response shapes mirror the TypeScript ``Scan``/``Finding`` types so a
future frontend integration stays straightforward, using Python-style
snake_case field names.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    """Finding severity levels, ordered most to least severe."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Evidence(BaseModel):
    """A citable knowledge record backing a finding."""

    source: str
    section: str
    text: str


class Finding(BaseModel):
    """A single policy violation found in submitted content."""

    id: str
    category: str
    severity: Severity
    status: Literal["OPEN"] = "OPEN"
    title: str
    submitted_text: str
    explanation: str
    suggested_correction: str
    confidence: int = Field(ge=1, le=100)
    evidence: list[Evidence]


class ScanSummary(BaseModel):
    """Findings tallied by severity."""

    total_findings: int
    critical: int
    high: int
    medium: int
    low: int


class ScanRequest(BaseModel):
    """POST /scans payload: content to scan plus an optional knowledge filter."""

    content: str
    knowledge_sources: list[str] = Field(default_factory=list)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty or whitespace-only")
        return value


class ScanResponse(BaseModel):
    """The stable scan result returned by POST /scans and GET /scans."""

    id: str
    status: Literal["completed"] = "completed"
    compliance_score: int = Field(ge=0, le=100)
    summary: ScanSummary
    findings: list[Finding]
    content: str


class HealthResponse(BaseModel):
    """GET /health payload identifying the service and its API version."""

    status: Literal["healthy"]
    service: str
    version: str
