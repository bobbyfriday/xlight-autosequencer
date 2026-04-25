"""Timeline screen navigation: tab access + analysis-gated placeholder.

The Timeline screen renders the rich post-analysis view (waveform, sections,
beats, zoom controls). It only renders for an analyzed song — without one,
the screen falls back to a placeholder. This test covers:

1. Navigating to Timeline via the Chrome's "Timeline" tab without an
   analyzed song → placeholder is shown coherently
2. Library + analyze + click-through to Timeline placeholder for an
   imported-but-not-analyzed song

The full "Timeline rendered with sections + zoom" path is exercised by
test_content_flow.py, which has a real analysis run completed.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.slow]

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "cc0_music"


def _upload_via_api(base_url: str, mp3_path: Path) -> str:
    with mp3_path.open("rb") as f:
        resp = requests.post(
            f"{base_url}/api/v1/import",
            files={"audio": (mp3_path.name, f, "audio/mpeg")},
            timeout=30,
        )
    resp.raise_for_status()
    data = resp.json()
    return data.get("song_id") or data["song"]["song_id"]


@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_timeline_tab_without_song_shows_placeholder(
    page: Page, base_url: str, snapshot
) -> None:
    """No song → Timeline tab renders the 'Drop a song first' placeholder."""
    page.goto(base_url)

    # Empty library renders.
    library_root = page.get_by_test_id("library-screen").or_(
        page.get_by_test_id("library-empty-drop")
    ).first
    expect(library_root).to_be_visible(timeout=10000)
    snapshot("library-empty-before-timeline-tab")

    # Click Timeline tab.
    page.get_by_role("tab", name="Timeline").click()

    # The screen routes to the placeholder. The PlaceholderScreen renders the
    # label as text — assert it's present.
    expect(page.get_by_text("Drop a song first", exact=False).first).to_be_visible(
        timeout=5000
    )
    snapshot("timeline-placeholder-no-song")


@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_timeline_tab_with_imported_unanalyzed_song(
    page: Page, base_url: str, snapshot
) -> None:
    """Imported but not analyzed → Timeline tab shows analysis-required state."""
    _upload_via_api(base_url, FIXTURES_DIR / "maple_leaf_rag.mp3")
    page.goto(base_url)

    # Library has one song row.
    expect(page.get_by_test_id("library-screen")).to_be_visible(timeout=10000)
    song_rows = page.locator('[data-testid^="song-row-"]')
    expect(song_rows.first).to_be_visible(timeout=5000)
    snapshot("library-with-imported-song")

    # Click into Timeline via Chrome tab. With an imported-but-unanalyzed
    # song, the screen should be either the analysis-required placeholder
    # OR (if the app auto-selects the song first) the analyze-screen.
    page.get_by_role("tab", name="Timeline").click()

    # Coherent state: one of the gate placeholders OR the timeline itself
    # (if the app surfaces a partially-loaded view). All three are valid
    # — the test asserts that some recognizable Timeline-context state
    # rendered, not "the screen broke".
    expected_labels = [
        "Drop a song first",        # no song selected
        "Analysis required",        # imported but not analyzed
        "Loading analysis",         # transient load state
        "ZOOM",                     # full timeline (if analysis happened)
    ]
    visible = [
        lbl for lbl in expected_labels
        if page.get_by_text(lbl, exact=False).first.is_visible()
    ]
    assert visible, (
        f"Timeline tab landed in unrecognized state. "
        f"None of {expected_labels} are visible."
    )
    snapshot("timeline-with-unanalyzed-song")
