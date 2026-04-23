"""Tests for GET /audio/<song_id> — T056."""
from __future__ import annotations

import io
import struct
import wave
import pytest


def _make_wav_bytes(duration_secs: float = 0.5) -> bytes:
    sample_rate = 22050
    n_samples = int(duration_secs * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
    return buf.getvalue()


class TestAudioStream:
    def test_unknown_song_returns_404(self, client):
        resp = client.get("/audio/deadbeef00000000")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body is not None
        assert body["error"]["code"] == "source_file_missing"

    def test_streams_bytes_with_accept_ranges(self, client, tmp_path):
        wav_path = tmp_path / "test.wav"
        wav_bytes = _make_wav_bytes()
        wav_path.write_bytes(wav_bytes)

        song_id = client.post(
            "/api/v1/import",
            data={
                "audio": (io.BytesIO(wav_bytes), "test.wav"),
                "source_path": str(wav_path),
            },
            content_type="multipart/form-data",
        ).get_json()["song"]["song_id"]

        resp = client.get(f"/audio/{song_id}")
        assert resp.status_code == 200
        assert "bytes" in resp.headers.get("Accept-Ranges", "")

    def test_partial_content_206(self, client, tmp_path):
        wav_path = tmp_path / "test.wav"
        wav_bytes = _make_wav_bytes()
        wav_path.write_bytes(wav_bytes)

        song_id = client.post(
            "/api/v1/import",
            data={
                "audio": (io.BytesIO(wav_bytes), "test.wav"),
                "source_path": str(wav_path),
            },
            content_type="multipart/form-data",
        ).get_json()["song"]["song_id"]

        resp = client.get(
            f"/audio/{song_id}",
            headers={"Range": "bytes=0-99"},
        )
        assert resp.status_code == 206

    def test_no_source_path_returns_404(self, client):
        # Song exists but has no source path
        wav_bytes = _make_wav_bytes()
        song_id = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav_bytes), "test.wav")},
            content_type="multipart/form-data",
        ).get_json()["song"]["song_id"]

        resp = client.get(f"/audio/{song_id}")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "source_file_missing"

    def test_missing_file_returns_404(self, client):
        wav_bytes = _make_wav_bytes()
        song_id = client.post(
            "/api/v1/import",
            data={
                "audio": (io.BytesIO(wav_bytes), "test.wav"),
                "source_path": "/nonexistent/path/audio.wav",
            },
            content_type="multipart/form-data",
        ).get_json()["song"]["song_id"]

        resp = client.get(f"/audio/{song_id}")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "source_file_missing"
