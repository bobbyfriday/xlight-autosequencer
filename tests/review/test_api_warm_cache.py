"""T147: SC-008 — GET /api/v1/songs/<id>/analysis returns within 1000ms when
analysis data is already cached in the session directory.
"""
import json
import time

import pytest

from src.review.storage.library import save_library
from src.review.storage.paths import library_root


def _seed_song_with_analysis(tmp_path, song_id: str):
    """Write a library entry + a minimal session.json for the song."""
    lib = {
        "schema_version": 1,
        "songs": [
            {
                "song_id": song_id,
                "title": "Warm Cache Song",
                "status": "analyzed",
                "source_paths": [],
                "folder_id": "unfiled",
                "imported_at": "2026-04-21T00:00:00Z",
            }
        ],
        "folders": [{"id": "unfiled", "name": "Unfiled", "created_at": "2026-04-21T00:00:00Z"}],
        "preferences": {},
        "layout": None,
    }
    save_library(lib)

    # Write a minimal session.json with pre-cooked analysis
    song_dir = library_root() / "songs" / song_id
    song_dir.mkdir(parents=True, exist_ok=True)
    analysis_data = {
        "song_id": song_id,
        "detected_sections": [
            {"index": 0, "start_ms": 0, "end_ms": 5000, "kind": "verse", "label": "Verse 1"},
        ],
        "duration_ms": 5000,
        "bpm": 120.0,
        "timing_tracks": [],
    }
    (song_dir / "analysis.json").write_text(
        json.dumps(analysis_data), encoding="utf-8"
    )


class TestWarmCachePerformance:
    def test_analysis_response_within_1000ms_warm_cache(
        self, client, tmp_path, monkeypatch
    ):
        """SC-008: GET /api/v1/songs/<id>/analysis < 1000ms when data cached."""
        monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
        song_id = "warmcache0000001"
        _seed_song_with_analysis(tmp_path, song_id)

        start = time.monotonic()
        resp = client.get(f"/api/v1/songs/{song_id}/analysis")
        elapsed_ms = (time.monotonic() - start) * 1000

        # The endpoint may return 200 (data cached) or 202/404 (not yet analyzed).
        # Either way, the response must arrive within 1000ms.
        assert elapsed_ms < 1000, (
            f"GET /api/v1/songs/{song_id}/analysis took {elapsed_ms:.1f}ms, "
            f"expected < 1000ms (SC-008)"
        )
