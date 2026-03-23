"""xLights value curve (.xvc) XML export."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.analyzer.result import ConditionedCurve, ValueCurveExport

if TYPE_CHECKING:
    from src.analyzer.structure import SongStructure


SOURCE_VERSION = "2024.01"
_XVC_ID = "ID_VALUECURVE_XVC"
_MACRO_MAX_POINTS = 100


def _build_data_attribute(
    values: list[int],
    macro: bool = False,
) -> str:
    """Encode a list of 0-100 integers as a pipe-delimited xLights data attribute."""
    pts = values
    if macro and len(pts) > _MACRO_MAX_POINTS:
        # Uniformly downsample to ≤100 points.
        step = len(pts) / _MACRO_MAX_POINTS
        pts = [pts[round(i * step)] for i in range(_MACRO_MAX_POINTS)]
        # Always include the last value.
        pts[-1] = values[-1]

    n = len(pts)
    pairs_str = ";".join(
        f"{i / max(n - 1, 1):.2f}:{float(v):.2f}"
        for i, v in enumerate(pts)
    )

    return (
        f"Active=TRUE|"
        f"Id={_XVC_ID}|"
        f"Type=Custom|"
        f"Min=0.00|"
        f"Max=100.00|"
        f"Values={pairs_str};"
    )


def _write_xvc_xml(data: str, output_path: str) -> None:
    root = ET.Element("valuecurve")
    root.set("data", data)
    tree = ET.ElementTree(root)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(fh, encoding="unicode", xml_declaration=False)


class XvcExporter:
    """Write ConditionedCurve objects as xLights .xvc value curve files."""

    def write(
        self,
        curve: ConditionedCurve,
        output_path: str,
        segment_label: str = "",
        macro: bool = False,
    ) -> ValueCurveExport:
        """
        Write a single .xvc file from a ConditionedCurve.

        macro=True reduces the curve to ≤100 control points for full-song use.
        """
        pts = curve.values
        if macro and len(pts) > _MACRO_MAX_POINTS:
            step = len(pts) / _MACRO_MAX_POINTS
            pts = [pts[round(i * step)] for i in range(_MACRO_MAX_POINTS)]
            pts[-1] = curve.values[-1]

        data = _build_data_attribute(pts, macro=False)  # pts already downsampled
        _write_xvc_xml(data, output_path)

        fps = curve.fps or 20
        duration_ms = int(len(curve.values) * 1000 / fps)

        return ValueCurveExport(
            file_path=output_path,
            curve_name=curve.name,
            curve_type="macro" if macro else "segment",
            start_ms=0,
            end_ms=duration_ms,
            point_count=len(pts),
            segment_label=segment_label or None,
        )

    def write_all(
        self,
        curves: list[ConditionedCurve],
        output_dir: str,
        song_structure: Optional["SongStructure"] = None,
    ) -> list[ValueCurveExport]:
        """Write one .xvc per curve plus a macro curve at reduced resolution."""
        out_dir = Path(output_dir)
        results: list[ValueCurveExport] = []

        for curve in curves:
            # Segment (full-resolution) curve
            seg_filename = f"{curve.stem}_{curve.feature}.xvc"
            seg_path = str(out_dir / seg_filename)
            results.append(self.write(curve, seg_path, macro=False))

            # Macro (reduced-resolution) curve
            macro_filename = f"{curve.stem}_{curve.feature}_macro.xvc"
            macro_path = str(out_dir / macro_filename)
            results.append(self.write(curve, macro_path, macro=True))

        return results
