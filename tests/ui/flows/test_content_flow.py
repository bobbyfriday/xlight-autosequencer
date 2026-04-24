"""Content verification flow: upload → real analysis → assert content matches manifest.

Unlike the other UI flows (smoke tests — "does the screen render?"), this flow
actually runs the analyzer pipeline and asserts the displayed content matches
the manifest's expected values. It's the one flow that catches regressions
in how backend analysis data plumbs through to UI rendering.

Marked `ui` + `content` — the `content` marker lets the acceptance gate's quick
mode select this flow specifically (`pytest -m "ui and content"`).

This test is expensive: the analyzer pipeline runs for real on a mid-sized
fixture. Expect ~30–90s wall time depending on CPU and optional algorithms.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.content, pytest.mark.slow]

MANIFEST = Path(__file__).resolve().parent.parent.parent / "fixtures" / "cc0_music" / "manifest.json"


def _manifest_track(slug: str) -> dict:
    data = json.loads(MANIFEST.read_text())
    for t in data["tracks"]:
        if t["slug"] == slug:
            return t
    raise AssertionError(f"slug '{slug}' not in manifest")


def _section_detection_available() -> bool:
    """Section detection (qm_segmenter / madmom) requires the .venv-vamp stack.
    Without it, librosa alone returns 0 sections on most fixtures, so a content
    check against expected_section_count would always fail. Skip cleanly
    instead of false-reporting a regression.
    """
    from src.analyzer.capabilities import detect_capabilities
    caps = detect_capabilities()
    # madmom powers downbeat/segment detection; vamp powers qm_segmenter.
    # Either is sufficient for non-zero sections on the fixtures.
    return bool(caps.get("madmom") or caps.get("vamp"))


@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_content_flow_analyzer_populates_ui(
    page: Page, base_url: str, fixture_mp3: Path
) -> None:
    if not _section_detection_available():
        pytest.skip(
            "Section detection requires madmom or vamp (installed via .venv-vamp). "
            "Without either, librosa-only analysis returns 0 sections and the "
            "manifest's expected_section_count can't be validated."
        )

    expected = _manifest_track("maple_leaf_rag")

    page.goto(base_url)

    library_root = page.get_by_test_id("library-screen").or_(
        page.get_by_test_id("library-empty-drop")
    ).first
    expect(library_root).to_be_visible(timeout=10000)

    # Fresh upload — library is reset between tests by the autouse fixture.
    empty_drop = page.get_by_test_id("library-empty-drop")
    if empty_drop.is_visible():
        page.get_by_test_id("library-file-input").set_input_files(str(fixture_mp3))

    # Land on analyze screen — live analysis auto-starts for a freshly imported song.
    expect(page.get_by_test_id("analyze-screen").first).to_be_visible(timeout=30000)

    # ---- Metadata checks (available before analysis completes) -------------

    # Header meta includes title + formatted duration.
    header_meta = page.get_by_test_id("analyze-header-meta")
    expect(header_meta).to_be_visible(timeout=10000)

    # Song title from ID3. The fixture's ID3 title is "Maple Leaf Rag"
    # (library service derives it from the MP3 tags).
    title_attr = header_meta.get_attribute("data-song-title") or ""
    assert "maple" in title_attr.lower() or "rag" in title_attr.lower(), (
        f"Expected title to mention maple/rag; got {title_attr!r}"
    )

    # Duration displayed within ±3 seconds of manifest value.
    duration_ms_str = header_meta.get_attribute("data-duration-ms") or "0"
    displayed_sec = int(duration_ms_str) // 1000
    expected_sec = int(expected["duration_seconds"])
    assert abs(displayed_sec - expected_sec) <= 3, (
        f"Displayed duration {displayed_sec}s off from manifest {expected_sec}s "
        "(tolerance ±3s — MP3 duration depends on which decoder rounds)"
    )

    # Header title flips from "Analyzing…" to "Analysis complete" once the
    # pipeline finishes. Sections stream in via SSE during the run.
    # ---- Wait for analysis completion + assert section count ---------------

    # Live analysis: inspector-sections-header is present throughout and its
    # data-section-count grows as sections are detected.
    inspector_header = page.get_by_test_id("inspector-sections-header")
    expect(inspector_header).to_be_visible(timeout=30000)

    # Wait for header-title to flip to "Analysis complete". Long timeout:
    # the full analyzer pipeline runs for real (30-180s depending on corpus).
    analysis_complete_locator = page.locator(
        '[data-testid="analyze-header-title"][data-analysis-complete="true"]'
    )
    expect(analysis_complete_locator).to_be_visible(timeout=240_000)

    # Sections are populated by a secondary fetch that triggers *after* the
    # analysis-complete flag flips (Analyze.tsx "Fetch sections on complete"
    # effect at ~line 197). Wait for the DOM attribute to reach > 0 before
    # asserting — otherwise we race with that fetch.
    sections_populated = page.locator(
        '[data-testid="inspector-sections-header"]:not([data-section-count="0"])'
    )
    expect(sections_populated).to_be_visible(timeout=30_000)

    section_count_str = inspector_header.get_attribute("data-section-count")
    assert section_count_str is not None, "inspector-sections-header is missing data-section-count"
    actual_count = int(section_count_str)

    expected_count = int(expected["expected_section_count"])
    # Tolerance ±2 sections: section detection has inherent fuzziness.
    # Maple Leaf Rag is AABB so any detection under 2 or over 6 is a real regression.
    assert abs(actual_count - expected_count) <= 2, (
        f"Displayed section count {actual_count} far from manifest expected "
        f"{expected_count} (tolerance ±2). Likely regression in section detection."
    )

    # Also verify the visible label matches the count — catches state-display bugs.
    header_text = inspector_header.text_content() or ""
    match = re.search(r"SECTIONS\s*·\s*(\d+)", header_text)
    assert match, f"Could not parse section count from header text: {header_text!r}"
    assert int(match.group(1)) == actual_count, (
        f"DOM attribute ({actual_count}) disagrees with visible text ({match.group(1)})"
    )
