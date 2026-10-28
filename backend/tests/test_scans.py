"""Tests for POST /api/v1/scans and GET /api/v1/scans (M3).

Covers the request contract, every deterministic rule family, evidence
resolution, knowledge-source filtering, scan listing, and determinism.
"""

import re

FINDING_ID_PATTERN = re.compile(r"^INK-\d{4}$")

DEMO_DRAFT = (
    "NOVA is the fastest AI engine on the market, delivering 50% faster inference "
    "with 100% uptime and zero latency. Our NOVA AI platform is completely secure."
)

COMPLIANT_DRAFT = (
    "NOVA Cloud delivers up to 30% faster inference for enterprise AI workloads "
    "on our inference platform."
)

ALL_SOURCES = ["claims", "terms", "guidelines", "prohibited", "facts"]

# Every (source, section, text) tuple that valid seeded evidence may cite.
SEEDED_EVIDENCE = {
    ("Product Claims", "\u00a74.2", "Up to 30% faster inference."),
    ("Terminology", "\u00a73.1", "NOVA Cloud \u00b7 AI infrastructure \u00b7 inference platform"),
    (
        "Brand Guidelines",
        "\u00a71.3",
        "Precise \u00b7 Technical \u00b7 Confident. NOVA is an AI infrastructure company. "
        "Avoid unsupported market superlatives such as \u201cfastest AI engine\u201d, "
        "\u201cbest AI platform\u201d, \u201c#1 AI platform\u201d.",
    ),
    (
        "Prohibited Claims",
        "\u00a75.4",
        "Absolute claims (e.g. \u201c100% uptime\u201d, \u201c100% secure\u201d, "
        "\u201czero latency\u201d) are prohibited; cite approved measured facts instead.",
    ),
    ("Product Facts", "\u00a72.1", "99.9% platform availability."),
}


