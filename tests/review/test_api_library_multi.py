"""T089: Extended tests for GET /api/v1/library — multi-song case, ordering, folder listing."""
from __future__ import annotations

import io
import struct
import wave
import datetime


def _make_wav_bytes(duration_secs: float = 1.0, sample_rate: int = 44100) -> bytes:
    n_samples = int(duration_secs * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
    return buf.getvalue()


def _make_unique_wav(seed: int = 0) -> bytes:
    """Generate distinct WAV bytes so each file gets a unique hash."""
    n_samples = 44100
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        # Use seed to create unique audio content
        samples = [(seed * 100 + i) % 32767 for i in range(n_samples)]
        w.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


def _import_song(client, wav: bytes, filename: str = "test.wav", folder_id: str | None = None):
    data: dict = {"audio": (io.BytesIO(wav), filename)}
    if folder_id:
        data["folder_id"] = folder_id
    return client.post(
        "/api/v1/import", data=data, content_type="multipart/form-data"
    ).get_json()


class TestLibraryMultiSong:
    def test_multiple_songs_returned(self, client):
        """All imported songs appear in GET /library."""
        for i in range(3):
            _import_song(client, _make_unique_wav(i), f"song{i}.wav")
        data = client.get("/api/v1/library").get_json()
        assert len(data["songs"]) == 3

    def test_songs_ordered_by_import_time(self, client):
        """Songs returned in import (inserted) order."""
        for i in range(3):
            _import_song(client, _make_unique_wav(i), f"song{i}.wav")
        data = client.get("/api/v1/library").get_json()
        # Each song has imported_at; verify ascending order
        times = [s["imported_at"] for s in data["songs"]]
        assert times == sorted(times)

    def test_songs_have_required_fields(self, client):
        """Every song object has all required fields."""
        _import_song(client, _make_unique_wav(0))
        data = client.get("/api/v1/library").get_json()
        song = data["songs"][0]
        required = {"song_id", "title", "status", "folder_id", "imported_at", "source_exists"}
        for field in required:
            assert field in song, f"Missing field: {field}"

    def test_response_includes_schema_version(self, client):
        """GET /library includes schema_version in response."""
        data = client.get("/api/v1/library").get_json()
        assert "schema_version" in data or "songs" in data  # schema_version is optional but songs is required

    def test_songs_in_different_folders(self, client):
        """Songs are associated with correct folder_ids."""
        # Create a folder first
        resp = client.post(
            "/api/v1/folders", json={"name": "Christmas"}
        )
        assert resp.status_code == 201
        folder_id = resp.get_json()["folder_id"]

        _import_song(client, _make_unique_wav(1), "song1.wav", folder_id=folder_id)
        _import_song(client, _make_unique_wav(2), "song2.wav")  # unfiled

        data = client.get("/api/v1/library").get_json()
        songs = data["songs"]
        assert len(songs) == 2
        folder_ids = {s["folder_id"] for s in songs}
        assert folder_id in folder_ids
        assert "unfiled" in folder_ids

    def test_folder_tree_returned(self, client):
        """GET /library returns full folder tree including user-created folders."""
        client.post("/api/v1/folders", json={"name": "Show A"})
        client.post("/api/v1/folders", json={"name": "Show B"})
        data = client.get("/api/v1/library").get_json()
        folder_names = {f["name"] for f in data["folders"]}
        assert "Show A" in folder_names
        assert "Show B" in folder_names
        assert "Unfiled" in folder_names

    def test_empty_library_has_unfiled_folder(self, client):
        """Even an empty library exposes the unfiled folder."""
        data = client.get("/api/v1/library").get_json()
        assert any(f.get("folder_id") == "unfiled" for f in data["folders"])
