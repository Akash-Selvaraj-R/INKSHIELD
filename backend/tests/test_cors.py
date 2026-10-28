"""Tests for CORS configuration and the frontend's camelCase payload (M4)."""


def test_cors_allows_configured_frontend_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_allows_scan_requests(client):
    response = client.options(
        "/api/v1/scans",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"]


def test_scan_accepts_frontend_camel_case_payload(client):
    response = client.post(
        "/api/v1/scans",
        json={
            "content": "NOVA delivers 50% faster inference",
            "contentType": "landing_page",
            "knowledgeSources": ["claims"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["findings"]) == 1
    assert body["findings"][0]["evidence"][0]["source"] == "Product Claims"


def test_scan_still_accepts_snake_case_payload(client):
    response = client.post(
        "/api/v1/scans",
        json={"content": "50% faster inference", "knowledge_sources": ["claims"]},
    )

    assert response.status_code == 201
    assert len(response.json()["findings"]) == 1
