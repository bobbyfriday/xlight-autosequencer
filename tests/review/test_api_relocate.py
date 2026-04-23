"""T132: Failing tests for POST /api/v1/songs/<id>/relocate.

User provides a new absolute path; backend verifies the file hashes to the
song's song_id, appends the path to source_paths, returns updated Song.
"""
import hashlib
import json
import os
import tempfile

import pytest

from src.review.storage.library import save_library


def _sha256_prefix(data: bytes, n: int = 16) -> str:
    return hashlib.sha256(data).hexdigest()[:n]


def _seed_song(tmp_path, song_id: str, title: str = "Test", source_paths=None):
    lib = {
        "schema_version": 1,
        "songs": [
            {
                "song_id": song_id,
                "title": title,
                "status": "draft",
                "source_paths": source_paths or [],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ],
        "folders": [{"id": "unfiled", "name": "Unfiled", "created_at": "2026-04-21T00:00:00Z"}],
        "preferences": {},
        "layout": None,
    }
    save_library(lib)


class TestRelocate:
    def test_relocate_unknown_song_returns_404(self, client, tmp_path, monkeypatch):
        """Relocating a song_id not in the library returns 404."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        _seed_song(tmp_path, "aabbccddeeff0011")
        resp = client.post(
            "/api/v1/songs/doesnotexist0001/relocate",
            json={"path": "/some/file.mp3"},
        )
        assert resp.status_code == 404

    def test_relocate_missing_path_field_returns_400(self, client, tmp_path, monkeypatch):
        """Request body without 'path' field returns 400."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        song_id = "aabbccddeeff0011"
        _seed_song(tmp_path, song_id)
        resp = client.post(f"/api/v1/songs/{song_id}/relocate", json={})
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "missing_path"

    def test_relocate_nonexistent_file_returns_404(self, client, tmp_path, monkeypatch):
        """Providing a path that doesn't exist on disk returns 404."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        song_id = "aabbccddeeff0011"
        _seed_song(tmp_path, song_id)
        resp = client.post(
            f"/api/v1/songs/{song_id}/relocate",
            json={"path": "/absolutely/nonexistent/file.mp3"},
        )
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["error"]["code"] == "file_not_found"

    def test_relocate_hash_mismatch_returns_409(self, client, tmp_path, monkeypatch):
        """File exists but hashes to wrong song_id → 409 conflict."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        # Write a file whose hash won't match our song_id
        audio_file = tmp_path / "wrong_song.mp3"
        wrong_content = b"\xff\xfb" + b"\x01" * 200
        audio_file.write_bytes(wrong_content)
        # song_id is 16 hex chars of sha256 of different content
        song_id = _sha256_prefix(b"\xff\xfb" + b"\x02" * 200)
        _seed_song(tmp_path, song_id)

        resp = client.post(
            f"/api/v1/songs/{song_id}/relocate",
            json={"path": str(audio_file)},
        )
        assert resp.status_code == 409
        body = resp.get_json()
        assert body["error"]["code"] == "hash_mismatch"

    def test_relocate_success_appends_path(self, client, tmp_path, monkeypatch):
        """Correct hash → path appended to source_paths, status no longer source_missing."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        audio_content = b"\xff\xfb" + b"\xaa" * 300
        song_id = _sha256_prefix(audio_content)

        audio_file = tmp_path / "mysong.mp3"
        audio_file.write_bytes(audio_content)

        # Seed the song with source_missing status and no paths
        lib = {
            "schema_version": 1,
            "songs": [
                {
                    "song_id": song_id,
                    "title": "My Song",
                    "status": "source_missing",
                    "source_paths": [],
                    "folder_id": "unfiled",
                    "imported_at": "2026-04-21T00:00:00Z",
                }
            ],
            "folders": [
                {"id": "unfiled", "name": "Unfiled", "created_at": "2026-04-21T00:00:00Z"}
            ],
            "preferences": {},
            "layout": None,
        }
        save_library(lib)

        resp = client.post(
            f"/api/v1/songs/{song_id}/relocate",
            json={"path": str(audio_file)},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert str(audio_file) in body["source_paths"]
        assert body["status"] != "source_missing"

    def test_relocate_does_not_duplicate_path(self, client, tmp_path, monkeypatch):
        """If the path is already in source_paths, it's not added again."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        audio_content = b"\xff\xfb" + b"\xbb" * 300
        song_id = _sha256_prefix(audio_content)

        audio_file = tmp_path / "dupe.mp3"
        audio_file.write_bytes(audio_content)

        lib = {
            "schema_version": 1,
            "songs": [
                {
                    "song_id": song_id,
                    "title": "Dupe",
                    "status": "draft",
                    "source_paths": [str(audio_file)],  # already present
                    "folder_id": "unfiled",
                    "imported_at": "2026-04-21T00:00:00Z",
                }
            ],
            "folders": [
                {"id": "unfiled", "name": "Unfiled", "created_at": "2026-04-21T00:00:00Z"}
            ],
            "preferences": {},
            "layout": None,
        }
        save_library(lib)

        resp = client.post(
            f"/api/v1/songs/{song_id}/relocate",
            json={"path": str(audio_file)},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["source_paths"].count(str(audio_file)) == 1
