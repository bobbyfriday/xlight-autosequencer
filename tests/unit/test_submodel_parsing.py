"""Tests for src/grouper/layout.py — parse_pixel_ranges() and SubModel parsing."""
from __future__ import annotations

import tempfile
import textwrap

import pytest

from src.grouper.layout import SubModel, parse_layout, parse_pixel_ranges


class TestParsePixelRanges:
    def test_comma_list(self):
        assert parse_pixel_ranges("1,14,17") == (1, 14, 17)

    def test_simple_forward_range(self):
        assert parse_pixel_ranges("1-13") == (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)

    def test_single_element_range(self):
        assert parse_pixel_ranges("5-5") == (5,)

    def test_reverse_range_preserves_order(self):
        # xLights uses declaration order to drive intra-subModel direction —
        # don't sort/normalize.
        assert parse_pixel_ranges("16-15") == (16, 15)

    def test_mixed_comma_and_ranges(self):
        assert parse_pixel_ranges("95-96,94,1,14,16-15") == (95, 96, 94, 1, 14, 16, 15)

    def test_whitespace_tolerated(self):
        assert parse_pixel_ranges(" 1 , 2 , 3 - 5 ") == (1, 2, 3, 4, 5)

    def test_empty_string(self):
        assert parse_pixel_ranges("") == ()

    def test_whitespace_only(self):
        assert parse_pixel_ranges("   ") == ()

    def test_empty_tokens_dropped(self):
        # ",,1,," should yield (1,) — tolerate stray commas.
        assert parse_pixel_ranges(",,1,,") == (1,)

    def test_non_numeric_token_raises(self):
        with pytest.raises(ValueError, match="bad pixel-range token"):
            parse_pixel_ranges("1,foo,3")

    def test_non_numeric_range_raises(self):
        with pytest.raises(ValueError, match="bad pixel-range token"):
            parse_pixel_ranges("1-x")


class TestSubModelParsing:
    def _layout_xml(self, body: str) -> str:
        return textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <xlights_rgbeffects>
              <model name="Snowflake" DisplayAs="Custom" parm1="10" parm2="10">
                {body}
              </model>
            </xlights_rgbeffects>
        """)

    def _parse(self, body: str):
        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            f.write(self._layout_xml(body))
            tmp = f.name
        layout = parse_layout(tmp)
        return layout.props[0]

    def test_single_line_attribute(self):
        prop = self._parse('<subModel name="Ring 1" type="ranges" line0="1,14,17"/>')
        assert len(prop.sub_models) == 1
        sm = prop.sub_models[0]
        assert sm.name == "Ring 1"
        assert sm.pixel_indices == (1, 14, 17)

    def test_concatenates_multiple_lines(self):
        prop = self._parse(
            '<subModel name="Arrow 1" type="ranges" '
            'line0="95-96,94,1,14,16-15" line1="9-10,2,12-11" line2="4-3,6"/>'
        )
        sm = prop.sub_models[0]
        # line0: 95,96,94,1,14,16,15
        # line1: 9,10,2,12,11
        # line2: 4,3,6
        assert sm.pixel_indices == (95, 96, 94, 1, 14, 16, 15, 9, 10, 2, 12, 11, 4, 3, 6)

    def test_stops_at_missing_line_attr(self):
        # Skips line2 (missing) — does NOT skip line1 just because line2 is gone.
        prop = self._parse(
            '<subModel name="Spoke 1" type="ranges" line0="1,2" line1="3,4"/>'
        )
        sm = prop.sub_models[0]
        assert sm.pixel_indices == (1, 2, 3, 4)

    def test_empty_submodel(self):
        prop = self._parse('<subModel name="Unused" type="ranges"/>')
        sm = prop.sub_models[0]
        assert sm.name == "Unused"
        assert sm.pixel_indices == ()

    def test_bad_token_in_line_does_not_crash_layout(self):
        # A typo in user XML should skip that line, not blow up the whole
        # layout load.  The valid line1 is preserved.
        prop = self._parse(
            '<subModel name="Oops" type="ranges" line0="1,foo,3" line1="10,20"/>'
        )
        sm = prop.sub_models[0]
        # line0 raised, was skipped; line1 parsed normally.
        assert sm.pixel_indices == (10, 20)

    def test_submodel_is_frozen(self):
        sm = SubModel(name="X", pixel_indices=(1, 2))
        with pytest.raises(Exception):
            sm.name = "Y"  # type: ignore[misc]
