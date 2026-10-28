"""Scan routes: create scans (POST) and list process-local scans (GET)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.schemas.scan import ScanRequest, ScanResponse
from app.services.scanner import ScanStore, scan_content

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
