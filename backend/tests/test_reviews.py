"""Tests for the human review workflow endpoint (M5).

Covers all four decisions, 404/422 validation, preservation of the
deterministic finding data, isolation of unrelated findings, and
persistence of the updated state on subsequent GETs.
"""

REVIEW_CONTENT = "NOVA delivers 50% faster inference with 100% uptime."
ALL_SOURCES = ["claims", "facts", "prohibited", "terms", "guidelines"]


def create_scan(client) -> dict:
    """Create a scan whose findings can be reviewed."""
    response = client.post(
        "/api/v1/scans",
        json={"content": REVIEW_CONTENT, "knowledge_sources": ALL_SOURCES},
    )
    assert response.status_code == 201
    scan = response.json()
    # The content above must yield at least two findings so the tests can
    # assert that unrelated findings are never mutated.
    assert len(scan["findings"]) >= 2
    return scan


def submit_review(client, scan_id: str, finding_id: str, payload: dict):
    return client.patch(
        f"/api/v1/scans/{scan_id}/findings/{finding_id}/review",
        json=payload,
    )


def get_finding_from_store(client, scan_id: str, finding_id: str) -> dict:
    """Re-fetch the scan through GET and return the stored finding."""
    response = client.get("/api/v1/scans")
    assert response.status_code == 200
    scan = next(item for item in response.json() if item["id"] == scan_id)
    return next(item for item in scan["findings"] if item["id"] == finding_id)


