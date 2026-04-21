"""Failing tests for the max-overlap section-mapping algorithm — T105 (US3).

Mirrors research §10: 0.3 threshold, orphan detection, new-sections-need-theme.
"""
from __future__ import annotations

import pytest

# The module under test (to be implemented in T106)
from src.review.api.v1.overlap_mapping import compute_overlap_mapping


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sec(index: int, start_ms: int, end_ms: int, theme_id: str = "shimmer-wash") -> dict:
    return {
        "index": index,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "kind": "verse",
        "label": f"Section {index}",
        "theme_id": theme_id,
    }


# ---------------------------------------------------------------------------
# Basic overlap cases
# ---------------------------------------------------------------------------

class TestComputeOverlapMapping:

    def test_identical_sections_map_to_themselves(self):
        old = [_sec(0, 0, 10000, "theme-a"), _sec(1, 10000, 20000, "theme-b")]
        new = [_sec(0, 0, 10000), _sec(1, 10000, 20000)]
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        assert result["mapping"][0]["action"] in ("kept", "shifted")
        assert result["mapping"][1]["action"] in ("kept", "shifted")

    def test_shifted_boundary_keeps_theme(self):
        """A boundary that shifted 200ms: new section still maps to old (>= 0.3 overlap)."""
        old = [_sec(0, 0, 10000, "theme-a"), _sec(1, 10000, 20000, "theme-b")]
        new = [_sec(0, 0, 10200), _sec(1, 10200, 20000)]  # boundary shifted 200ms
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        mapping = {r["new_section_index"]: r for r in result["mapping"]}
        assert mapping[0]["action"] in ("kept", "shifted")
        assert mapping[0]["inherited_theme_id"] == "theme-a"
        assert mapping[1]["action"] in ("kept", "shifted")
        assert mapping[1]["inherited_theme_id"] == "theme-b"

    def test_new_section_with_low_overlap_needs_theme(self):
        """New section that barely overlaps an old section gets action=needs_theme."""
        old = [_sec(0, 0, 10000, "theme-a")]
        # New section overlaps old by only 10% (1000ms of 10000ms new duration)
        new = [_sec(0, 9000, 19000)]  # overlaps old by 1000ms; 1000/10000 = 0.10 < 0.3
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        mapping = {r["new_section_index"]: r for r in result["mapping"]}
        assert mapping[0]["action"] == "needs_theme"
        assert mapping[0]["inherited_theme_id"] is None

    def test_0_3_threshold_boundary_gets_theme(self):
        """Overlap ratio exactly at 0.3 is accepted (carry-over)."""
        old = [_sec(0, 0, 10000, "theme-a")]
        # New section: 10000ms duration, overlaps old by 3000ms = 0.3
        new = [_sec(0, 7000, 17000)]  # overlap with old: 7000–10000 = 3000ms, ratio 0.3
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        mapping = {r["new_section_index"]: r for r in result["mapping"]}
        assert mapping[0]["action"] in ("kept", "shifted")
        assert mapping[0]["inherited_theme_id"] == "theme-a"

    def test_below_threshold_gives_needs_theme(self):
        """Overlap ratio below 0.3 → needs_theme."""
        old = [_sec(0, 0, 10000, "theme-a")]
        # New section: 10000ms duration, overlaps old by 2999ms = 0.2999 < 0.3
        new = [_sec(0, 7001, 17001)]
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        mapping = {r["new_section_index"]: r for r in result["mapping"]}
        assert mapping[0]["action"] == "needs_theme"

    # ---------------------------------------------------------------------------
    # Orphan (dropped) detection
    # ---------------------------------------------------------------------------

    def test_orphan_old_section_appears_in_dropped(self):
        """Old section with no matching new section is an orphan (dropped)."""
        old = [
            _sec(0, 0, 10000, "theme-a"),
            _sec(1, 10000, 20000, "theme-b"),
        ]
        # New has only one section covering old[0] — old[1] is orphaned
        new = [_sec(0, 0, 10000)]
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        assert len(result["dropped"]) >= 1
        dropped_indexes = [d["old_section_index"] for d in result["dropped"]]
        assert 1 in dropped_indexes

    def test_no_orphans_when_all_mapped(self):
        """No dropped when every old section is mapped."""
        old = [_sec(0, 0, 10000, "theme-a"), _sec(1, 10000, 20000, "theme-b")]
        new = [_sec(0, 0, 10000), _sec(1, 10000, 20000)]
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        assert result["dropped"] == []

    # ---------------------------------------------------------------------------
    # New sections needing theme
    # ---------------------------------------------------------------------------

    def test_new_section_in_gap_needs_theme(self):
        """A new section in entirely new time range needs a theme."""
        old = [_sec(0, 0, 10000, "theme-a")]
        new = [_sec(0, 0, 10000), _sec(1, 10000, 20000)]  # second is new territory
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        mapping = {r["new_section_index"]: r for r in result["mapping"]}
        assert mapping[1]["action"] == "needs_theme"

    # ---------------------------------------------------------------------------
    # Split produces two sections from one
    # ---------------------------------------------------------------------------

    def test_split_both_halves_carry_over_theme(self):
        """When one old section maps to two new sections (split), both get theme."""
        old = [_sec(0, 0, 20000, "theme-a")]
        new = [_sec(0, 0, 10000), _sec(1, 10000, 20000)]  # split in half
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        mapping = {r["new_section_index"]: r for r in result["mapping"]}
        # Both halves overlap old[0] by 50% = 0.5 >= 0.3
        assert mapping[0]["inherited_theme_id"] == "theme-a"
        assert mapping[1]["inherited_theme_id"] == "theme-a"

    # ---------------------------------------------------------------------------
    # Result structure
    # ---------------------------------------------------------------------------

    def test_result_has_required_keys(self):
        old = [_sec(0, 0, 10000, "theme-a")]
        new = [_sec(0, 0, 10000)]
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        assert "mapping" in result
        assert "dropped" in result

    def test_mapping_entries_have_required_fields(self):
        old = [_sec(0, 0, 10000, "theme-a")]
        new = [_sec(0, 0, 10000)]
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        for entry in result["mapping"]:
            assert "new_section_index" in entry
            assert "action" in entry
            assert "inherited_theme_id" in entry

    def test_empty_inputs_return_empty(self):
        result = compute_overlap_mapping(old_sections=[], new_sections=[])
        assert result["mapping"] == []
        assert result["dropped"] == []

    def test_only_new_sections_all_need_theme(self):
        old: list = []
        new = [_sec(0, 0, 10000), _sec(1, 10000, 20000)]
        result = compute_overlap_mapping(old_sections=old, new_sections=new)
        for entry in result["mapping"]:
            assert entry["action"] == "needs_theme"