def create_scan(client, content, knowledge_sources=None):
    payload = {"content": content}
    if knowledge_sources is not None:
        payload["knowledge_sources"] = knowledge_sources
    response = client.post("/api/v1/scans", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def assert_well_formed_finding(finding):
    assert FINDING_ID_PATTERN.match(finding["id"])
    assert finding["category"] in {"CLAIM", "TERMINOLOGY"}
    assert finding["severity"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    assert finding["status"] == "OPEN"
    assert finding["title"]
    assert finding["submitted_text"]
    assert finding["explanation"]
    assert finding["suggested_correction"]
    assert 0 < finding["confidence"] <= 100
    assert finding["evidence"]
    for evidence in finding["evidence"]:
        assert evidence["source"]
        assert evidence["section"]
        assert evidence["text"]


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def test_empty_content_is_rejected_with_422(client):
    response = client.post("/api/v1/scans", json={"content": ""})

    assert response.status_code == 422


def test_whitespace_only_content_is_rejected_with_422(client):
    response = client.post("/api/v1/scans", json={"content": "   \n\t  "})

    assert response.status_code == 422


def test_missing_content_is_rejected_with_422(client):
    response = client.post("/api/v1/scans", json={})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Successful scans: stable shape, summary, score, order, determinism
# ---------------------------------------------------------------------------


def test_successful_scan_returns_stable_structured_response(client):
    body = create_scan(client, DEMO_DRAFT)

    assert set(body) >= {"id", "status", "compliance_score", "summary", "findings"}
    assert body["id"].startswith("scan_")
    assert body["status"] == "completed"
    assert body["content"] == DEMO_DRAFT
    # 1 CRITICAL (15) + 3 HIGH (30) + 2 MEDIUM (10) => 45.
    assert body["summary"] == {
        "total_findings": 6,
        "critical": 1,
        "high": 3,
        "medium": 2,
        "low": 0,
    }
    assert body["compliance_score"] == 45
    for finding in body["findings"]:
        assert_well_formed_finding(finding)


def test_findings_are_returned_in_reading_order_with_sequential_ids(client):
    body = create_scan(client, DEMO_DRAFT)

    ids = [finding["id"] for finding in body["findings"]]
    assert ids == [f"INK-{42 + index:04d}" for index in range(len(ids))]
    positions = [DEMO_DRAFT.index(finding["submitted_text"]) for finding in body["findings"]]
    assert positions == sorted(positions)


def test_scan_of_compliant_content_has_no_findings_and_full_score(client):
    body = create_scan(client, COMPLIANT_DRAFT)

    assert body["findings"] == []
    assert body["summary"]["total_findings"] == 0
    assert body["compliance_score"] == 100


def test_identical_content_produces_identical_findings(client):
    first = create_scan(client, DEMO_DRAFT)
    second = create_scan(client, DEMO_DRAFT)

    assert first["findings"] == second["findings"]
    assert first["summary"] == second["summary"]
    assert first["compliance_score"] == second["compliance_score"]
    assert first["id"] != second["id"]


# ---------------------------------------------------------------------------
# Rule family: unsupported quantitative claims
# ---------------------------------------------------------------------------


def test_flags_performance_claims_above_the_approved_30_percent_limit(client):
    body = create_scan(client, "NOVA delivers 50% faster inference at scale.")

    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["category"] == "CLAIM"
    assert finding["severity"] == "CRITICAL"
    assert finding["submitted_text"] == "50% faster inference"
    assert finding["evidence"][0] == {
        "source": "Product Claims",
        "section": "\u00a74.2",
        "text": "Up to 30% faster inference.",
    }
    assert finding["suggested_correction"] == "Up to 30% faster inference."


def test_does_not_flag_claims_at_or_below_the_approved_limit(client):
    for text in ("Up to 30% faster inference.", "30% faster inference", "20% faster inference"):
        body = create_scan(client, text)
        assert body["findings"] == [], text


# ---------------------------------------------------------------------------
# Rule family: prohibited absolutes
# ---------------------------------------------------------------------------


def test_flags_prohibited_absolute_claims(client):
    expectations = {
        "100% uptime": ("HIGH", "Prohibited absolute availability claim"),
        "100% secure": ("HIGH", "Prohibited absolute security claim"),
        "zero latency": ("HIGH", "Prohibited absolute performance claim"),
    }
    for text, (severity, title) in expectations.items():
        body = create_scan(client, text)
        assert len(body["findings"]) == 1, text
        finding = body["findings"][0]
        assert finding["severity"] == severity, text
        assert finding["title"] == title, text
        assert finding["category"] == "CLAIM"


def test_prohibited_uptime_cites_the_approved_fact_as_evidence(client):
    finding = create_scan(client, "100% uptime")["findings"][0]

    assert finding["evidence"][0] == {
        "source": "Product Facts",
        "section": "\u00a72.1",
        "text": "99.9% platform availability.",
    }
    assert finding["suggested_correction"] == "99.9% platform availability."


# ---------------------------------------------------------------------------
# Rule family: unverified superlatives
# ---------------------------------------------------------------------------


def test_flags_unverified_superlatives(client):
    for text in ("the fastest AI platform", "the best AI platform", "#1 AI platform"):
        body = create_scan(client, text)
        assert len(body["findings"]) == 1, text
        finding = body["findings"][0]
        assert finding["severity"] == "HIGH", text
        assert finding["title"] == "Unverified market superlative", text
        assert finding["category"] == "TERMINOLOGY"
        assert finding["evidence"][0]["source"] == "Brand Guidelines"
        assert finding["evidence"][0]["section"] == "\u00a71.3"


def test_superlative_suppresses_overlapping_terminology_finding(client):
    body = create_scan(client, "the fastest AI engine on the market")

    assert len(body["findings"]) == 1
    assert body["findings"][0]["title"] == "Unverified market superlative"


# ---------------------------------------------------------------------------
# Rule family: unapproved terminology
# ---------------------------------------------------------------------------


def test_flags_unapproved_terminology(client):
    body = create_scan(client, "NOVA AI platform")

    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["category"] == "TERMINOLOGY"
    assert finding["severity"] == "MEDIUM"
    assert finding["submitted_text"] == "NOVA AI platform"
    assert finding["evidence"][0] == {
        "source": "Terminology",
        "section": "\u00a73.1",
        "text": "NOVA Cloud \u00b7 AI infrastructure \u00b7 inference platform",
    }
    assert finding["suggested_correction"] == "NOVA Cloud platform"
    assert finding["confidence"] == 97


def test_flags_ai_engine_as_unapproved_terminology(client):
    body = create_scan(client, "Meet our new AI engine.")

    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["title"] == "Unapproved terminology"
    assert finding["suggested_correction"] == "AI infrastructure"


# ---------------------------------------------------------------------------
# Evidence references
# ---------------------------------------------------------------------------


def test_evidence_only_cites_actual_seeded_knowledge(client):
    body = create_scan(client, DEMO_DRAFT, ALL_SOURCES)

    assert body["findings"]
    for finding in body["findings"]:
        for evidence in finding["evidence"]:
            assert (
                evidence["source"],
                evidence["section"],
                evidence["text"],
            ) in SEEDED_EVIDENCE, f"fabricated evidence: {evidence}"


# ---------------------------------------------------------------------------
# Knowledge-source filtering
# ---------------------------------------------------------------------------


def test_only_claims_selected_limits_findings_to_claim_rules(client):
    body = create_scan(client, "NOVA has 50% faster inference", ["claims"])

    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["severity"] == "CRITICAL"
    assert finding["evidence"][0]["source"] == "Product Claims"

    others = create_scan(
        client, "NOVA AI platform is completely secure with 100% uptime", ["claims"]
    )
    assert others["findings"] == []


def test_only_terms_selected_has_no_superlative_evidence(client):
    body = create_scan(client, "the fastest AI engine on the market", ["terms"])

    # Without the guidelines source there is no superlative evidence, so only
    # the terminology rule for "AI engine" may match.
    assert len(body["findings"]) == 1
    assert body["findings"][0]["title"] == "Unapproved terminology"
    assert body["findings"][0]["evidence"][0]["source"] == "Terminology"

    assert create_scan(client, "50% faster inference", ["terms"])["findings"] == []


def test_prohibited_evidence_falls_back_within_selected_sources(client):
    prohibited_only = create_scan(client, "100% uptime", ["prohibited"])
    finding = prohibited_only["findings"][0]
    # Facts are not selected, so evidence falls back to the selected
    # Prohibited Claims policy chunk — never a fabricated reference.
    assert finding["evidence"][0]["source"] == "Prohibited Claims"
    assert finding["evidence"][0]["section"] == "\u00a75.4"

    with_facts = create_scan(client, "100% uptime", ["prohibited", "facts"])
    assert with_facts["findings"][0]["evidence"][0] == {
        "source": "Product Facts",
        "section": "\u00a72.1",
        "text": "99.9% platform availability.",
    }


def test_evidence_stays_within_the_selected_sources(client):
    expectations = [
        (["claims"], {"Product Claims"}),
        (["terms"], {"Terminology"}),
        (["prohibited"], {"Prohibited Claims"}),
        (["prohibited", "facts"], {"Prohibited Claims", "Product Facts"}),
    ]
    content = "NOVA is the fastest AI engine, 50% faster inference with 100% uptime. NOVA AI platform is completely secure."
    for selection, allowed_sources in expectations:
        body = create_scan(client, content, selection)
        assert body["findings"], selection
        for finding in body["findings"]:
            for evidence in finding["evidence"]:
                assert evidence["source"] in allowed_sources, (selection, evidence)


def test_unknown_knowledge_source_ids_are_ignored_safely(client):
    mixed = create_scan(client, "50% faster inference", ["claims", "ghost-source"])
    assert len(mixed["findings"]) == 1
    assert mixed["status"] == "completed"

    empty = create_scan(client, "50% faster inference", ["ghost-source"])
    assert empty["findings"] == []
    assert empty["summary"] == {
        "total_findings": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    assert empty["compliance_score"] == 100
    assert empty["status"] == "completed"


# ---------------------------------------------------------------------------
# Scan listing
# ---------------------------------------------------------------------------


def test_lists_no_scans_when_none_exist(client):
    response = client.get("/api/v1/scans")

    assert response.status_code == 200
    assert response.json() == []


def test_lists_scans_created_in_the_current_process(client):
    first = create_scan(client, "50% faster inference")
    second = create_scan(client, "100% uptime")

    response = client.get("/api/v1/scans")

    assert response.status_code == 200
    listed = response.json()
    assert [scan["id"] for scan in listed] == [first["id"], second["id"]]
    assert listed[0]["findings"] == first["findings"]
    assert listed[1]["summary"] == second["summary"]
