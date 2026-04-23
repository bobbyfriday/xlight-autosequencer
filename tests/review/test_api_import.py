"""Tests for POST /api/v1/import — T042."""
from __future__ import annotations

import io
import os
import wave
import struct
import pytest


def _make_wav_bytes(duration_secs: float = 1.0, sample_rate: int = 44100) -> bytes:
    """Generate minimal valid WAV bytes."""
    n_samples = int(duration_secs * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
    return buf.getvalue()


def _wav_upload(data: bytes, filename: str = "test.wav", source_path: str | None = None):
    fields: dict = {"audio": (filename, io.BytesIO(data), "audio/wav")}
    if source_path:
        fields["source_path"] = source_path
    return fields


class TestImportNewSong:
    def test_returns_201_on_new_song(self, client):
        wav = _make_wav_bytes()
        resp = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "test.wav")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201

    def test_created_flag_true(self, client):
        wav = _make_wav_bytes()
        data = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "test.wav")},
            content_type="multipart/form-data",
        ).get_json()
        assert data["created"] is True

    def test_song_fields_present(self, client):
        wav = _make_wav_bytes()
        data = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "test.wav")},
            content_type="multipart/form-data",
        ).get_json()
        song = data["song"]
        assert "song_id" in song
        assert "title" in song
        assert "duration_ms" in song
        assert song["status"] == "draft"
        assert song["folder_id"] == "unfiled"
        assert "imported_at" in song
        assert isinstance(song["source_paths"], list)

    def test_song_id_is_16_hex_chars(self, client):
        wav = _make_wav_bytes()
        data = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "test.wav")},
            content_type="multipart/form-data",
        ).get_json()
        song_id = data["song"]["song_id"]
        assert len(song_id) == 16
        assert all(c in "0123456789abcdef" for c in song_id)

    def test_duration_ms_positive(self, client):
        wav = _make_wav_bytes(duration_secs=2.0)
        data = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "test.wav")},
            content_type="multipart/form-data",
        ).get_json()
        assert data["song"]["duration_ms"] > 0

    def test_source_path_stored(self, client):
        wav = _make_wav_bytes()
        data = client.post(
            "/api/v1/import",
            data={
                "audio": (io.BytesIO(wav), "test.wav"),
                "source_path": "/tmp/test.wav",
            },
            content_type="multipart/form-data",
        ).get_json()
        assert "/tmp/test.wav" in data["song"]["source_paths"]


class TestImportDedup:
    def test_returns_200_on_dedup(self, client):
        wav = _make_wav_bytes()
        client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "first.wav")},
            content_type="multipart/form-data",
        )
        resp = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "first_again.wav")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200

    def test_created_false_on_dedup(self, client):
        wav = _make_wav_bytes()
        client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "first.wav")},
            content_type="multipart/form-data",
        )
        data = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "first_again.wav")},
            content_type="multipart/form-data",
        ).get_json()
        assert data["created"] is False

    def test_same_song_id_on_dedup(self, client):
        wav = _make_wav_bytes()
        d1 = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "first.wav")},
            content_type="multipart/form-data",
        ).get_json()
        d2 = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "second.wav")},
            content_type="multipart/form-data",
        ).get_json()
        assert d1["song"]["song_id"] == d2["song"]["song_id"]

    def test_new_source_path_added_on_dedup(self, client):
        wav = _make_wav_bytes()
        client.post(
            "/api/v1/import",
            data={
                "audio": (io.BytesIO(wav), "first.wav"),
                "source_path": "/music/first.wav",
            },
            content_type="multipart/form-data",
        )
        data = client.post(
            "/api/v1/import",
            data={
                "audio": (io.BytesIO(wav), "second.wav"),
                "source_path": "/music/second.wav",
            },
            content_type="multipart/form-data",
        ).get_json()
        assert data.get("source_path_added") is True
        assert "/music/second.wav" in data["song"]["source_paths"]


class TestImportErrors:
    def test_missing_file_returns_400(self, client):
        resp = client.post(
            "/api/v1/import",
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert client.post(
            "/api/v1/import",
            data={},
            content_type="multipart/form-data",
        ).get_json()["error"]["code"] == "missing_file"

    def test_unsupported_format_returns_400(self, client):
        resp = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(b"fake"), "song.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "unsupported_format"
