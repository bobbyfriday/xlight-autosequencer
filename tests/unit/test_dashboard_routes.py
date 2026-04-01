"""Tests for dashboard and theme API routes."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def _tmp_xlight(tmp_path):
    """Set up a temporary ~/.xlight directory for tests."""
    xlight_dir = tmp_path / ".xlight"
    xlight_dir.mkdir()
    (xlight_dir / "custom_themes").mkdir()
    library_path = xlight_dir / "library.json"
    library_path.write_text(json.dumps({"version": "1.0", "entries": []}))
    return xlight_dir, library_path


@pytest.fixture
def app(_tmp_xlight):
    """Create a test Flask app in upload/dashboard mode."""
    xlight_dir, library_path = _tmp_xlight

    with patch("src.library.DEFAULT_LIBRARY_PATH", library_path):
        from src.review.server import create_app
        app = create_app(analysis_path=None, audio_path=None)
        app.config["TESTING"] = True
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


class TestDashboardRoutes:
    """Test that the dashboard homepage and library routes work."""

    def test_homepage_serves_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"dashboard" in resp.data.lower() or b"xLight" in resp.data

    def test_library_view_redirects(self, client):
        resp = client.get("/library-view")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")

    def test_library_returns_empty(self, client):
        resp = client.get("/library")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "entries" in data
        assert len(data["entries"]) == 0

    def test_library_enriched_fields(self, client, _tmp_xlight):
        """Test that the library endpoint returns enriched fields."""
        xlight_dir, library_path = _tmp_xlight

        # Create a fake analysis file and library entry
        analysis_dir = xlight_dir / "songs"
        analysis_dir.mkdir()
        analysis_file = analysis_dir / "test_hierarchy.json"
        analysis_file.write_text(json.dumps({
            "schema_version": "2.0.0",
            "validation": {"overall_score": 0.85},
            "song": {"title": "Test Song", "artist": "Test Artist"},
        }))

        library_path.write_text(json.dumps({
            "version": "1.0",
            "entries": [{
                "source_hash": "abc123",
                "source_file": str(analysis_dir / "test.mp3"),
                "filename": "test.mp3",
                "analysis_path": str(analysis_file),
                "duration_ms": 180000,
                "estimated_tempo_bpm": 120.0,
                "track_count": 22,
                "stem_separation": True,
                "analyzed_at": 1711843200000,
            }],
        }))

        resp = client.get("/library")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["title"] == "Test Song"
        assert entry["artist"] == "Test Artist"
        assert entry["quality_score"] == 0.85
        assert "has_phonemes" in entry
        assert "has_story" in entry
        assert "file_exists" in entry
        assert "analysis_exists" in entry

    def test_timeline_serves_index(self, client):
        resp = client.get("/timeline")
        assert resp.status_code == 200

    def test_phonemes_view_serves_page(self, client):
        resp = client.get("/phonemes-view")
        assert resp.status_code == 200


class TestThemeRoutes:
    """Test theme CRUD endpoints."""

    def test_theme_list(self, client):
        resp = client.get("/themes/list")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "themes" in data
        # Should have built-in themes
        assert len(data["themes"]) > 0
        # Each theme should have is_builtin flag
        for theme in data["themes"]:
            assert "is_builtin" in theme

    def test_theme_editor_page(self, client):
        resp = client.get("/themes/editor")
        assert resp.status_code == 200

    def test_create_custom_theme(self, client, _tmp_xlight):
        xlight_dir, _ = _tmp_xlight
        with patch("src.themes.library._DEFAULT_CUSTOM_DIR", xlight_dir / "custom_themes"):
            resp = client.post("/themes/create", json={
                "name": "Test Theme",
                "mood": "ethereal",
                "occasion": "general",
                "genre": "any",
                "intent": "A test theme",
                "palette": ["#ff0000", "#00ff00"],
                "accent_palette": ["#0000ff"],
                "layers": [{"effect": "Shimmer", "blend_mode": "Normal", "parameter_overrides": {}}],
            })
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["status"] == "created"

    def test_create_duplicate_name_409(self, client, _tmp_xlight):
        xlight_dir, _ = _tmp_xlight
        theme_data = {
            "name": "Dup Theme",
            "mood": "dark",
            "occasion": "general",
            "genre": "any",
            "intent": "test",
            "palette": ["#000000", "#ff0000"],
            "layers": [{"effect": "Fire", "blend_mode": "Normal", "parameter_overrides": {}}],
        }
        with patch("src.themes.library._DEFAULT_CUSTOM_DIR", xlight_dir / "custom_themes"):
            client.post("/themes/create", json=theme_data)
            resp = client.post("/themes/create", json=theme_data)
            assert resp.status_code == 409

    def test_edit_builtin_403(self, client):
        # Get a builtin theme name
        resp = client.get("/themes/list")
        themes = resp.get_json()["themes"]
        builtin = next((t for t in themes if t["is_builtin"]), None)
        if builtin is None:
            pytest.skip("No built-in themes found")
        resp = client.put(f"/themes/{builtin['name']}", json=builtin)
        assert resp.status_code == 403

    def test_delete_builtin_403(self, client):
        resp = client.get("/themes/list")
        themes = resp.get_json()["themes"]
        builtin = next((t for t in themes if t["is_builtin"]), None)
        if builtin is None:
            pytest.skip("No built-in themes found")
        resp = client.delete(f"/themes/{builtin['name']}")
        assert resp.status_code == 403
