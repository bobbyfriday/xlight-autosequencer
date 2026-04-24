"""View flow: analyzed content renders in the UI coherently.

Navigates between library and analyze views; asserts counts and state survive
round-trips. This catches regressions in routing, state hydration, and
backend data plumbing.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.slow]


@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_view_flow_library_to_analyze_roundtrip(
    page: Page, base_url: str, fixture_mp3: Path
) -> None:
    page.goto(base_url)

    # The library renders either `library-screen` (non-empty) or
    # `library-empty-drop` (empty) — wait for whichever appears.
    library_root = page.get_by_test_id("library-screen").or_(
        page.get_by_test_id("library-empty-drop")
    ).first
    expect(library_root).to_be_visible(timeout=10000)

    # Upload a fixture if the library is empty.
    empty_drop = page.get_by_test_id("library-empty-drop")
    if empty_drop.is_visible():
        page.get_by_test_id("library-file-input").set_input_files(str(fixture_mp3))

    # Arrive at the analyze screen.
    expect(page.get_by_test_id("analyze-screen").first).to_be_visible(timeout=30000)

    # Navigate back to library and confirm the song row is present.
    page.goto(base_url)
    expect(page.get_by_test_id("library-screen")).to_be_visible(timeout=10000)

    # At least one song row should exist (id pattern: song-row-<hash>).
    song_rows = page.locator('[data-testid^="song-row-"]')
    expect(song_rows.first).to_be_visible(timeout=5000)
    assert song_rows.count() >= 1

    # Click the first song row. The app routes by status — for a just-uploaded
    # unanalyzed song, this may land on analyze-screen or on an intermediate
    # "analysis required" state. Either is a coherent render; we just assert
    # we leave the library screen.
    song_rows.first.click()
    expect(page.get_by_test_id("library-screen")).not_to_be_visible(timeout=10000)
