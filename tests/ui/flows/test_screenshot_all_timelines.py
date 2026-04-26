"""Screenshot every MP3's timeline view for visual review.

Not a regression gate — explicitly opt-in via `pytest -m screenshot_all`.
Imports each MP3 (CC0 fixtures + ./songs/), runs analysis through the UI,
navigates to the timeline, and saves a full-page screenshot to
`tests/golden/timeline-screenshots/<slug>.png`.

The directory is gitignored — these are diagnostic artifacts, not goldens.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.slow, pytest.mark.screenshot_all]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCREENSHOTS_DIR = REPO_ROOT / "tests" / "golden" / "timeline-screenshots"
SONGS_DIR = REPO_ROOT / "songs"
CC0_DIR = REPO_ROOT / "tests" / "fixtures" / "cc0_music"


def _slug(mp3: Path) -> str:
    return mp3.stem


def _discover_mp3s() -> list[Path]:
    """Top-level MP3 in each ./songs/<slug>/ dir + the 4 CC0 fixtures.

    Stems live under `<dir>/stems/*.mp3`; we exclude those by limiting glob
    depth.
    """
    paths: list[Path] = []
    if SONGS_DIR.exists():
        for d in sorted(SONGS_DIR.iterdir()):
            if not d.is_dir():
                continue
            mp3 = d / f"{d.name}.mp3"
            if mp3.exists():
                paths.append(mp3)
    if CC0_DIR.exists():
        for mp3 in sorted(CC0_DIR.glob("*.mp3")):
            paths.append(mp3)
    return paths


SONGS = _discover_mp3s()


@pytest.fixture(autouse=True)
def _ensure_screenshots_dir() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("mp3", SONGS, ids=[_slug(p) for p in SONGS])
def test_screenshot_timeline(mp3: Path, page: Page, base_url: str) -> None:
    """Upload `mp3`, run analysis, navigate to timeline, screenshot full-page."""
    out_path = SCREENSHOTS_DIR / f"{_slug(mp3)}.png"

    # ---- Land on Library, upload via file input ---------------------------
    page.goto(base_url)

    library_root = page.get_by_test_id("library-screen").or_(
        page.get_by_test_id("library-empty-drop")
    ).first
    expect(library_root).to_be_visible(timeout=15000)

    # Library is wiped by the autouse fixture, so the empty-drop input is shown.
    empty_drop = page.get_by_test_id("library-empty-drop")
    if empty_drop.is_visible():
        page.get_by_test_id("library-file-input").set_input_files(str(mp3))

    # Analyze screen auto-loads.
    expect(page.get_by_test_id("analyze-screen").first).to_be_visible(timeout=30000)

    # ---- Wait for analysis complete -----------------------------------------
    analysis_complete = page.locator(
        '[data-testid="analyze-header-title"][data-analysis-complete="true"]'
    )
    # Generous timeout: fresh analysis without cached stems can run ~3 min on
    # the largest fixtures; with cached stems, ~30-60s. Allow worst-case +
    # margin.
    expect(analysis_complete).to_be_visible(timeout=300_000)

    # Sections populate after a secondary fetch. Don't fail if 0 sections —
    # some songs may not have detectable sections, but the timeline should
    # still render. Just wait briefly for the secondary fetch to settle.
    page.wait_for_timeout(1500)

    # ---- Navigate to Timeline + screenshot ----------------------------------
    review_btn = page.get_by_role("button", name=re.compile(r"review timeline", re.I)).first
    expect(review_btn).to_be_visible(timeout=10000)
    review_btn.click()

    # Timeline marker: "ZOOM" + "WAVEFORM" labels are unique to that screen.
    expect(page.get_by_text("ZOOM", exact=False).first).to_be_visible(timeout=15000)
    expect(page.get_by_text("WAVEFORM", exact=False).first).to_be_visible(timeout=5000)

    # Brief settle so the waveform renders and section overlays paint.
    page.wait_for_timeout(800)

    page.screenshot(path=str(out_path), full_page=True, type="png")
    assert out_path.exists() and out_path.stat().st_size > 1000, (
        f"Screenshot was not written or is suspiciously small: {out_path}"
    )
