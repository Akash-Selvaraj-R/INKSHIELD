"""In-memory audit event log (M6).

Events are recorded only from real, successful operations (scan
creation and human review decisions) — failed requests never produce
entries and nothing is fabricated. Like the scan store, the log lives
in process memory and lasts for the current server process only.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.audit import (
    AuditAction,
    AuditActorType,
    AuditEvent,
    AuditObjectType,
    INITIAL_STATE,
)
from app.schemas.scan import ReviewDecision

# Honest actor labels: the scanner is deterministic (SYSTEM), and no
# authentication exists yet, so human decisions are attributed to the
# generic "Reviewer" role rather than a fabricated person.
SCANNER_ACTOR = "INKSHIELD Scanner"
REVIEWER_ACTOR = "Reviewer"

# Map every review decision to its audit action.
DECISION_ACTIONS: dict[ReviewDecision, AuditAction] = {
    ReviewDecision.APPROVED: AuditAction.REVIEW_APPROVED,
    ReviewDecision.REJECTED: AuditAction.REVIEW_REJECTED,
    ReviewDecision.EDITED: AuditAction.CORRECTION_EDITED,
    ReviewDecision.ESCALATED: AuditAction.REVIEW_ESCALATED,
}


def _next_event_id() -> str:
    return f"audit_{uuid4().hex[:12]}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AuditLog:
    """Thread-safe append-only audit log for the current process."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = threading.Lock()

    def record(
        self,
        *,
        action: AuditAction,
        actor: str,
        actor_type: AuditActorType,
        object_type: AuditObjectType,
        object_id: str,
        previous_state: str,
        new_state: str,
    ) -> AuditEvent:
        """Append one event and return it."""
        event = AuditEvent(
            id=_next_event_id(),
            timestamp=_timestamp(),
            actor=actor,
            actor_type=actor_type,
            action=action,
            object_type=object_type,
            object_id=object_id,
            previous_state=previous_state,
            new_state=new_state,
        )
        with self._lock:
            self._events.append(event)
        return event

    def list(self) -> list[AuditEvent]:
        """All events in chronological (append) order."""
        with self._lock:
            return list(self._events)


def record_scan_completed(log: AuditLog, scan_id: str, finding_count: int) -> AuditEvent:
    """Record that a scan finished (called only after a successful scan)."""
    return log.record(
        action=AuditAction.SCAN_COMPLETED,
        actor=SCANNER_ACTOR,
        actor_type=AuditActorType.SYSTEM,
        object_type=AuditObjectType.SCAN,
        object_id=scan_id,
        previous_state="RUNNING",
        new_state="NEEDS REVIEW" if finding_count else "COMPLETED",
    )


def record_review_decision(
    log: AuditLog,
    finding_id: str,
    decision: ReviewDecision,
    previous_decision: ReviewDecision | None,
) -> AuditEvent:
    """Record a human review decision with its state transition."""
    return log.record(
        action=DECISION_ACTIONS[decision],
        actor=REVIEWER_ACTOR,
        actor_type=AuditActorType.HUMAN,
        object_type=AuditObjectType.FINDING,
        object_id=finding_id,
        previous_state=previous_decision.value if previous_decision else INITIAL_STATE,
        new_state=decision.value,
    )
