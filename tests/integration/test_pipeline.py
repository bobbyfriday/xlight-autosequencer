"""Integration test for the pipeline CLI command (US7)."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.cli import cli

FIXTURE = Path(__file__).parent.parent / "fixtures" / "beat_120bpm_10s.wav"


@pytest.mark.skipif(
    not FIXTURE.exists(),
    reason="Fixture audio file not found",
)
class TestPipelineCLI:
    """T046 — pipeline command produces valid .xtiming and .xvc output files."""

    def test_pipeline_exits_zero(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "pipeline",
            str(FIXTURE),
            "--output-dir", str(tmp_path),
            "--no-sweep",
        ])
        assert result.exit_code == 0, f"pipeline failed:\n{result.output}"

    def test_pipeline_produces_xtiming_file(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "pipeline",
            str(FIXTURE),
            "--output-dir", str(tmp_path),
            "--no-sweep",
        ])
        xtiming_files = list(tmp_path.glob("*.xtiming"))
        assert len(xtiming_files) >= 1, f"No .xtiming files in {list(tmp_path.iterdir())}"

    def test_xtiming_is_valid_xml(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "pipeline",
            str(FIXTURE),
            "--output-dir", str(tmp_path),
            "--no-sweep",
        ])
        for f in tmp_path.glob("*.xtiming"):
            tree = ET.parse(f)
            assert tree.getroot().tag == "timings"

    def test_pipeline_produces_xvc_file(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "pipeline",
            str(FIXTURE),
            "--output-dir", str(tmp_path),
            "--no-sweep",
        ])
        xvc_files = list(tmp_path.glob("*.xvc"))
        assert len(xvc_files) >= 1, f"No .xvc files in {list(tmp_path.iterdir())}"

    def test_xvc_is_valid_xml(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "pipeline",
            str(FIXTURE),
            "--output-dir", str(tmp_path),
            "--no-sweep",
        ])
        for f in tmp_path.glob("*.xvc"):
            tree = ET.parse(f)
            assert tree.getroot().tag == "valuecurve"

    def test_export_manifest_written(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "pipeline",
            str(FIXTURE),
            "--output-dir", str(tmp_path),
            "--no-sweep",
        ])
        manifest = tmp_path / "export_manifest.json"
        assert manifest.exists(), "export_manifest.json not found"
        data = json.loads(manifest.read_text())
        assert "timing_tracks" in data
        assert "value_curves" in data
