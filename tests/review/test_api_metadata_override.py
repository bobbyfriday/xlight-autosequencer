"""Tests for PATCH /api/v1/songs/<id>/metadata and the ``override_artist`` /
``override_title`` plumbing into the Genius step.

Covers Tier 2 of the analyze-screen metadata-override feature — the UI lets
the user correct ID3-derived artist/title mid-analysis, and the pipeline's
next Genius lookup honours the override.
"""
from __future__ import annotations

import io
import struct
import wave


def _make_unique_wav(seed: int = 0) -> bytes:
    n_samples = 44100
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        samples = [(seed * 100 + i) % 32767 for i in range(n_samples)]
        w.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


def _import(client, seed: int = 0):
    wav = _make_unique_wav(seed)
    resp = client.post(
        "/api/v1/import",
        data={"audio": (io.BytesIO(wav), f"test-{seed}.wav")},
        content_type="multipart/form-data",
    )
    return resp.get_json()["song"]


class TestPatchMetadata:
    def test_404_when_song_missing(self, client):
        resp = client.patch("/api/v1/songs/doesnotexist/metadata",
                            json={"artist": "X"})
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "song_not_found"

    def test_sets_override_artist(self, client):
        song = _import(client, seed=1)
        resp = client.patch(
            f"/api/v1/songs/{song['song_id']}/metadata",
            json={"artist": "Mariah Carey"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["override_artist"] == "Mariah Carey"

    def test_sets_override_title(self, client):
        song = _import(client, seed=2)
        resp = client.patch(
            f"/api/v1/songs/{song['song_id']}/metadata",
            json={"title": "All I Want for Christmas Is You"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["override_title"] == "All I Want for Christmas Is You"

    def test_clears_override_on_empty_string(self, client):
        song = _import(client, seed=3)
        sid = song["song_id"]
        client.patch(f"/api/v1/songs/{sid}/metadata", json={"artist": "Wrong Artist"})
        resp = client.patch(f"/api/v1/songs/{sid}/metadata", json={"artist": ""})
        assert resp.status_code == 200
        assert "override_artist" not in resp.get_json() or resp.get_json().get("override_artist") is None

    def test_partial_update_preserves_other_override(self, client):
        song = _import(client, seed=4)
        sid = song["song_id"]
        client.patch(f"/api/v1/songs/{sid}/metadata",
                     json={"artist": "A", "title": "T"})
        resp = client.patch(f"/api/v1/songs/{sid}/metadata", json={"artist": "B"})
        j = resp.get_json()
        assert j["override_artist"] == "B"
        assert j["override_title"] == "T"

    def test_override_appears_in_library_listing(self, client):
        song = _import(client, seed=5)
        sid = song["song_id"]
        client.patch(f"/api/v1/songs/{sid}/metadata",
                     json={"artist": "Override Artist"})
        listing = client.get("/api/v1/library").get_json()
        match = next(s for s in listing["songs"] if s["song_id"] == sid)
        assert match["override_artist"] == "Override Artist"


class TestGeniusQualityCheck:
    """Unit-test the renamed _genius_quality_check helper."""

    def test_accept_well_formed_sections(self):
        from src.story.builder import _genius_quality_check
        sections = [
            (0, 10_000, "intro"),
            (10_000, 45_000, "verse"),
            (45_000, 75_000, "chorus"),
            (75_000, 120_000, "bridge"),
            (120_000, 180_000, "outro"),
        ]
        ok, reason = _genius_quality_check(sections, duration_ms=180_000)
        assert ok is True
        assert reason is None

    def test_reject_huge_section(self):
        from src.story.builder import _genius_quality_check
        # one section covers 75% of a 4-minute song — likely a wrong match
        sections = [
            (0, 20_000, "intro"),
            (20_000, 200_000, "verse"),
            (200_000, 240_000, "outro"),
        ]
        ok, reason = _genius_quality_check(sections, duration_ms=240_000)
        assert ok is False
        assert "75%" in (reason or "") and "wrong-song" in (reason or "")

    def test_reject_too_few_sections(self):
        from src.story.builder import _genius_quality_check
        sections = [(0, 120_000, "intro"), (120_000, 240_000, "outro")]
        ok, reason = _genius_quality_check(sections, duration_ms=240_000)
        # Two sections may pass the count check but one covers 50% (50% < 60%)
        # so reject here must be about one-role or count. Use 1 section to
        # force the count rule unambiguously:
        one_sec = [(0, 120_000, "verse")]
        ok1, reason1 = _genius_quality_check(one_sec, duration_ms=240_000)
        assert ok1 is False
        assert reason1 and ("1 section" in reason1 or "wrong-song" in reason1)

    def test_reject_single_role(self):
        from src.story.builder import _genius_quality_check
        sections = [
            (0, 10_000, "verse"),
            (10_000, 40_000, "verse"),
            (40_000, 80_000, "verse"),
            (80_000, 120_000, "verse"),
        ]
        ok, reason = _genius_quality_check(sections, duration_ms=120_000)
        assert ok is False
        assert "one distinct" in (reason or "")

    def test_empty_sections_rejected(self):
        from src.story.builder import _genius_quality_check
        ok, reason = _genius_quality_check([], duration_ms=180_000)
        assert ok is False
        assert reason
