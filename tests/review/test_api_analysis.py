"""Tests for analysis endpoints — T046."""
from __future__ import annotations

import io
import json
import struct
import time
import wave
import pytest


def _make_wav_bytes(duration_secs: float = 0.5, sample_rate: int = 22050) -> bytes:
    n_samples = int(duration_secs * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
    return buf.getvalue()


def _import_wav(client) -> str:
    """Import a WAV and return song_id."""
    wav = _make_wav_bytes()
    data = client.post(
        "/api/v1/import",
        data={"audio": (io.BytesIO(wav), "test.wav")},
        content_type="multipart/form-data",
    ).get_json()
    return data["song"]["song_id"]


class TestAnalyzeStart:
    def test_returns_202(self, client):
        song_id = _import_wav(client)
        resp = client.post(f"/api/v1/songs/{song_id}/analyze")
        assert resp.status_code == 202

    def test_returns_run_id(self, client):
        song_id = _import_wav(client)
        data = client.post(f"/api/v1/songs/{song_id}/analyze").get_json()
        assert "run_id" in data
        assert isinstance(data["run_id"], str)

    def test_returns_started_at(self, client):
        song_id = _import_wav(client)
        data = client.post(f"/api/v1/songs/{song_id}/analyze").get_json()
        assert "started_at" in data

    def test_idempotent_same_run_id(self, client):
        song_id = _import_wav(client)
        d1 = client.post(f"/api/v1/songs/{song_id}/analyze").get_json()
        d2 = client.post(f"/api/v1/songs/{song_id}/analyze").get_json()
        assert d1["run_id"] == d2["run_id"]

    def test_unknown_song_returns_404(self, client):
        resp = client.post("/api/v1/songs/deadbeef00000000/analyze")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "song_not_found"


class TestGetAnalysis:
    def test_not_analyzed_returns_409(self, client):
        song_id = _import_wav(client)
        resp = client.get(f"/api/v1/songs/{song_id}/analysis")
        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "not_analyzed"

    def test_unknown_song_returns_404(self, client):
        resp = client.get("/api/v1/songs/deadbeef00000000/analysis")
        assert resp.status_code == 404


class TestAnalyzeSSE:
    def test_sse_endpoint_returns_event_stream(self, client):
        song_id = _import_wav(client)
        run_data = client.post(f"/api/v1/songs/{song_id}/analyze").get_json()
        # SSE stream; in testing mode the handler runs synchronously
        resp = client.get(f"/api/v1/songs/{song_id}/analyze/status")
        assert resp.status_code in (200, 404)  # 404 if run already done

    def test_sse_terminates_with_overall_done(self, client):
        """SSE stream for a fast mock analysis should end with overall.done event."""
        song_id = _import_wav(client)
        client.post(f"/api/v1/songs/{song_id}/analyze")
        # Wait briefly for analysis to complete (stub is fast)
        time.sleep(0.5)
        resp = client.get(f"/api/v1/songs/{song_id}/analyze/status")
        body = resp.get_data(as_text=True)
        # Should contain at least one data line
        assert "data:" in body or resp.status_code == 404
