"""Failing tests for API error handling scaffold — run before T020."""


def test_unknown_route_returns_404(client):
    r = client.get("/api/v1/nonexistent-route-xyz")
    assert r.status_code == 404


def test_error_response_shape(client):
    r = client.get("/api/v1/nonexistent-route-xyz")
    data = r.get_json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]


def test_error_response_content_type(client):
    r = client.get("/api/v1/nonexistent-route-xyz")
    assert "application/json" in r.content_type
