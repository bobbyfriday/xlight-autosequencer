"""T127: Failing tests for library export/import endpoints (FR-049c).

POST /api/v1/library/export  — produces valid zip bundle
POST /api/v1/library/import  — merge + replace modes
"""
import io
import json
import zipfile

import pytest

from src.review.storage.library import save_library


def _seed_library(tmp_path, songs=None, folders=None):
    """Write a library.json with given songs/folders to the state dir."""
    lib = {
        "schema_version": 1,
        "songs": songs or [],
        "folders": folders
        or [{"id": "unfiled", "name": "Unfiled", "created_at": "2026-04-21T00:00:00Z"}],
        "preferences": {},
        "layout": None,
    }
    save_library(lib)
    return lib


# ─── Export ────────────────────────────────────────────────────────────────────


class TestLibraryExport:
    def test_export_returns_zip(self, client, tmp_path, monkeypatch):
        """POST /api/v1/library/export returns 200 with application/zip content type."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        _seed_library(tmp_path)
        resp = client.post("/api/v1/library/export")
        assert resp.status_code == 200
        assert resp.content_type in (
            "application/zip",
            "application/octet-stream",
        )

    def test_export_zip_contains_library_json(self, client, tmp_path, monkeypatch):
        """The produced zip contains library.json at its root."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        _seed_library(tmp_path)
        resp = client.post("/api/v1/library/export")
        assert resp.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(resp.data))
        assert "library.json" in zf.namelist()

    def test_export_zip_contains_per_song_sessions(self, client, tmp_path, monkeypatch):
        """Each song with a session.json has it included under songs/<id>/session.json."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        song_id = "aabbccddeeff0011"
        songs = [
            {
                "song_id": song_id,
                "title": "Test",
                "status": "draft",
                "source_paths": [],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ]
        _seed_library(tmp_path, songs=songs)
        # Write a session.json for the song
        from src.review.storage.paths import song_session_path

        sess_path = song_session_path(song_id)
        sess_path.parent.mkdir(parents=True, exist_ok=True)
        sess_path.write_text(json.dumps({"sections": [], "assignments": []}))

        resp = client.post("/api/v1/library/export")
        assert resp.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(resp.data))
        assert f"songs/{song_id}/session.json" in zf.namelist()

    def test_export_excludes_audio_files(self, client, tmp_path, monkeypatch):
        """Audio files (source_paths) are NOT included in the bundle."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        audio = tmp_path / "song.mp3"
        audio.write_bytes(b"\xff\xfb" + b"\x00" * 100)
        songs = [
            {
                "song_id": "deadbeef00000001",
                "title": "Audio Song",
                "status": "draft",
                "source_paths": [str(audio)],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ]
        _seed_library(tmp_path, songs=songs)
        resp = client.post("/api/v1/library/export")
        assert resp.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(resp.data))
        for name in zf.namelist():
            assert not name.endswith(".mp3"), f"Audio file found in bundle: {name}"
            assert not name.endswith(".wav"), f"Audio file found in bundle: {name}"


# ─── Import ────────────────────────────────────────────────────────────────────


def _make_bundle(songs=None, sessions=None) -> bytes:
    """Create a minimal valid .xonset-bundle zip for testing."""
    from src.review.storage.bundle import pack

    lib = {
        "schema_version": 1,
        "songs": songs or [],
        "folders": [{"id": "unfiled", "name": "Unfiled", "created_at": "2026-04-21T00:00:00Z"}],
        "preferences": {},
        "layout": None,
    }
    return pack(lib, sessions or {})


class TestLibraryImport:
    def test_import_missing_body_returns_400(self, client, tmp_path, monkeypatch):
        """POST /api/v1/library/import with no file returns 400."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        resp = client.post("/api/v1/library/import")
        assert resp.status_code == 400

    def test_import_invalid_zip_returns_400(self, client, tmp_path, monkeypatch):
        """Sending garbage bytes returns 400 with error code bundle_invalid."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        resp = client.post(
            "/api/v1/library/import",
            data={"bundle": (io.BytesIO(b"not a zip"), "bundle.xonset")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "bundle_invalid"

    def test_import_replace_mode_replaces_library(self, client, tmp_path, monkeypatch):
        """Replace mode: existing songs are discarded; bundle songs become the library."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        existing_songs = [
            {
                "song_id": "existing00000001",
                "title": "Existing",
                "status": "draft",
                "source_paths": [],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ]
        _seed_library(tmp_path, songs=existing_songs)

        bundle_songs = [
            {
                "song_id": "bundled000000001",
                "title": "Bundled",
                "status": "draft",
                "source_paths": ["/nonexistent/song.mp3"],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ]
        bundle = _make_bundle(songs=bundle_songs)

        resp = client.post(
            "/api/v1/library/import",
            data={
                "bundle": (io.BytesIO(bundle), "bundle.xonset"),
                "mode": "replace",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        song_ids = [s["song_id"] for s in body["songs"]]
        assert "bundled000000001" in song_ids
        assert "existing00000001" not in song_ids

    def test_import_merge_mode_combines_songs(self, client, tmp_path, monkeypatch):
        """Merge mode: bundle songs are added; existing songs are kept."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        existing_songs = [
            {
                "song_id": "existing00000001",
                "title": "Existing",
                "status": "draft",
                "source_paths": [],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ]
        _seed_library(tmp_path, songs=existing_songs)

        bundle_songs = [
            {
                "song_id": "bundled000000001",
                "title": "Bundled",
                "status": "draft",
                "source_paths": ["/nonexistent/song.mp3"],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ]
        bundle = _make_bundle(songs=bundle_songs)

        resp = client.post(
            "/api/v1/library/import",
            data={
                "bundle": (io.BytesIO(bundle), "bundle.xonset"),
                "mode": "merge",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        song_ids = [s["song_id"] for s in body["songs"]]
        assert "bundled000000001" in song_ids
        assert "existing00000001" in song_ids

    def test_import_source_missing_songs_populated(self, client, tmp_path, monkeypatch):
        """source_missing_songs in response lists songs whose audio path doesn't exist."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        _seed_library(tmp_path)

        bundle_songs = [
            {
                "song_id": "missing000000001",
                "title": "Missing Audio",
                "status": "draft",
                "source_paths": ["/absolutely/nonexistent/song.mp3"],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            },
            {
                "song_id": "present00000001",
                "title": "Present Audio",
                "status": "draft",
                "source_paths": [],  # no path at all — also missing
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            },
        ]
        bundle = _make_bundle(songs=bundle_songs)

        resp = client.post(
            "/api/v1/library/import",
            data={
                "bundle": (io.BytesIO(bundle), "bundle.xonset"),
                "mode": "replace",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "source_missing_songs" in body
        missing_ids = body["source_missing_songs"]
        assert "missing000000001" in missing_ids
        assert "present00000001" in missing_ids
