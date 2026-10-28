"""Tests for GET /api/v1/health."""


def test_health_reports_healthy_status_and_version(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["version"] == "v1"
    assert body["service"]


def test_health_response_is_small_and_stable(client):
    body = client.get("/api/v1/health").json()

    assert set(body) == {"status", "service", "version"}
