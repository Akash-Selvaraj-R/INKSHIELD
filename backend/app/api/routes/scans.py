"""Scan routes: create scans (POST), list process-local scans (GET),
and record human review decisions (PATCH .../review).

Both write endpoints append audit events (M6) after — and only after —
the underlying store operation succeeds.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.routes.audit import get_audit_log
from app.schemas.scan import Finding, ReviewRequest, ScanRequest, ScanResponse
from app.services.audit import AuditLog, record_review_decision, record_scan_completed
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
    audit_log: Annotated[AuditLog, Depends(get_audit_log)],
) -> ScanResponse:
    """Scan content with the deterministic rule engine.

    Empty or whitespace-only content is rejected with HTTP 422 by the
    request schema. ``knowledge_sources`` optionally filters which
    knowledge sources may back findings; unknown ids are ignored.
    Successful scans are appended to the audit log (M6).
    """
    scan = store.add(scan_content(payload.content, payload.knowledge_sources))
    record_scan_completed(audit_log, scan.id, len(scan.findings))
    return scan


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
    audit_log: Annotated[AuditLog, Depends(get_audit_log)],
) -> Finding:
    """Record a human review decision for one finding (M5).

    ``decision`` must be APPROVED, REJECTED, EDITED or ESCALATED (422
    otherwise); EDITED also requires a non-blank ``correctedText``.
    Unknown scan or finding ids return 404. On success the updated
    finding is returned, persists for subsequent GETs, and the state
    transition is appended to the audit log (M6) — failed requests are
    never audited.
    """
    try:
        finding, previous_decision = store.apply_review(scan_id, finding_id, payload)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FindingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    record_review_decision(audit_log, finding_id, payload.decision, previous_decision)
    return finding
