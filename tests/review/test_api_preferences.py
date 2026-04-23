"""Failing tests for GET/PUT /api/v1/preferences — run before T119."""

DEFAULTS = {
    "mode": "dark",
    "density": "comfortable",
    "inspector_open": True,
    "tweaks_open": False,
    "last_song_id": None,
    "last_screen": "library",
    "last_playhead_ms_by_song": {},
    "layout_id": None,
    "library_state_version": 0,
}


def test_get_preferences_returns_200(client):
    r = client.get("/api/v1/preferences")
    assert r.status_code == 200


def test_get_preferences_returns_default_shape(client):
    r = client.get("/api/v1/preferences")
    data = r.get_json()
    for key in DEFAULTS:
        assert key in data, f"Missing key: {key}"


def test_get_preferences_default_mode_is_dark(client):
    r = client.get("/api/v1/preferences")
    assert r.get_json()["mode"] == "dark"


def test_put_preferences_partial_update(client):
    r = client.put(
        "/api/v1/preferences",
        json={"mode": "light"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["mode"] == "light"


def test_put_preferences_other_fields_unchanged(client):
    r = client.put(
        "/api/v1/preferences",
        json={"mode": "light"},
        content_type="application/json",
    )
    data = r.get_json()
    assert data["density"] == "comfortable"
    assert data["inspector_open"] is True


def test_put_preferences_density_update(client):
    r = client.put(
        "/api/v1/preferences",
        json={"density": "compact"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["density"] == "compact"


def test_put_preferences_inspector_toggle(client):
    r = client.put(
        "/api/v1/preferences",
        json={"inspector_open": False},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["inspector_open"] is False


def test_put_preferences_invalid_mode_returns_400(client):
    r = client.put(
        "/api/v1/preferences",
        json={"mode": "neon"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_put_preferences_invalid_mode_error_code(client):
    r = client.put(
        "/api/v1/preferences",
        json={"mode": "neon"},
        content_type="application/json",
    )
    data = r.get_json()
    assert "error" in data
    assert data["error"]["code"] == "invalid_preferences"


def test_put_preferences_invalid_density_returns_400(client):
    r = client.put(
        "/api/v1/preferences",
        json={"density": "huge"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_put_preferences_update_persists(client):
    """Two GET/PUT requests share the same library state in one session."""
    client.put(
        "/api/v1/preferences",
        json={"mode": "light"},
        content_type="application/json",
    )
    r2 = client.get("/api/v1/preferences")
    assert r2.get_json()["mode"] == "light"


def test_put_preferences_last_playhead_update(client):
    payload = {"last_playhead_ms_by_song": {"aabb1122": 45200}}
    r = client.put("/api/v1/preferences", json=payload, content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["last_playhead_ms_by_song"] == {"aabb1122": 45200}
