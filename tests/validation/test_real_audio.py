"""End-to-end validation tests using real CC0 audio files.

These tests run the full pipeline: audio analysis -> sequence generation ->
quality validation. They require the full analysis stack (librosa, vamp,
madmom, ffmpeg) and the CC0 music fixtures.

Run:
    python -m tests.validation.download_fixtures  # download tracks first
    pytest tests/validation/test_real_audio.py -v -s

Skip conditions:
- Tracks not downloaded -> skip
- librosa not installed -> skip
- Orchestrator can't run (missing vamp/ffmpeg) -> skip individual tests
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.analyzer.result import HierarchyResult, TimingMark, ValueCurve

CC0_DIR = Path(__file__).parent.parent / "fixtures" / "cc0_music"

TRACKS = {
    "space_ambience": {
        "file": "space_ambience.mp3",
        "genre": "classical",
        "description": "Ambient pads, minimal melody, low energy",
    },
    "nostalgic_piano": {
        "file": "nostalgic_piano.mp3",
        "genre": "classical",
        "description": "Solo piano, clear melodic phrases",
    },
    "maple_leaf_rag": {
        "file": "maple_leaf_rag.mp3",
        "genre": "classical",
        "description": "Ragtime with clear section structure",
    },
    "funshine": {
        "file": "funshine.mp3",
        "genre": "pop",
        "description": "Upbeat pop/funk, drums + bass + melody",
    },
    "black_box_legendary": {
        "file": "black_box_legendary.mp3",
        "genre": "rock",
        "description": "Electronic/cinematic, heavy beats",
    },
}


def _have_fixtures() -> bool:
    if not CC0_DIR.exists():
        return False
    return all((CC0_DIR / t["file"]).exists() for t in TRACKS.values())


def _have_orchestrator() -> bool:
    try:
        import librosa
        from src.analyzer.orchestrator import run_orchestrator
        return True
    except ImportError:
        return False


requires_fixtures = pytest.mark.skipif(
    not _have_fixtures(),
    reason="CC0 music fixtures not downloaded. Run: python -m tests.validation.download_fixtures",
)

requires_orchestrator = pytest.mark.skipif(
    not _have_orchestrator(),
    reason="Full analysis stack not available (librosa/vamp/ffmpeg required)",
)


def _make_layout_xml(path: Path) -> Path:
    """Write a minimal xlights_rgbeffects.xml for testing."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<xlights_rgbeffects>
    <model name="MegaTree" DisplayAs="Poly Line"
           WorldPosX="400" WorldPosY="100" WorldPosZ="0"
           ScaleX="2" ScaleY="4" parm1="16" parm2="100" />
    <model name="ArchLeft" DisplayAs="Arch"
           WorldPosX="100" WorldPosY="300" WorldPosZ="0"
           ScaleX="3" ScaleY="2" parm1="1" parm2="50" />
    <model name="ArchRight" DisplayAs="Arch"
           WorldPosX="700" WorldPosY="300" WorldPosZ="0"
           ScaleX="3" ScaleY="2" parm1="1" parm2="50" />
    <model name="MatrixSign" DisplayAs="Matrix"
           WorldPosX="400" WorldPosY="400" WorldPosZ="0"
           ScaleX="4" ScaleY="2" parm1="32" parm2="16" />
    <model name="CandyCane1" DisplayAs="Single Line"
           WorldPosX="200" WorldPosY="450" WorldPosZ="0"
           ScaleX="1" ScaleY="2" parm1="1" parm2="30" />
    <model name="CandyCane2" DisplayAs="Single Line"
           WorldPosX="600" WorldPosY="450" WorldPosZ="0"
           ScaleX="1" ScaleY="2" parm1="1" parm2="30" />
    <model name="StarTopper" DisplayAs="Star"
           WorldPosX="400" WorldPosY="50" WorldPosZ="0"
           ScaleX="1" ScaleY="1" parm1="5" parm2="10" />
