"""Unit tests for src/settings.py — settings file read/write."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Tests for load_settings()
# ---------------------------------------------------------------------------

class TestLoadSettings:
    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        settings_file = tmp_path / ".xlight" / "settings.json"
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import load_settings
            result = load_settings()
        assert result == {}

    def test_returns_dict_when_file_exists(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"layout_path": "/some/path.xml"}))
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import load_settings
            result = load_settings()
        assert result == {"layout_path": "/some/path.xml"}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{invalid json")
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import load_settings
            result = load_settings()
        assert result == {}


# ---------------------------------------------------------------------------
# Tests for save_settings()
# ---------------------------------------------------------------------------

class TestSaveSettings:
    def test_creates_file_when_missing(self, tmp_path):
        settings_file = tmp_path / ".xlight" / "settings.json"
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import save_settings
            save_settings({"layout_path": "/a/b.xml"})
        assert settings_file.exists()
        data = json.loads(settings_file.read_text())
        assert data["layout_path"] == "/a/b.xml"

    def test_merges_with_existing_keys(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"other_key": "value", "layout_path": "/old.xml"}))
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import save_settings
            save_settings({"layout_path": "/new.xml"})
        data = json.loads(settings_file.read_text())
        assert data["layout_path"] == "/new.xml"
        assert data["other_key"] == "value"

    def test_creates_parent_directory(self, tmp_path):
        settings_file = tmp_path / "nested" / "dir" / "settings.json"
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import save_settings
            save_settings({"layout_path": "/x.xml"})
        assert settings_file.exists()


# ---------------------------------------------------------------------------
# Tests for round-trip save + load
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_save_then_load_preserves_all_keys(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        data = {"layout_path": "/path/to/layout.xml", "other": "value"}
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import load_settings, save_settings
            save_settings(data)
            result = load_settings()
        assert result == data


# ---------------------------------------------------------------------------
# Tests for get_layout_path()
# ---------------------------------------------------------------------------

class TestGetLayoutPath:
    def test_returns_none_when_not_set(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import get_layout_path
            result = get_layout_path()
        assert result is None

    def test_returns_none_when_layout_path_is_null(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"layout_path": None}))
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import get_layout_path
            result = get_layout_path()
        assert result is None

    def test_returns_path_when_set(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"layout_path": "/some/path.xml"}))
        with patch("src.settings.SETTINGS_PATH", settings_file):
            from src.settings import get_layout_path
            result = get_layout_path()
        assert result == Path("/some/path.xml")
        assert isinstance(result, Path)
