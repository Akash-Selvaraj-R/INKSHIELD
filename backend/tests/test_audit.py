"""Tests for the audit event architecture (M6).

Covers: events recorded only for successful scans/reviews, correct
event fields and state transitions, chronological ordering, no entries
for failed requests, and persistence on subsequent GETs.
"""

import pytest

from app.schemas.audit import AuditAction

SCAN_CONTENT = "NOVA delivers 50% faster inference with 100% uptime."
ALL_SOURCES = ["claims", "facts", "prohibited", "terms", "guidelines"]


def create_scan(client, content: str = SCAN_CONTENT, sources: list[str] | None = None) -> dict:
    response = client.post(
        "/api/v1/scans",
        json={"content": content, "knowledge_sources": sources if sources is not None else ALL_SOURCES},
    )
    assert response.status_code == 201
    return response.json()


def submit_review(client, scan_id: str, finding_id: str, payload: dict):
    return client.patch(
        f"/api/v1/scans/{scan_id}/findings/{finding_id}/review",
        json=payload,
    )


def get_events(client) -> list[dict]:
    response = client.get("/api/v1/audit-events")
    assert response.status_code == 200
    return response.json()


def test_audit_starts_empty(client):
    assert get_events(client) == []


def test_successful_scan_records_event(client):
    scan = create_scan(client)
    assert len(scan["findings"]) >= 2

    events = get_events(client)
    assert len(events) == 1
    event = events[0]
    assert event["id"].startswith("audit_")
    assert event["timestamp"]  # ISO 8601 UTC
    assert "T" in event["timestamp"]
    assert event["action"] == AuditAction.SCAN_COMPLETED.value
    assert event["actor"] == "INKSHIELD Scanner"
    assert event["actor_type"] == "SYSTEM"
    assert event["object_type"] == "SCAN"
    assert event["object_id"] == scan["id"]
    assert event["previous_state"] == "RUNNING"
    assert event["new_state"] == "NEEDS REVIEW"


def test_scan_without_findings_records_completed(client):
    # No valid knowledge source ids -> deterministic scan with zero findings.
    scan = create_scan(client, content="NOVA Cloud platform overview.", sources=["does_not_exist"])

    assert scan["findings"] == []
    events = get_events(client)
    assert len(events) == 1
    assert events[0]["new_state"] == "COMPLETED"


def test_failed_scan_records_no_event(client):
    response = client.post("/api/v1/scans", json={"content": "   ", "knowledge_sources": ALL_SOURCES})

    assert response.status_code == 422
    assert get_events(client) == []


def test_successful_review_records_decision_event(client):
    scan = create_scan(client)
    finding = scan["findings"][0]

    response = submit_review(client, scan["id"], finding["id"], {"decision": "APPROVED"})

    assert response.status_code == 200
    events = get_events(client)
    assert len(events) == 2  # scan + review
    event = events[1]
    assert event["action"] == AuditAction.REVIEW_APPROVED.value
    assert event["actor"] == "Reviewer"
    assert event["actor_type"] == "HUMAN"
    assert event["object_type"] == "FINDING"
    assert event["object_id"] == finding["id"]
    assert event["previous_state"] == "PENDING"
    assert event["new_state"] == "APPROVED"
    assert event["id"].startswith("audit_")


@pytest.mark.parametrize(
    ("decision", "payload", "expected_action"),
    [
        ("REJECTED", {"decision": "REJECTED"}, "Review rejected"),
        ("EDITED", {"decision": "EDITED", "correctedText": "Up to 30% faster inference."}, "Correction edited"),
        ("ESCALATED", {"decision": "ESCALATED"}, "Review escalated"),
    ],
)
def test_each_decision_records_its_action(client, decision, payload, expected_action):
    scan = create_scan(client)
    finding = scan["findings"][0]

    response = submit_review(client, scan["id"], finding["id"], payload)

    assert response.status_code == 200
    events = get_events(client)
    review_event = events[-1]
    assert review_event["action"] == expected_action
    assert review_event["new_state"] == decision
    assert review_event["previous_state"] == "PENDING"


def test_rere_review_records_previous_state(client):
    scan = create_scan(client)
    finding = scan["findings"][0]
    assert submit_review(client, scan["id"], finding["id"], {"decision": "APPROVED"}).status_code == 200
    assert submit_review(client, scan["id"], finding["id"], {"decision": "REJECTED"}).status_code == 200

    events = get_events(client)
    assert len(events) == 3
    second_review = events[2]
    assert second_review["previous_state"] == "APPROVED"  # transition, not PENDING
    assert second_review["new_state"] == "REJECTED"
    assert second_review["action"] == AuditAction.REVIEW_REJECTED.value


def test_events_are_recorded_in_chronological_order(client):
    scan = create_scan(client)
    submit_review(client, scan["id"], scan["findings"][0]["id"], {"decision": "ESCALATED"})
    create_scan(client, content="NOVA Cloud for enterprise teams.", sources=["terms"])

    events = get_events(client)
    assert [event["action"] for event in events] == [
        AuditAction.SCAN_COMPLETED.value,
        AuditAction.REVIEW_ESCALATED.value,
        AuditAction.SCAN_COMPLETED.value,
    ]
    assert events[1]["object_id"] == scan["findings"][0]["id"]


def test_failed_reviews_record_no_events(client):
    scan = create_scan(client)
    finding = scan["findings"][0]
    baseline = len(get_events(client))

    # Unknown scan, unknown finding, invalid decision, blank EDITED text.
    assert submit_review(client, "scan_missing", finding["id"], {"decision": "APPROVED"}).status_code == 404
    assert submit_review(client, scan["id"], "INK-9999", {"decision": "APPROVED"}).status_code == 404
    assert submit_review(client, scan["id"], finding["id"], {"decision": "MAYBE"}).status_code == 422
    assert submit_review(client, scan["id"], finding["id"], {"decision": "EDITED"}).status_code == 422

    assert len(get_events(client)) == baseline


def test_events_persist_for_subsequent_gets(client):
    scan = create_scan(client)
    submit_review(client, scan["id"], scan["findings"][0]["id"], {"decision": "EDITED", "correctedText": "99.9% uptime."})

    first = get_events(client)
    second = get_events(client)

    assert len(first) == 2
    assert second == first
    # Audit data is independent of the scan list endpoint.
    assert len(client.get("/api/v1/scans").json()) == 1
    assert len(get_events(client)) == 2
