"""Pydantic request/response models for the scan API (M3).

The response shapes mirror the TypeScript ``Scan``/``Finding`` types so a
future frontend integration stays straightforward, using Python-style
snake_case field names.
"""

from enum import Enum
from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class Severity(str, Enum):
    """Finding severity levels, ordered most to least severe."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, Enum):
    """Lifecycle status of a finding. Starts OPEN; human review moves it
    to the status matching the submitted decision (M5)."""

    OPEN = "OPEN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    ESCALATED = "ESCALATED"


class ReviewDecision(str, Enum):
    """Decisions a human reviewer may submit (M5). No PENDING value:
    "no decision yet" is represented by ``review.decision = None``."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    ESCALATED = "ESCALATED"


class Review(BaseModel):
    """Human review state attached to a finding."""

    required: bool = True
    decision: ReviewDecision | None = None


class ReviewRequest(BaseModel):
    """PATCH /scans/{scan_id}/findings/{finding_id}/review payload.

    ``corrected_text`` also accepts the frontend's camelCase
    ``correctedText`` spelling. EDITED decisions must carry a non-blank
    corrected text (validated below, so violations surface as 422).
    """

    model_config = ConfigDict(validate_by_name=True)

    decision: ReviewDecision
    corrected_text: str | None = Field(
        default=None,
        validation_alias=AliasChoices("corrected_text", "correctedText"),
    )

    @field_validator("corrected_text")
    @classmethod
    def strip_corrected_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def edited_requires_corrected_text(self) -> "ReviewRequest":
        if self.decision is ReviewDecision.EDITED and not self.corrected_text:
            raise ValueError("correctedText is required and must not be blank when decision is EDITED")
        return self


class Evidence(BaseModel):
    """A citable knowledge record backing a finding."""

    source: str
    section: str
    text: str


class Finding(BaseModel):
    """A single policy violation found in submitted content.

    ``status``/``review``/``corrected_text`` are updated by the human
    review endpoint; the deterministic scan data (title, explanation,
    evidence, confidence, ...) is never altered by a review.
    """

    id: str
    category: str
    severity: Severity
    status: FindingStatus = FindingStatus.OPEN
    title: str
    submitted_text: str
    explanation: str
    suggested_correction: str
    confidence: int = Field(ge=1, le=100)
    evidence: list[Evidence]
    review: Review = Field(default_factory=Review)
    corrected_text: str | None = None


class ScanSummary(BaseModel):
    """Findings tallied by severity."""

    total_findings: int
    critical: int
    high: int
    medium: int
    low: int


class ScanRequest(BaseModel):
    """POST /scans payload: content to scan plus an optional knowledge filter.

    ``knowledge_sources`` also accepts the frontend's camelCase
    ``knowledgeSources`` spelling so the JS client can send its natural
    payload shape (M4 integration).
    """

    model_config = ConfigDict(validate_by_name=True)

    content: str
    knowledge_sources: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("knowledge_sources", "knowledgeSources"),
    )

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
