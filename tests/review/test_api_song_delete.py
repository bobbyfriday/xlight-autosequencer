"""T093: Failing tests for DELETE /api/v1/songs/<id> and POST /api/v1/songs/<id>/purge."""
from __future__ import annotations

import io
import struct
import wave


def _make_unique_wav(seed: int = 0) -> bytes:
    # 6 seconds so the import-time validator (5 s minimum) accepts it.
    n_samples = 6 * 44100
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        samples = [(seed * 100 + i) % 32767 for i in range(n_samples)]
        w.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


def _import_song(client, wav: bytes, filename: str = "test.wav"):
    return client.post(
        "/api/v1/import",
        data={"audio": (io.BytesIO(wav), filename)},
        content_type="multipart/form-data",
    ).get_json()


class TestDeleteSong:
    def test_delete_existing_song_returns_200(self, client):
        song_data = _import_song(client, _make_unique_wav(1))
        song_id = song_data["song"]["song_id"]
        resp = client.delete(f"/api/v1/songs/{song_id}")
        assert resp.status_code == 200

    def test_delete_returns_song_id(self, client):
        song_data = _import_song(client, _make_unique_wav(2))
        song_id = song_data["song"]["song_id"]
        data = client.delete(f"/api/v1/songs/{song_id}").get_json()
        assert data["song_id"] == song_id

    def test_delete_returns_cache_purge_available(self, client):
        """Response must include cache_purge_available boolean."""
        song_data = _import_song(client, _make_unique_wav(3))
        song_id = song_data["song"]["song_id"]
        data = client.delete(f"/api/v1/songs/{song_id}").get_json()
        assert "cache_purge_available" in data
        assert isinstance(data["cache_purge_available"], bool)

    def test_delete_returns_cache_size_bytes(self, client):
        """Response includes cache_size_bytes (may be 0 if no cache)."""
        song_data = _import_song(client, _make_unique_wav(4))
        song_id = song_data["song"]["song_id"]
        data = client.delete(f"/api/v1/songs/{song_id}").get_json()
        assert "cache_size_bytes" in data
        assert isinstance(data["cache_size_bytes"], int)

    def test_delete_song_removed_from_library(self, client):
        song_data = _import_song(client, _make_unique_wav(5))
        song_id = song_data["song"]["song_id"]
        client.delete(f"/api/v1/songs/{song_id}")
        lib = client.get("/api/v1/library").get_json()
        assert not any(s["song_id"] == song_id for s in lib["songs"])

    def test_delete_nonexistent_song_returns_404(self, client):
        resp = client.delete("/api/v1/songs/deadbeefdeadbeef")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "song_not_found"

    def test_delete_twice_returns_404(self, client):
        song_data = _import_song(client, _make_unique_wav(6))
        song_id = song_data["song"]["song_id"]
        client.delete(f"/api/v1/songs/{song_id}")
        resp = client.delete(f"/api/v1/songs/{song_id}")
        assert resp.status_code == 404

    def test_delete_removes_session_file(self, client, tmp_path):
        """Session file (session.json) should be removed after delete."""
        from src.review.storage.paths import song_session_path
        song_data = _import_song(client, _make_unique_wav(7))
        song_id = song_data["song"]["song_id"]
        # Create a fake session file
        p = song_session_path(song_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"sections": [], "assignments": []}')
        client.delete(f"/api/v1/songs/{song_id}")
        assert not p.exists()


class TestPurgeSongCache:
    def test_purge_nonexistent_song_returns_404(self, client):
        """Purging a song still in library returns 409; purging unknown returns 404."""
        resp = client.post("/api/v1/songs/deadbeefdeadbeef/purge", json={})
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "cache_not_found"

    def test_purge_song_still_in_library_returns_409(self, client):
        """Cannot purge a song that's still imported."""
        song_data = _import_song(client, _make_unique_wav(8))
        song_id = song_data["song"]["song_id"]
        resp = client.post(f"/api/v1/songs/{song_id}/purge", json={})
        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "song_still_imported"

    def test_purge_after_delete_returns_200(self, client, tmp_path):
        """After deleting a song, purge returns 200 even with no cache files."""
        song_data = _import_song(client, _make_unique_wav(9))
        song_id = song_data["song"]["song_id"]
        client.delete(f"/api/v1/songs/{song_id}")
        # No cache on disk — should still succeed (freed_bytes = 0)
        resp = client.post(f"/api/v1/songs/{song_id}/purge", json={})
        assert resp.status_code == 200

    def test_purge_returns_freed_bytes(self, client):
        song_data = _import_song(client, _make_unique_wav(10))
        song_id = song_data["song"]["song_id"]
        client.delete(f"/api/v1/songs/{song_id}")
        data = client.post(f"/api/v1/songs/{song_id}/purge", json={}).get_json()
        assert "freed_bytes" in data
        assert isinstance(data["freed_bytes"], int)

    def test_purge_twice_returns_404(self, client):
        """Purging after already purging returns 404 (nothing to purge)."""
        song_data = _import_song(client, _make_unique_wav(11))
        song_id = song_data["song"]["song_id"]
        client.delete(f"/api/v1/songs/{song_id}")
        client.post(f"/api/v1/songs/{song_id}/purge", json={})
        resp = client.post(f"/api/v1/songs/{song_id}/purge", json={})
        assert resp.status_code == 404
