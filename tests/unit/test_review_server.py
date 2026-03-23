"""Tests for the Flask review server endpoints."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.review.server import create_app


FIXTURE_ANALYSIS = {
    "schema_version": "1.0",
    "source_file": "/fake/song.mp3",
    "filename": "song.mp3",
    "duration_ms": 10000,
    "sample_rate": 44100,
    "estimated_tempo_bpm": 120.0,
    "run_timestamp": "2026-03-22T10:00:00",
    "algorithms": [
        {"name": "qm_beats", "element_type": "beat", "library": "vamp", "plugin_key": None, "parameters": {}},
        {"name": "librosa_drums", "element_type": "onset", "library": "librosa", "plugin_key": None, "parameters": {}},
        {"name": "librosa_bass", "element_type": "onset", "library": "librosa", "plugin_key": None, "parameters": {}},
    ],
    "timing_tracks": [
        {"name": "qm_beats", "algorithm_name": "qm_beats", "element_type": "beat",
         "quality_score": 0.85, "mark_count": 10, "avg_interval_ms": 500,
         "marks": [{"time_ms": i * 500, "confidence": None} for i in range(10)]},
        {"name": "librosa_drums", "algorithm_name": "librosa_drums", "element_type": "onset",
         "quality_score": 0.72, "mark_count": 8, "avg_interval_ms": 625,
         "marks": [{"time_ms": i * 625, "confidence": None} for i in range(8)]},
        {"name": "librosa_bass", "algorithm_name": "librosa_bass", "element_type": "onset",
         "quality_score": 0.60, "mark_count": 6, "avg_interval_ms": 833,
         "marks": [{"time_ms": i * 833, "confidence": None} for i in range(6)]},
    ],
}


@pytest.fixture()
def analysis_file(tmp_path):
    """Write fixture analysis JSON and return its path."""
    p = tmp_path / "song_analysis.json"
    p.write_text(json.dumps(FIXTURE_ANALYSIS), encoding="utf-8")
    return str(p)


@pytest.fixture()
def audio_file(tmp_path):
    """Create a tiny fake MP3 file (not real audio — just for endpoint testing)."""
    p = tmp_path / "song.mp3"
    p.write_bytes(b"\xff\xfb\x90\x00" * 100)  # minimal fake MP3 bytes
    return str(p)


@pytest.fixture()
def client(analysis_file, audio_file):
    app = create_app(analysis_file, audio_file)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── GET /analysis ─────────────────────────────────────────────────────────────

def test_analysis_returns_200(client):
    resp = client.get("/analysis")
    assert resp.status_code == 200


def test_analysis_content_type_json(client):
    resp = client.get("/analysis")
    assert "application/json" in resp.content_type


def test_analysis_tracks_length(client):
    resp = client.get("/analysis")
    data = resp.get_json()
    assert len(data["timing_tracks"]) == 3


def test_analysis_duration_ms(client):
    resp = client.get("/analysis")
    data = resp.get_json()
    assert data["duration_ms"] == 10000


# ── GET /audio ────────────────────────────────────────────────────────────────

def test_audio_returns_200(client):
    resp = client.get("/audio")
    assert resp.status_code == 200


def test_audio_content_type(client):
    resp = client.get("/audio")
    assert "audio/mpeg" in resp.content_type


def test_audio_accept_ranges_header(client):
    resp = client.get("/audio")
    assert resp.headers.get("Accept-Ranges") == "bytes"


# ── POST /export ──────────────────────────────────────────────────────────────

def test_export_success(client, tmp_path, analysis_file):
    """Export 2 of 3 tracks — output file contains exactly 2 tracks."""
    resp = client.post(
        "/export",
        json={"selected_track_names": ["qm_beats", "librosa_drums"]},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "path" in data
    out_path = Path(data["path"])
    assert out_path.exists()
    with open(out_path) as fh:
        exported = json.load(fh)
    assert len(exported["timing_tracks"]) == 2
    names = {t["name"] for t in exported["timing_tracks"]}
    assert names == {"qm_beats", "librosa_drums"}


def test_export_no_tracks_returns_400(client):
    resp = client.post("/export", json={"selected_track_names": []})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_export_empty_body_returns_400(client):
    resp = client.post("/export", json={})
    assert resp.status_code == 400


def test_export_overwrite_returns_409_then_200(client, analysis_file):
    """First export succeeds; second returns 409; third with overwrite=true succeeds."""
    payload = {"selected_track_names": ["qm_beats"]}

    r1 = client.post("/export", json=payload)
    assert r1.status_code == 200

    r2 = client.post("/export", json=payload)
    assert r2.status_code == 409
    assert "warning" in r2.get_json()

    payload["overwrite"] = True
    r3 = client.post("/export", json=payload)
    assert r3.status_code == 200


def test_export_preserves_all_mark_data(client):
    """Exported tracks contain all timing marks intact."""
    resp = client.post(
        "/export",
        json={"selected_track_names": ["qm_beats"]},
        headers={"X-Overwrite": "true"},
    )
    # First export (or retry with overwrite)
    if resp.status_code == 409:
        resp = client.post(
            "/export",
            json={"selected_track_names": ["qm_beats"], "overwrite": True},
        )
    assert resp.status_code == 200
    out_path = Path(resp.get_json()["path"])
    with open(out_path) as fh:
        exported = json.load(fh)
    track = exported["timing_tracks"][0]
    assert track["mark_count"] == 10
    assert len(track["marks"]) == 10
