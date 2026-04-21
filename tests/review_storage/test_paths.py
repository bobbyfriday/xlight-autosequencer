"""Failing tests for src/review/storage/paths.py — run before T012."""
import os
import pytest

from src.review.storage import paths


def test_library_root_default(state_dir):
    root = paths.library_root()
    assert root == state_dir / "library"


def test_library_root_env_override(tmp_path, monkeypatch):
    custom = tmp_path / "custom_state"
    monkeypatch.setenv("XLIGHT_STATE_HOME", str(custom))
    assert paths.library_root() == custom / "library"


def test_song_session_path(state_dir):
    p = paths.song_session_path("aabbccddeeff0011")
    assert p == state_dir / "library" / "songs" / "aabbccddeeff0011" / "session.json"


def test_library_json_path(state_dir):
    p = paths.library_json_path()
    assert p == state_dir / "library" / "library.json"
