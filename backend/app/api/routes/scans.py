"""Scan routes: create scans (POST), list process-local scans (GET),
and record human review decisions (PATCH .../review)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.scan import Finding, ReviewRequest, ScanRequest, ScanResponse
from app.services.scanner import (
    FindingNotFoundError,
    ScanNotFoundError,
    ScanStore,
    scan_content,
)

router = APIRouter(tags=["scans"])


def get_scan_store(request: Request) -> ScanStore:
    """Expose the app's in-memory scan store as a route dependency."""
    return request.app.state.scan_store


@router.post(
    "/scans",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scan(
    payload: ScanRequest,
    store: Annotated[ScanStore, Depends(get_scan_store)],
) -> ScanResponse:
    """Scan content with the deterministic rule engine.

    Empty or whitespace-only content is rejected with HTTP 422 by the
    request schema. ``knowledge_sources`` optionally filters which
    knowledge sources may back findings; unknown ids are ignored.
    """
    return store.add(scan_content(payload.content, payload.knowledge_sources))


@router.get("/scans", response_model=list[ScanResponse])
def list_scans(store: Annotated[ScanStore, Depends(get_scan_store)]) -> list[ScanResponse]:
    """List scans created during the current server process (empty when none)."""
    return store.list()


@router.patch(
    "/scans/{scan_id}/findings/{finding_id}/review",
    response_model=Finding,
)
def review_finding(
    scan_id: str,
    finding_id: str,
    payload: ReviewRequest,
    store: Annotated[ScanStore, Depends(get_scan_store)],
) -> Finding:
    """Record a human review decision for one finding (M5).

    ``decision`` must be APPROVED, REJECTED, EDITED or ESCALATED (422
    otherwise); EDITED also requires a non-blank ``correctedText``.
    Unknown scan or finding ids return 404. On success the updated
    finding is returned and persists for subsequent GETs.
    """
    try:
        return store.apply_review(scan_id, finding_id, payload)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FindingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