</xlights_rgbeffects>"""
    layout_path = path / "xlights_rgbeffects.xml"
    layout_path.write_text(xml_content)
    return layout_path


def _synthesize_sections(hierarchy: HierarchyResult) -> list[TimingMark]:
    """Create fallback sections when vamp segmenter is unavailable.

    Splits the song into ~30-second chunks with cycling labels, using bar
    boundaries for alignment when available.
    """
    duration_ms = hierarchy.duration_ms
    target_section_ms = 30000
    num_sections = max(2, duration_ms // target_section_ms)
    section_ms = duration_ms // num_sections

    # Snap to bar boundaries if bars are available
    bar_times = []
    if hierarchy.bars and hierarchy.bars.marks:
        bar_times = [m.time_ms for m in hierarchy.bars.marks]

    labels = ["intro", "verse", "chorus", "bridge", "verse", "chorus", "outro"]
    sections: list[TimingMark] = []

    for i in range(num_sections):
        raw_start = i * section_ms
        # Snap to nearest bar
        if bar_times:
            start = min(bar_times, key=lambda b: abs(b - raw_start))
        else:
            start = raw_start

        if i + 1 < num_sections:
            raw_end = (i + 1) * section_ms
            if bar_times:
                end = min(bar_times, key=lambda b: abs(b - raw_end))
            else:
                end = raw_end
        else:
            end = duration_ms

        if end <= start:
            continue

        label = labels[i] if i < len(labels) else labels[i % len(labels)]
        sections.append(TimingMark(
            time_ms=start, confidence=0.7,
            label=label, duration_ms=end - start,
        ))

    return sections


def _synthesize_energy_curve(hierarchy: HierarchyResult) -> dict[str, ValueCurve]:
    """Create a simple energy curve when the orchestrator doesn't produce one.

    Uses beat density as a proxy for energy: windows with more onsets = higher energy.
    """
    duration_ms = hierarchy.duration_ms
    if duration_ms <= 0:
        return {}

    fps = 4
    num_frames = max(1, duration_ms * fps // 1000)
    frame_ms = 1000 / fps

    # Use onset marks to estimate energy per frame
    onset_times: list[int] = []
    if hierarchy.beats and hierarchy.beats.marks:
        onset_times = [m.time_ms for m in hierarchy.beats.marks]

    values: list[int] = []
    window_ms = 4000  # 4-second window for smoothing

    for f in range(num_frames):
        center_ms = f * frame_ms
        count = sum(
            1 for t in onset_times
            if center_ms - window_ms / 2 <= t <= center_ms + window_ms / 2
        )
        # Normalize: assume max ~16 onsets in 4s window (4 Hz beat) = energy 80
        energy = min(100, int(count * 5))
        values.append(max(10, energy))  # floor of 10

    return {
        "full_mix": ValueCurve(
            name="full_mix", stem_source="full_mix",
            fps=fps, values=values,
        ),
    }


@requires_fixtures
@requires_orchestrator
class TestRealAudioValidation:
    """Full pipeline validation with real CC0 music."""

    @pytest.fixture(params=list(TRACKS.keys()))
    def track_info(self, request) -> dict:
        info = TRACKS[request.param].copy()
        info["name"] = request.param
        info["path"] = CC0_DIR / info["file"]
        return info

    def test_analyze_and_validate(self, track_info: dict, tmp_path: Path):
        """Run full pipeline on a real track and validate quality."""
        from src.analyzer.orchestrator import run_orchestrator
        from src.effects.library import load_effect_library
        from src.generator.models import GenerationConfig
        from src.generator.plan import build_plan
        from src.generator.xsq_writer import write_xsq
        from src.grouper.classifier import classify_props, normalize_coords
        from src.grouper.grouper import generate_groups
        from src.grouper.layout import parse_layout
        from src.themes.library import load_theme_library
        from src.validation.report import generate_report, save_report

        audio_path = track_info["path"]
        layout_path = _make_layout_xml(tmp_path)

        # 1. Analyze
        hierarchy = run_orchestrator(str(audio_path), fresh=True)
        assert hierarchy.duration_ms > 0
        assert hierarchy.beats is not None or hierarchy.sections

        # When vamp is unavailable, the orchestrator produces no sections
        # and no energy curves. Synthesize fallback sections so the generator
        # can still produce effects and we can validate the pipeline.
        if not hierarchy.sections:
            hierarchy.sections = _synthesize_sections(hierarchy)
        if not hierarchy.energy_curves:
            hierarchy.energy_curves = _synthesize_energy_curve(hierarchy)

        # 2. Parse layout
        layout = parse_layout(layout_path)
        normalize_coords(layout.props)
        classify_props(layout.props)
        groups = generate_groups(layout.props)

        # 3. Generate sequence
        effect_lib = load_effect_library()
        theme_lib = load_theme_library(effect_library=effect_lib)
        config = GenerationConfig(
            audio_path=audio_path,
            layout_path=layout_path,
            output_dir=tmp_path,
            genre=track_info["genre"],
            occasion="general",
        )
        plan = build_plan(config, hierarchy, layout.props, groups, effect_lib, theme_lib)

        # 4. Write XSQ
        xsq_path = tmp_path / f"{track_info['name']}.xsq"
        write_xsq(plan, xsq_path, hierarchy=hierarchy, audio_path=audio_path)
        assert xsq_path.exists()

        # Validate XSQ is well-formed XML
        tree = ET.parse(xsq_path)
        assert tree.getroot().tag == "xsequence"

        # 5. Validate quality
        report = generate_report(plan, hierarchy)

        # Save report for inspection
        report_path = tmp_path / f"{track_info['name']}_validation.json"
        save_report(report, report_path)

        # Print report for visibility
        print(f"\n{'=' * 60}")
        print(report.summary_table())
        print(f"{'=' * 60}")

        # Assert minimum quality thresholds
        assert report.total_effects > 0, "No effects generated"
        assert report.overall_score >= 20.0, (
            f"{track_info['name']}: overall {report.overall_score} below floor 20"
        )

        # Beat alignment should be reasonable with real audio analysis
        beat_score = next(
            r.score for r in report.scorer_results if r.name == "beat_alignment"
        )
        assert beat_score >= 20.0, (
            f"{track_info['name']}: beat alignment {beat_score} below floor 20"
        )

        # Should cover most of the song
        coverage = next(
            r.score for r in report.scorer_results if r.name == "temporal_coverage"
        )
        assert coverage >= 50.0, (
            f"{track_info['name']}: coverage {coverage} below floor 50"
        )


@requires_fixtures
@requires_orchestrator
class TestRealAudioBaseline:
    """Generate and compare baselines from real audio analysis."""

    def test_generate_all_reports(self, tmp_path: Path):
        """Generate validation reports for all CC0 tracks — summary comparison."""
        from src.analyzer.orchestrator import run_orchestrator
        from src.effects.library import load_effect_library
        from src.generator.models import GenerationConfig
        from src.generator.plan import build_plan
        from src.grouper.classifier import classify_props, normalize_coords
        from src.grouper.grouper import generate_groups
        from src.grouper.layout import parse_layout
        from src.themes.library import load_theme_library
        from src.validation.baseline import (
            Baseline,
            create_baseline_entry,
            save_baseline,
        )
        from src.validation.report import generate_report, save_report

        layout_path = _make_layout_xml(tmp_path)
        effect_lib = load_effect_library()
        theme_lib = load_theme_library(effect_library=effect_lib)
        layout = parse_layout(layout_path)
        normalize_coords(layout.props)
        classify_props(layout.props)
        groups = generate_groups(layout.props)

        entries = []

        for name, info in TRACKS.items():
            audio_path = CC0_DIR / info["file"]
            hierarchy = run_orchestrator(str(audio_path), fresh=True)

            # Fallback sections/energy when vamp unavailable
            if not hierarchy.sections:
                hierarchy.sections = _synthesize_sections(hierarchy)
            if not hierarchy.energy_curves:
                hierarchy.energy_curves = _synthesize_energy_curve(hierarchy)

            config = GenerationConfig(
                audio_path=audio_path,
                layout_path=layout_path,
                output_dir=tmp_path,
                genre=info["genre"],
                occasion="general",
            )
            plan = build_plan(
                config, hierarchy, layout.props, groups, effect_lib, theme_lib,
            )

            report = generate_report(plan, hierarchy)
            save_report(report, tmp_path / f"{name}_report.json")
            entries.append(create_baseline_entry(name, report))

            print(f"\n{'=' * 60}")
            print(report.summary_table())

        # Save combined baseline
        baseline = Baseline(version="1.0-real-audio", entries=entries)
        baseline_path = tmp_path / "real_audio_baseline.json"
        save_baseline(baseline, baseline_path)

        print(f"\n{'=' * 60}")
        print(f"Baseline saved: {baseline_path}")
        print(f"Tracks: {len(entries)}")
        avg_overall = sum(e.overall for e in entries) / len(entries)
        print(f"Average overall score: {avg_overall:.1f}%")
