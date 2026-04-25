"""Upload flow: pick a fixture MP3, POST /api/v1/import, verify analyze screen.

Marked `ui` — skipped by default; run via `pytest -m ui` or the acceptance gate.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.slow]


@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_upload_flow_renders_analyze_screen(
    page: Page, base_url: str, fixture_mp3: Path, snapshot
) -> None:
    # Navigate to the library (drop) screen.
    page.goto(base_url)

    # The empty library shows the drop target.
    drop = page.get_by_test_id("library-empty-drop").or_(page.get_by_test_id("drop-target")).first
    expect(drop).to_be_visible(timeout=5000)
    snapshot("library-empty")

    # Upload via the Library's hidden file input (wrapped by the drop area).
    file_input = page.get_by_test_id("library-file-input")
    file_input.set_input_files(str(fixture_mp3))

    # After import succeeds the client navigates to the analyze screen.
    analyze_root = page.get_by_test_id("analyze-screen").first
    expect(analyze_root).to_be_visible(timeout=30000)

    # Minimum sanity: the metadata banner rendered with a title derived from the MP3.
    banner = page.get_by_test_id("metadata-banner").first
    expect(banner).to_be_visible()
    snapshot("analyze-rendered-after-upload")
