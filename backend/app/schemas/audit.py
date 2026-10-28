"""Pydantic models for the audit event architecture (M6).

The shapes mirror the frontend ``AuditEvent`` type in
``lib/api/types.ts`` using Python-style snake_case field names, with
string-valued enums so events can be displayed directly in the audit
table.
"""

from enum import Enum

from pydantic import BaseModel


class AuditActorType(str, Enum):
    """Who (or what) performed the action — mirrors the frontend
    ``ActorType``."""

    HUMAN = "HUMAN"
    AI = "AI"
    SYSTEM = "SYSTEM"


class AuditObjectType(str, Enum):
    """Kind of object an event refers to — mirrors the frontend
    ``AuditEvent.objectType`` union."""

    SCAN = "SCAN"
    FINDING = "FINDING"
    KNOWLEDGE_SOURCE = "KNOWLEDGE_SOURCE"


class AuditAction(str, Enum):
    """Recorded actions, phrased for direct display in the audit table."""

    SCAN_COMPLETED = "Scan completed"
    REVIEW_APPROVED = "Review approved"
    REVIEW_REJECTED = "Review rejected"
    CORRECTION_EDITED = "Correction edited"
    REVIEW_ESCALATED = "Review escalated"


# State used for events whose "previous" condition was "nothing yet".
INITIAL_STATE = "PENDING"
SCAN_RUNNING_STATE = "RUNNING"
SCAN_NEEDS_REVIEW_STATE = "NEEDS REVIEW"
SCAN_COMPLETED_STATE = "COMPLETED"


class AuditEvent(BaseModel):
    """One append-only audit record: who did what to which object,
    including the state transition it caused."""

    id: str
    # ISO 8601 UTC timestamp (e.g. 2026-10-28T13:05:11+00:00).
    timestamp: str
    actor: str
    actor_type: AuditActorType
    action: AuditAction
    object_type: AuditObjectType
    object_id: str
    previous_state: str
    new_state: str