def test_approved_sets_status_and_decision(client):
    scan = create_scan(client)
    target, untouched = scan["findings"][0], scan["findings"][1]

    response = submit_review(client, scan["id"], target["id"], {"decision": "APPROVED"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == target["id"]
    assert body["status"] == "APPROVED"
    assert body["review"] == {"required": True, "decision": "APPROVED"}
    assert body["corrected_text"] is None

    # Deterministic finding data is preserved exactly.
    assert body["title"] == target["title"]
    assert body["submitted_text"] == target["submitted_text"]
    assert body["explanation"] == target["explanation"]
    assert body["suggested_correction"] == target["suggested_correction"]
    assert body["confidence"] == target["confidence"]
    assert body["evidence"] == target["evidence"]
    assert body["severity"] == target["severity"]
    assert body["category"] == target["category"]

    # The unrelated finding was never mutated.
    other = get_finding_from_store(client, scan["id"], untouched["id"])
    assert other["status"] == "OPEN"
    assert other["review"]["decision"] is None


def test_rejected_sets_status_and_decision(client):
    scan = create_scan(client)
    target = scan["findings"][0]

    response = submit_review(client, scan["id"], target["id"], {"decision": "REJECTED"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["review"] == {"required": True, "decision": "REJECTED"}
    # Rejection does not invent a correction.
    assert body["corrected_text"] is None
    assert body["suggested_correction"] == target["suggested_correction"]

    stored = get_finding_from_store(client, scan["id"], target["id"])
    assert stored["status"] == "REJECTED"
    assert stored["review"]["decision"] == "REJECTED"


def test_edited_stores_corrected_text_and_preserves_suggestion(client):
    scan = create_scan(client)
    target = scan["findings"][0]
    corrected = "Up to 30% faster inference."

    response = submit_review(
        client,
        scan["id"],
        target["id"],
        {"decision": "EDITED", "correctedText": corrected},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EDITED"
    assert body["review"] == {"required": True, "decision": "EDITED"}
    assert body["corrected_text"] == corrected
    # The suggested correction is preserved alongside the corrected text.
    assert body["suggested_correction"] == target["suggested_correction"]
    assert body["explanation"] == target["explanation"]
    assert body["evidence"] == target["evidence"]


def test_edited_accepts_snake_case_corrected_text(client):
    scan = create_scan(client)
    target = scan["findings"][0]

    response = submit_review(
        client,
        scan["id"],
        target["id"],
        {"decision": "EDITED", "corrected_text": " 99.9% platform availability. "},
    )

    assert response.status_code == 200
    # Whitespace is stripped server-side.
    assert response.json()["corrected_text"] == "99.9% platform availability."


def test_escalated_sets_status_and_decision(client):
    scan = create_scan(client)
    target = scan["findings"][0]

    response = submit_review(client, scan["id"], target["id"], {"decision": "ESCALATED"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ESCALATED"
    assert body["review"] == {"required": True, "decision": "ESCALATED"}

    stored = get_finding_from_store(client, scan["id"], target["id"])
    assert stored["status"] == "ESCALATED"
    assert stored["review"]["decision"] == "ESCALATED"


def test_unknown_scan_returns_404(client):
    scan = create_scan(client)
    target = scan["findings"][0]

    response = submit_review(client, "scan_does_not_exist", target["id"], {"decision": "APPROVED"})

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_unknown_finding_returns_404(client):
    scan = create_scan(client)

    response = submit_review(client, scan["id"], "INK-9999", {"decision": "APPROVED"})

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "INK-9999" in detail
    assert "was not found" in detail
    # The scan's real findings are untouched by the failed request.
    for finding in scan["findings"]:
        stored = get_finding_from_store(client, scan["id"], finding["id"])
        assert stored["status"] == "OPEN"
        assert stored["review"]["decision"] is None


def test_invalid_decision_returns_422(client):
    scan = create_scan(client)
    target = scan["findings"][0]

    response = submit_review(client, scan["id"], target["id"], {"decision": "MAYBE"})

    assert response.status_code == 422


def test_malformed_payload_returns_422(client):
    scan = create_scan(client)
    target = scan["findings"][0]
    url = f"/api/v1/scans/{scan['id']}/findings/{target['id']}/review"

    # Missing decision.
    assert client.patch(url, json={}).status_code == 422
    # Decision of the wrong type.
    assert client.patch(url, json={"decision": 123}).status_code == 422
    # Corrected text of the wrong type.
    assert (
        client.patch(url, json={"decision": "EDITED", "correctedText": 7}).status_code
        == 422
    )
    # Not JSON at all.
    assert (
        client.patch(
            url,
            content="definitely not json",
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    # EDITED without a usable corrected text.
    assert client.patch(url, json={"decision": "EDITED"}).status_code == 422
    assert (
        client.patch(url, json={"decision": "EDITED", "correctedText": "   "}).status_code
        == 422
    )


def test_updated_state_persists_on_subsequent_get(client):
    scan = create_scan(client)
    target, untouched = scan["findings"][0], scan["findings"][1]

    first = submit_review(client, scan["id"], target["id"], {"decision": "EDITED", "correctedText": "Up to 30% faster inference."})
    assert first.status_code == 200

    response = client.get("/api/v1/scans")
    assert response.status_code == 200
    stored_scan = next(item for item in response.json() if item["id"] == scan["id"])

    # Score and summary stay deterministic: a review never re-scans content.
    assert stored_scan["compliance_score"] == scan["compliance_score"]
    assert stored_scan["summary"] == scan["summary"]
    assert stored_scan["content"] == scan["content"]

    stored_target = next(item for item in stored_scan["findings"] if item["id"] == target["id"])
    assert stored_target["status"] == "EDITED"
    assert stored_target["review"]["decision"] == "EDITED"
    assert stored_target["corrected_text"] == "Up to 30% faster inference."
    assert stored_target["suggested_correction"] == target["suggested_correction"]

    stored_other = next(item for item in stored_scan["findings"] if item["id"] == untouched["id"])
    assert stored_other["status"] == "OPEN"
    assert stored_other["review"]["decision"] is None


def test_cors_preflight_allows_patch_reviews(client):
    response = client.options(
        "/api/v1/scans/scan_x/findings/INK-0042/review",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "PATCH" in response.headers["access-control-allow-methods"]
