"""Tests for XvcExporter: .xvc value curve XML output."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.analyzer.result import ConditionedCurve
from src.analyzer.xvc_export import XvcExporter


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _curve(
    name: str = "drums_rms",
    stem: str = "drums",
    feature: str = "rms",
    fps: int = 20,
    values: list[int] | None = None,
) -> ConditionedCurve:
    if values is None:
        values = list(range(0, 101, 5))  # 21 points, 0..100
    return ConditionedCurve(name=name, stem=stem, feature=feature, fps=fps, values=values)


@pytest.fixture()
def exporter() -> XvcExporter:
    return XvcExporter()


@pytest.fixture()
def written_xvc(tmp_path, exporter):
    curve = _curve()
    out = str(tmp_path / "drums_rms.xvc")
    exporter.write(curve, out)
    return out


# ── T011: XvcExporter.write() — XML structure ─────────────────────────────────


class TestXvcExporterWrite:
    """T011 — write() produces valid .xvc XML with correct structure."""

    def test_produces_valid_xml(self, written_xvc):
        tree = ET.parse(written_xvc)
        assert tree is not None

    def test_root_element_is_valuecurve(self, written_xvc):
        root = ET.parse(written_xvc).getroot()
        assert root.tag == "valuecurve"

    def test_data_attribute_present(self, written_xvc):
        root = ET.parse(written_xvc).getroot()
        assert root.get("data") is not None

    def test_data_contains_active_true(self, written_xvc):
        data = ET.parse(written_xvc).getroot().get("data")
        assert "Active=TRUE" in data

    def test_data_contains_id_valuecurve_xvc(self, written_xvc):
        data = ET.parse(written_xvc).getroot().get("data")
        assert "Id=ID_VALUECURVE_XVC" in data

    def test_data_contains_type_custom(self, written_xvc):
        data = ET.parse(written_xvc).getroot().get("data")
        assert "Type=Custom" in data

    def test_data_contains_min_0(self, written_xvc):
        data = ET.parse(written_xvc).getroot().get("data")
        assert "Min=0.00" in data

    def test_data_contains_max_100(self, written_xvc):
        data = ET.parse(written_xvc).getroot().get("data")
        assert "Max=100.00" in data

    def test_values_field_present(self, written_xvc):
        data = ET.parse(written_xvc).getroot().get("data")
        assert "Values=" in data

    def test_values_semicolon_separated_x_colon_y(self, written_xvc):
        data = ET.parse(written_xvc).getroot().get("data")
        # Extract the Values=... section
        m = re.search(r"Values=([^|]+)", data)
        assert m, f"Values field not found in: {data}"
        pairs = m.group(1).rstrip(";").split(";")
        for pair in pairs:
            parts = pair.split(":")
            assert len(parts) == 2, f"Expected x:y pair, got: {pair}"
            x, y = float(parts[0]), float(parts[1])
            assert 0.0 <= x <= 1.0, f"x={x} out of [0, 1]"
            assert 0.0 <= y <= 100.0, f"y={y} out of [0, 100]"

    def test_x_values_span_0_to_1(self, written_xvc):
        """x values must start at 0.00 and end at 1.00."""
        data = ET.parse(written_xvc).getroot().get("data")
        m = re.search(r"Values=([^|]+)", data)
        pairs = m.group(1).rstrip(";").split(";")
        xs = [float(p.split(":")[0]) for p in pairs]
        assert xs[0] == pytest.approx(0.0, abs=0.01)
        assert xs[-1] == pytest.approx(1.0, abs=0.01)

    def test_y_values_match_curve_values(self, tmp_path, exporter):
        """Y values at first and last control points match curve values."""
        values = [10, 50, 90]
        curve = _curve(values=values)
        out = str(tmp_path / "test.xvc")
        exporter.write(curve, out)
        data = ET.parse(out).getroot().get("data")
        m = re.search(r"Values=([^|]+)", data)
        pairs = m.group(1).rstrip(";").split(";")
        ys = [float(p.split(":")[1]) for p in pairs]
        assert ys[0] == pytest.approx(10.0, abs=1.0)
        assert ys[-1] == pytest.approx(90.0, abs=1.0)

    def test_xml_declaration_present(self, tmp_path, exporter):
        curve = _curve()
        out = str(tmp_path / "decl.xvc")
        exporter.write(curve, out)
        content = Path(out).read_text(encoding="utf-8")
        assert content.startswith("<?xml")

    def test_returns_value_curve_export(self, tmp_path, exporter):
        from src.analyzer.result import ValueCurveExport
        curve = _curve()
        out = str(tmp_path / "test.xvc")
        result = exporter.write(curve, out)
        assert isinstance(result, ValueCurveExport)

    def test_returned_file_path_matches(self, tmp_path, exporter):
        curve = _curve()
        out = str(tmp_path / "test.xvc")
        result = exporter.write(curve, out)
        assert result.file_path == out

    def test_returned_point_count_matches_values(self, tmp_path, exporter):
        values = [0, 25, 50, 75, 100]
        curve = _curve(values=values)
        out = str(tmp_path / "test.xvc")
        result = exporter.write(curve, out)
        assert result.point_count == len(values)


# ── T012: macro curve export — ≤100 control points ───────────────────────────


class TestMacroCurve:
    """T012 — macro=True reduces the curve to ≤100 control points."""

    def test_macro_reduces_large_curve(self, tmp_path, exporter):
        values = list(range(100)) * 3  # 300 values
        curve = _curve(values=values)
        out = str(tmp_path / "macro.xvc")
        result = exporter.write(curve, out, macro=True)
        assert result.point_count <= 100

    def test_macro_small_curve_unchanged(self, tmp_path, exporter):
        values = list(range(50))
        curve = _curve(values=values)
        out = str(tmp_path / "macro_small.xvc")
        result = exporter.write(curve, out, macro=True)
        assert result.point_count <= 100

    def test_macro_x_still_spans_0_to_1(self, tmp_path, exporter):
        values = list(range(200))
        curve = _curve(values=values)
        out = str(tmp_path / "macro_span.xvc")
        exporter.write(curve, out, macro=True)
        data = ET.parse(out).getroot().get("data")
        m = re.search(r"Values=([^|]+)", data)
        pairs = m.group(1).rstrip(";").split(";")
        xs = [float(p.split(":")[0]) for p in pairs]
        assert xs[0] == pytest.approx(0.0, abs=0.01)
        assert xs[-1] == pytest.approx(1.0, abs=0.01)

    def test_macro_type_is_macro(self, tmp_path, exporter):
        values = list(range(50))
        curve = _curve(values=values)
        out = str(tmp_path / "macro_type.xvc")
        result = exporter.write(curve, out, macro=True)
        assert result.curve_type == "macro"

    def test_non_macro_type_is_segment(self, tmp_path, exporter):
        curve = _curve()
        out = str(tmp_path / "seg.xvc")
        result = exporter.write(curve, out, macro=False)
        assert result.curve_type == "segment"


# ── T013: output file naming convention ──────────────────────────────────────


class TestNamingConvention:
    """T013 — write_all() uses {stem}_{feature}_{qualifier}.xvc naming."""

    def test_write_all_returns_list(self, tmp_path, exporter):
        curves = [
            _curve(name="drums_rms", stem="drums", feature="rms"),
            _curve(name="bass_rms", stem="bass", feature="rms"),
        ]
        results = exporter.write_all(curves, str(tmp_path))
        assert isinstance(results, list)
        assert len(results) > 0

    def test_write_all_creates_xvc_files(self, tmp_path, exporter):
        curves = [_curve(name="drums_rms", stem="drums", feature="rms")]
        exporter.write_all(curves, str(tmp_path))
        xvc_files = list(tmp_path.glob("*.xvc"))
        assert len(xvc_files) > 0

    def test_write_all_filename_contains_stem(self, tmp_path, exporter):
        curves = [_curve(name="vocals_rms", stem="vocals", feature="rms")]
        exporter.write_all(curves, str(tmp_path))
        xvc_files = list(tmp_path.glob("*.xvc"))
        names = [f.name for f in xvc_files]
        assert any("vocals" in n for n in names), f"No file with 'vocals' in {names}"

    def test_write_all_filename_contains_feature(self, tmp_path, exporter):
        curves = [_curve(name="drums_flux", stem="drums", feature="flux")]
        exporter.write_all(curves, str(tmp_path))
        xvc_files = list(tmp_path.glob("*.xvc"))
        names = [f.name for f in xvc_files]
        assert any("flux" in n for n in names), f"No file with 'flux' in {names}"

    def test_write_all_files_end_in_xvc(self, tmp_path, exporter):
        curves = [_curve(name="guitar_rms", stem="guitar", feature="rms")]
        exporter.write_all(curves, str(tmp_path))
        xvc_files = list(tmp_path.glob("*.xvc"))
        for f in xvc_files:
            assert f.suffix == ".xvc"

    def test_write_all_produces_macro_file(self, tmp_path, exporter):
        """write_all includes a macro (full-song) curve for each input curve."""
        curves = [_curve(name="drums_rms", stem="drums", feature="rms", values=list(range(200)))]
        results = exporter.write_all(curves, str(tmp_path))
        macro_results = [r for r in results if r.curve_type == "macro"]
        assert len(macro_results) >= 1

    def test_segment_label_in_result(self, tmp_path, exporter):
        curve = _curve()
        out = str(tmp_path / "seg.xvc")
        result = exporter.write(curve, out, segment_label="verse_1")
        assert result.segment_label == "verse_1"
