"""Tests for ``_read_layout_model_names`` and the ``layout_path`` kwarg on
``parse()`` / ``parse_bytes()``.

Covers the OpenSpec change ``microscope-placement-coverage`` §2.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.evaluation.xsq_reader import _read_layout_model_names, parse, parse_bytes

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REFERENCE_LAYOUT = _REPO_ROOT / "tests" / "fixtures" / "reference" / "layout.xml"


# ── _read_layout_model_names ────────────────────────────────────────────────


def test_reads_models_in_document_order(tmp_path):
    layout = tmp_path / "layout.xml"
    layout.write_text(
        """<?xml version="1.0"?>
<xlightsproject>
  <models>
    <model name="Z_first" DisplayAs="Matrix"/>
    <model name="A_second" DisplayAs="Tree 360"/>
    <model name="M_third" DisplayAs="Star"/>
  </models>
</xlightsproject>
""",
        encoding="utf-8",
    )
    assert _read_layout_model_names(layout) == ("Z_first", "A_second", "M_third")


def test_returns_empty_when_no_models_defined(tmp_path):
    layout = tmp_path / "empty.xml"
    layout.write_text(
        """<?xml version="1.0"?>
<xlightsproject>
  <models>
  </models>
</xlightsproject>
""",
        encoding="utf-8",
    )
    assert _read_layout_model_names(layout) == ()


def test_raises_when_models_root_missing(tmp_path):
    layout = tmp_path / "no_models.xml"
    layout.write_text(
        """<?xml version="1.0"?>
<xlightsproject>
  <somethingElse/>
</xlightsproject>
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no <models> root"):
        _read_layout_model_names(layout)


def test_skips_models_without_name_attribute(tmp_path):
    layout = tmp_path / "weird.xml"
    layout.write_text(
        """<?xml version="1.0"?>
<xlightsproject>
  <models>
    <model name="HasName" DisplayAs="Matrix"/>
    <model DisplayAs="Tree 360"/>
    <model name="" DisplayAs="Arch"/>
    <model name="AlsoHasName" DisplayAs="Star"/>
  </models>
</xlightsproject>
""",
        encoding="utf-8",
    )
    assert _read_layout_model_names(layout) == ("HasName", "AlsoHasName")


def test_reads_reference_layout():
    """The reference layout has 9 models — make sure they all come through."""
    names = _read_layout_model_names(_REFERENCE_LAYOUT)
    assert "MatrixCenter" in names
    assert "MegaTree" in names
    assert "RadialSpinner" in names
    assert len(names) == 9


# ── parse() / parse_bytes() layout_path kwarg ───────────────────────────────


_MINIMAL_XSQ = b"""<?xml version="1.0"?>
<xsequence>
  <head>
    <sequenceDuration>10.0</sequenceDuration>
  </head>
  <ColorPalettes/>
  <ElementEffects>
    <Element type="model" name="MatrixCenter">
      <EffectLayer>
        <Effect name="Plasma" startTime="0" endTime="5000" palette="-1"/>
      </EffectLayer>
    </Element>
  </ElementEffects>
</xsequence>
"""


def test_parse_bytes_without_layout_yields_empty_universe():
    summary = parse_bytes(_MINIMAL_XSQ)
    assert summary.layout_model_names == ()
    # model_names still reflects placements
    assert summary.model_names == ("MatrixCenter",)


def test_parse_bytes_with_layout_populates_universe(tmp_path):
    layout = tmp_path / "layout.xml"
    layout.write_text(
        """<?xml version="1.0"?>
<xlightsproject>
  <models>
    <model name="MatrixCenter"/>
    <model name="UnreachedProp"/>
  </models>
</xlightsproject>
""",
        encoding="utf-8",
    )
    summary = parse_bytes(_MINIMAL_XSQ, layout_path=layout)
    assert summary.layout_model_names == ("MatrixCenter", "UnreachedProp")
    # model_names is unchanged — only placement-bearing models
    assert summary.model_names == ("MatrixCenter",)


def test_parse_from_disk_propagates_layout_kwarg(tmp_path):
    xsq = tmp_path / "seq.xsq"
    xsq.write_bytes(_MINIMAL_XSQ)
    summary = parse(xsq, layout_path=_REFERENCE_LAYOUT)
    assert "MatrixCenter" in summary.layout_model_names
    assert len(summary.layout_model_names) == 9
