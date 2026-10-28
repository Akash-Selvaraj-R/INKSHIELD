"""Audit event routes: list recorded events (GET, M6)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.schemas.audit import AuditEvent
from app.services.audit import AuditLog

router = APIRouter(tags=["audit"])


def get_audit_log(request: Request) -> AuditLog:
    """Expose the app's in-memory audit log as a route dependency."""
    return request.app.state.audit_log


@router.get("/audit-events", response_model=list[AuditEvent])
def list_audit_events(log: Annotated[AuditLog, Depends(get_audit_log)]) -> list[AuditEvent]:
    """List audit events recorded during the current server process.

    Events appear in chronological (append) order and only reflect real
    operations — scans and review decisions that succeeded.
    """
    return log.list()
