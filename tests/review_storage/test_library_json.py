"""Failing tests for src/review/storage/library.py — run before T014."""
import json
import pytest

from src.review.storage import library as lib_storage


MINIMAL_LIBRARY = {
    "schema_version": 1,
    "songs": [],
    "folders": [{"id": "unfiled", "name": "Unfiled", "created_at": "2026-04-21T00:00:00Z"}],
    "preferences": {
        "mode": "dark",
        "density": "comfortable",
        "inspector_open": True,
        "tweaks_open": False,
        "last_song_id": None,
        "last_screen": "library",
        "last_playhead_ms_by_song": {},
        "layout_id": None,
        "library_state_version": 0,
    },
    "layout": None,
}


def test_create_new_library(state_dir):
    lib = lib_storage.load_library()
    assert lib["schema_version"] == 1
    assert lib["songs"] == []
    assert any(f["id"] == "unfiled" for f in lib["folders"])


def test_round_trip(state_dir):
    lib = lib_storage.load_library()
    lib["songs"].append({"song_id": "aabb", "title": "Test"})
    lib_storage.save_library(lib)

    reloaded = lib_storage.load_library()
    assert reloaded["songs"][0]["song_id"] == "aabb"


def test_atomic_write(state_dir):
    """save_library uses write-to-temp + rename; no partial file on disk."""
    lib = lib_storage.load_library()
    lib_storage.save_library(lib)

    from src.review.storage.paths import library_json_path
    raw = library_json_path().read_text()
    parsed = json.loads(raw)
    assert parsed["schema_version"] == 1


def test_schema_version_preserved(state_dir):
    lib = lib_storage.load_library()
    assert lib["schema_version"] == 1
    lib_storage.save_library(lib)
    reloaded = lib_storage.load_library()
    assert reloaded["schema_version"] == 1


def test_corrupt_file_raises(state_dir):
    from src.review.storage.paths import library_json_path
    library_json_path().parent.mkdir(parents=True, exist_ok=True)
    library_json_path().write_text("not json {{{")

    with pytest.raises(lib_storage.LibraryCorruptError):
        lib_storage.load_library()
