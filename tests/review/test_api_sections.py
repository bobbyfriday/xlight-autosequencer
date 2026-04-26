"""Tests for GET /api/v1/songs/<id>/sections — T048."""
from __future__ import annotations

import io
import struct
import time
import wave
import pytest


def _make_wav_bytes(duration_secs: float = 6.0) -> bytes:
    """6-second sine WAV that passes import-time validation (≥ 5 s, non-silent)."""
    import math

    sample_rate = 22050
    n_samples = int(duration_secs * sample_rate)
    samples = [
        int(8000 * math.sin(2 * math.pi * 440 * i / sample_rate))
        for i in range(n_samples)
    ]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


def _import_and_analyze(client) -> str:
    """Import and analyze a song; return song_id."""
    wav = _make_wav_bytes()
    song_id = client.post(
        "/api/v1/import",
        data={"audio": (io.BytesIO(wav), "test.wav")},
        content_type="multipart/form-data",
    ).get_json()["song"]["song_id"]
    client.post(f"/api/v1/songs/{song_id}/analyze")
    # Wait for background analysis to complete
    for _ in range(20):
        time.sleep(0.1)
        lib_data = client.get("/api/v1/library").get_json()
        song = next((s for s in lib_data["songs"] if s["song_id"] == song_id), None)
        if song and song.get("status") == "analyzed":
            break
    return song_id


class TestSectionsNotAnalyzed:
    def test_unknown_song_returns_404(self, client):
        resp = client.get("/api/v1/songs/deadbeef00000000/sections")
        assert resp.status_code == 404

    def test_draft_song_returns_409(self, client):
        wav = _make_wav_bytes()
        song_id = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "test.wav")},
            content_type="multipart/form-data",
        ).get_json()["song"]["song_id"]
        resp = client.get(f"/api/v1/songs/{song_id}/sections")
        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "not_analyzed"


class TestSectionsAnalyzed:
    def test_returns_200(self, client):
        song_id = _import_and_analyze(client)
        resp = client.get(f"/api/v1/songs/{song_id}/sections")
        assert resp.status_code == 200

    def test_sections_list_present(self, client):
        song_id = _import_and_analyze(client)
        data = client.get(f"/api/v1/songs/{song_id}/sections").get_json()
        assert "sections" in data
        assert isinstance(data["sections"], list)
        assert len(data["sections"]) >= 1

    def test_section_fields(self, client):
        song_id = _import_and_analyze(client)
        data = client.get(f"/api/v1/songs/{song_id}/sections").get_json()
        for sec in data["sections"]:
            assert "index" in sec
            assert "start_ms" in sec
            assert "end_ms" in sec
            assert "kind" in sec
            assert "label" in sec

    def test_ghost_boundaries_present(self, client):
        song_id = _import_and_analyze(client)
        data = client.get(f"/api/v1/songs/{song_id}/sections").get_json()
        assert "ghost_boundaries" in data
        assert isinstance(data["ghost_boundaries"], list)
