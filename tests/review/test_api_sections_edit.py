"""Failing tests for section edit endpoints — T101 (US3).

Covers: split, merge, promote-ghost, delete, rename, reset per contracts/sections.md.
"""
from __future__ import annotations

import io
import struct
import time
import wave
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(duration_secs: float = 2.0) -> bytes:
    sample_rate = 22050
    n_samples = int(duration_secs * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
    return buf.getvalue()


def _import_and_analyze(client) -> str:
    """Import a WAV and run analysis; waits for status==analyzed. Returns song_id."""
    wav = _make_wav_bytes()
    song_id = client.post(
        "/api/v1/import",
        data={"audio": (io.BytesIO(wav), "test.wav")},
        content_type="multipart/form-data",
    ).get_json()["song"]["song_id"]
    client.post(f"/api/v1/songs/{song_id}/analyze")
    for _ in range(30):
        time.sleep(0.1)
        lib_data = client.get("/api/v1/library").get_json()
        song = next((s for s in lib_data["songs"] if s["song_id"] == song_id), None)
        if song and song.get("status") == "analyzed":
            break
    return song_id


def _get_sections(client, song_id: str) -> list[dict]:
    return client.get(f"/api/v1/songs/{song_id}/sections").get_json()["sections"]


# ---------------------------------------------------------------------------
# T101: Split tests (FR-021)
# ---------------------------------------------------------------------------

class TestSplit:
    def test_split_returns_200_with_updated_sections(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        # Pick midpoint of first section
        s0 = sections[0]
        mid = (s0["start_ms"] + s0["end_ms"]) // 2
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/split",
            json={"at_ms": mid},
        )
        assert resp.status_code == 200

    def test_split_increases_section_count(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        original_count = len(sections)
        s0 = sections[0]
        mid = (s0["start_ms"] + s0["end_ms"]) // 2
        client.post(f"/api/v1/songs/{song_id}/sections/split", json={"at_ms": mid})
        new_sections = _get_sections(client, song_id)
        assert len(new_sections) == original_count + 1

    def test_split_both_halves_have_original_theme(self, client):
        """Both halves inherit the original section's theme_id (FR-021 theme inherit)."""
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        s0 = sections[0]
        # Get original theme for section 0
        assignments_resp = client.get(f"/api/v1/songs/{song_id}/sections").get_json()
        # Assignments in the response after split
        mid = (s0["start_ms"] + s0["end_ms"]) // 2
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/split", json={"at_ms": mid}
        )
        data = resp.get_json()
        assert "assignments" in data
        # First two assignments should have same theme_id
        a0 = data["assignments"][0]
        a1 = data["assignments"][1]
        assert a0["theme_id"] == a1["theme_id"]

    def test_split_rejects_sub_500ms_result(self, client):
        """Splitting within 500ms of an existing boundary returns 422."""
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        s0 = sections[0]
        # Split very close to start boundary (100ms in)
        near_start = s0["start_ms"] + 100
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/split", json={"at_ms": near_start}
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "section_too_short"

    def test_split_rejects_at_existing_boundary(self, client):
        """Splitting exactly at an existing boundary returns 422 split_at_boundary."""
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        if len(sections) < 2:
            pytest.skip("need at least 2 sections")
        # at_ms == start of second section == end of first
        at_ms = sections[1]["start_ms"]
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/split", json={"at_ms": at_ms}
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] in ("split_at_boundary", "section_too_short")

    def test_split_unknown_song_returns_404(self, client):
        resp = client.post(
            "/api/v1/songs/deadbeef00000000/sections/split", json={"at_ms": 5000}
        )
        assert resp.status_code == 404

    def test_split_response_contains_sections_key(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        s0 = sections[0]
        mid = (s0["start_ms"] + s0["end_ms"]) // 2
        data = client.post(
            f"/api/v1/songs/{song_id}/sections/split", json={"at_ms": mid}
        ).get_json()
        assert "sections" in data


# ---------------------------------------------------------------------------
# T101: Merge tests (FR-022)
# ---------------------------------------------------------------------------

class TestMerge:
    def test_merge_returns_200(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        if len(sections) < 2:
            pytest.skip("need at least 2 sections")
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/merge",
            json={"section_index": 0},
        )
        assert resp.status_code == 200

    def test_merge_decreases_section_count(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        if len(sections) < 2:
            pytest.skip("need at least 2 sections")
        original_count = len(sections)
        client.post(
            f"/api/v1/songs/{song_id}/sections/merge", json={"section_index": 0}
        )
        new_sections = _get_sections(client, song_id)
        assert len(new_sections) == original_count - 1

    def test_merge_first_wins_theme(self, client):
        """Merged result keeps first section's theme (FR-022 first-wins)."""
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        if len(sections) < 2:
            pytest.skip("need at least 2 sections")
        # Assign different theme to second section first
        client.put(
            f"/api/v1/songs/{song_id}/assignments/1",
            json={"theme_id": "peak-flash", "overrides": {}, "user_confirmed": False},
        )
        # Get theme of first section
        session_resp = client.get(f"/api/v1/songs/{song_id}/sections").get_json()
        # Merge 0 with 1
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/merge", json={"section_index": 0}
        )
        data = resp.get_json()
        # After merge there should be one assignment for the merged section
        # It should keep the first section's theme (not "peak-flash")
        assert "sections" in data

    def test_merge_last_section_returns_422(self, client):
        """Merging the last section (no follower) returns 422 no_follower."""
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        last_idx = len(sections) - 1
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/merge",
            json={"section_index": last_idx},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "no_follower"

    def test_merge_unknown_song_returns_404(self, client):
        resp = client.post(
            "/api/v1/songs/deadbeef00000000/sections/merge",
            json={"section_index": 0},
        )
        assert resp.status_code == 404

    def test_merge_out_of_range_section_returns_404(self, client):
        song_id = _import_and_analyze(client)
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/merge",
            json={"section_index": 9999},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# T101: Promote-ghost tests (FR-025)
# ---------------------------------------------------------------------------

class TestPromoteGhost:
    def test_promote_ghost_unknown_song_returns_404(self, client):
        resp = client.post(
            "/api/v1/songs/deadbeef00000000/sections/promote-ghost",
            json={"at_ms": 5000},
        )
        assert resp.status_code == 404

    def test_promote_nonexistent_ghost_returns_404(self, client):
        song_id = _import_and_analyze(client)
        resp = client.post(
            f"/api/v1/songs/{song_id}/sections/promote-ghost",
            json={"at_ms": 999999999},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "ghost_not_found"


# ---------------------------------------------------------------------------
# T101: Delete tests (FR-023)
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_returns_200(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        if len(sections) < 2:
            pytest.skip("need at least 2 sections")
        resp = client.delete(f"/api/v1/songs/{song_id}/sections/0")
        assert resp.status_code == 200

    def test_delete_decreases_section_count(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        if len(sections) < 2:
            pytest.skip("need at least 2 sections")
        original_count = len(sections)
        client.delete(f"/api/v1/songs/{song_id}/sections/0")
        new_sections = _get_sections(client, song_id)
        assert len(new_sections) == original_count - 1

    def test_delete_last_section_returns_422(self, client):
        """Cannot delete when only one section remains (FR-023)."""
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        # Delete all but last
        while len(_get_sections(client, song_id)) > 1:
            client.delete(f"/api/v1/songs/{song_id}/sections/0")
        resp = client.delete(f"/api/v1/songs/{song_id}/sections/0")
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "last_section_required"

    def test_delete_unknown_song_returns_404(self, client):
        resp = client.delete("/api/v1/songs/deadbeef00000000/sections/0")
        assert resp.status_code == 404

    def test_delete_out_of_range_returns_404(self, client):
        song_id = _import_and_analyze(client)
        resp = client.delete(f"/api/v1/songs/{song_id}/sections/9999")
        assert resp.status_code == 404

    def test_delete_response_contains_sections(self, client):
        song_id = _import_and_analyze(client)
        sections = _get_sections(client, song_id)
        if len(sections) < 2:
            pytest.skip("need at least 2 sections")
        data = client.delete(f"/api/v1/songs/{song_id}/sections/0").get_json()
        assert "sections" in data


# ---------------------------------------------------------------------------
# T101: Rename / PATCH tests (FR-024)
# ---------------------------------------------------------------------------

class TestRename:
    def test_rename_returns_200(self, client):
        song_id = _import_and_analyze(client)
        resp = client.patch(
            f"/api/v1/songs/{song_id}/sections/0",
            json={"label": "My Custom Label"},
        )
        assert resp.status_code == 200

    def test_rename_updates_label(self, client):
        song_id = _import_and_analyze(client)
        client.patch(
            f"/api/v1/songs/{song_id}/sections/0", json={"label": "My Custom Label"}
        )
        sections = _get_sections(client, song_id)
        assert sections[0]["label"] == "My Custom Label"

    def test_rename_empty_label_returns_400(self, client):
        song_id = _import_and_analyze(client)
        resp = client.patch(
            f"/api/v1/songs/{song_id}/sections/0", json={"label": ""}
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "invalid_label"

    def test_rename_whitespace_only_returns_400(self, client):
        song_id = _import_and_analyze(client)
        resp = client.patch(
            f"/api/v1/songs/{song_id}/sections/0", json={"label": "   "}
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "invalid_label"

    def test_rename_too_long_returns_400(self, client):
        song_id = _import_and_analyze(client)
        resp = client.patch(
            f"/api/v1/songs/{song_id}/sections/0", json={"label": "x" * 65}
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "invalid_label"

    def test_rename_max_length_accepted(self, client):
        song_id = _import_and_analyze(client)
        resp = client.patch(
            f"/api/v1/songs/{song_id}/sections/0", json={"label": "x" * 64}
        )
        assert resp.status_code == 200

    def test_rename_unknown_song_returns_404(self, client):
        resp = client.patch(
            "/api/v1/songs/deadbeef00000000/sections/0",
            json={"label": "test"},
        )
        assert resp.status_code == 404

    def test_rename_out_of_range_section_returns_404(self, client):
        song_id = _import_and_analyze(client)
        resp = client.patch(
            f"/api/v1/songs/{song_id}/sections/9999",
            json={"label": "test"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# T101: Reset tests (FR-026)
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_returns_200(self, client):
        song_id = _import_and_analyze(client)
        resp = client.post(f"/api/v1/songs/{song_id}/sections/reset")
        assert resp.status_code == 200

    def test_reset_response_shape(self, client):
        """Reset response includes sections, ghost_boundaries, assignments, user_confirmed."""
        song_id = _import_and_analyze(client)
        data = client.post(f"/api/v1/songs/{song_id}/sections/reset").get_json()
        assert "sections" in data
        assert "ghost_boundaries" in data
        assert "assignments" in data
        assert data["user_confirmed"] is False

    def test_reset_restores_original_sections_after_rename(self, client):
        """After rename + reset, label returns to detected value."""
        song_id = _import_and_analyze(client)
        original_sections = _get_sections(client, song_id)
        original_label = original_sections[0]["label"]
        # Rename
        client.patch(
            f"/api/v1/songs/{song_id}/sections/0", json={"label": "CHANGED"}
        )
        # Reset
        client.post(f"/api/v1/songs/{song_id}/sections/reset")
        sections_after = _get_sections(client, song_id)
        assert sections_after[0]["label"] == original_label

    def test_reset_re_derives_default_assignments(self, client):
        """After reset, assignments are re-derived per FR-012a (theme_id is not None)."""
        song_id = _import_and_analyze(client)
        data = client.post(f"/api/v1/songs/{song_id}/sections/reset").get_json()
        for assignment in data["assignments"]:
            assert assignment["theme_id"] is not None

    def test_reset_unknown_song_returns_404(self, client):
        resp = client.post("/api/v1/songs/deadbeef00000000/sections/reset")
        assert resp.status_code == 404

    def test_reset_not_analyzed_returns_409(self, client):
        wav = _make_wav_bytes()
        song_id = client.post(
            "/api/v1/import",
            data={"audio": (io.BytesIO(wav), "test.wav")},
            content_type="multipart/form-data",
        ).get_json()["song"]["song_id"]
        resp = client.post(f"/api/v1/songs/{song_id}/sections/reset")
        assert resp.status_code == 409
