"""Synthetic song scenarios for validation testing.

Each scenario creates a realistic HierarchyResult that simulates a specific
type of song (pop, ballad, high-energy, etc.) with known musical structure.
No audio files needed — the scenarios provide pre-built analysis data that
the generator pipeline consumes directly.

This gives us:
- Known ground truth (we control the structure)
- Deterministic, reproducible results
- No audio library dependencies
- Songs that exercise different aspects of the generator
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.analyzer.result import HierarchyResult, TimingMark, TimingTrack, ValueCurve
from src.generator.models import GenerationConfig
from src.grouper.grouper import PowerGroup
from src.grouper.layout import Prop


@dataclass
class ValidationScenario:
    """A complete test scenario for validation."""

    name: str
    description: str
    hierarchy: HierarchyResult
    props: list[Prop]
    groups: list[PowerGroup]
    config_overrides: dict[str, Any] = field(default_factory=dict)

    def make_config(self, tmp_dir: Path) -> GenerationConfig:
        """Create a GenerationConfig for this scenario."""
        defaults = {
            "audio_path": tmp_dir / f"{self.name}.mp3",
            "layout_path": tmp_dir / "layout.xml",
            "genre": "pop",
            "occasion": "general",
        }
        defaults.update(self.config_overrides)
        return GenerationConfig(**defaults)


# ── Shared Fixtures ──────────────────────────────────────────────────────────


def _standard_props() -> list[Prop]:
    """A realistic 8-prop layout with varied types and positions."""
    return [
        Prop(name="MegaTree", display_as="Poly Line",
             world_x=400, world_y=100, world_z=0,
             scale_x=2, scale_y=4, parm1=16, parm2=100,
             sub_models=[], pixel_count=1600,
             norm_x=0.5, norm_y=0.2, aspect_ratio=0.5),
        Prop(name="ArchLeft", display_as="Arch",
             world_x=100, world_y=300, world_z=0,
             scale_x=3, scale_y=2, parm1=1, parm2=50,
             sub_models=[], pixel_count=50,
             norm_x=0.12, norm_y=0.6, aspect_ratio=1.5),
        Prop(name="ArchRight", display_as="Arch",
             world_x=700, world_y=300, world_z=0,
             scale_x=3, scale_y=2, parm1=1, parm2=50,
             sub_models=[], pixel_count=50,
             norm_x=0.88, norm_y=0.6, aspect_ratio=1.5),
        Prop(name="MatrixSign", display_as="Matrix",
             world_x=400, world_y=400, world_z=0,
             scale_x=4, scale_y=2, parm1=32, parm2=16,
             sub_models=[], pixel_count=512,
             norm_x=0.5, norm_y=0.8, aspect_ratio=2.0),
        Prop(name="CandyCaneL1", display_as="Single Line",
             world_x=200, world_y=450, world_z=0,
             scale_x=1, scale_y=2, parm1=1, parm2=30,
             sub_models=[], pixel_count=30,
             norm_x=0.25, norm_y=0.9, aspect_ratio=0.5),
        Prop(name="CandyCaneR1", display_as="Single Line",
             world_x=600, world_y=450, world_z=0,
             scale_x=1, scale_y=2, parm1=1, parm2=30,
             sub_models=[], pixel_count=30,
             norm_x=0.75, norm_y=0.9, aspect_ratio=0.5),
        Prop(name="MiniTreeL", display_as="Poly Line",
             world_x=50, world_y=400, world_z=0,
             scale_x=1, scale_y=1, parm1=4, parm2=25,
             sub_models=[], pixel_count=100,
             norm_x=0.06, norm_y=0.8, aspect_ratio=1.0),
        Prop(name="StarTopper", display_as="Star",
             world_x=400, world_y=50, world_z=0,
             scale_x=1, scale_y=1, parm1=5, parm2=10,
             sub_models=[], pixel_count=50,
             norm_x=0.5, norm_y=0.1, aspect_ratio=1.0),
    ]


def _standard_groups() -> list[PowerGroup]:
    """Power groups covering all 8 tiers for realistic validation."""
    return [
        PowerGroup(
            name="01_BASE_All", tier=1,
            members=["MegaTree", "ArchLeft", "ArchRight", "MatrixSign",
                      "CandyCaneL1", "CandyCaneR1", "MiniTreeL", "StarTopper"],
        ),
        PowerGroup(name="02_GEO_Left", tier=2, members=["ArchLeft", "CandyCaneL1", "MiniTreeL"]),
        PowerGroup(name="02_GEO_Right", tier=2, members=["ArchRight", "CandyCaneR1"]),
        PowerGroup(name="03_TYPE_Arches", tier=3, members=["ArchLeft", "ArchRight"]),
        PowerGroup(name="04_BEAT_Chase", tier=4, members=["CandyCaneL1", "CandyCaneR1"]),
        PowerGroup(name="05_TEX_HiDens", tier=5, members=["MegaTree", "MatrixSign"]),
        PowerGroup(name="06_PROP_CandyCanes", tier=6, members=["CandyCaneL1", "CandyCaneR1"]),
        PowerGroup(name="07_COMP_Arches", tier=7, members=["ArchLeft", "ArchRight"]),
        PowerGroup(name="08_HERO_MegaTree", tier=8, members=["MegaTree"]),
    ]


# ── Energy Curve Builders ────────────────────────────────────────────────────


def _build_energy_curve(
    duration_ms: int,
    fps: int,
    profile: list[tuple[float, float]],
) -> ValueCurve:
    """Build an energy curve from a piecewise-linear profile.

    profile: list of (time_fraction 0-1, energy 0-100) control points.
    Interpolates linearly between them.
    """
    num_frames = max(1, duration_ms * fps // 1000)
    values: list[int] = []

    for frame_idx in range(num_frames):
        t = frame_idx / max(1, num_frames - 1)
        # Find surrounding control points
        energy = profile[0][1]
        for i in range(len(profile) - 1):
            t0, e0 = profile[i]
            t1, e1 = profile[i + 1]
            if t0 <= t <= t1:
                frac = (t - t0) / max(0.001, t1 - t0)
                energy = e0 + (e1 - e0) * frac
                break
        else:
            energy = profile[-1][1]
        values.append(max(0, min(100, int(energy))))

    return ValueCurve(
        name="full_mix", stem_source="full_mix", fps=fps, values=values,
    )


def _build_beats(duration_ms: int, bpm: float) -> TimingTrack:
    """Generate a beat track at the given BPM."""
    interval_ms = int(60000 / bpm)
    marks = []
    t = 0
    beat_num = 0
    while t < duration_ms:
        marks.append(TimingMark(
            time_ms=t, confidence=0.95,
            label=str((beat_num % 4) + 1),
        ))
        t += interval_ms
        beat_num += 1
    return TimingTrack(
        name="beats", algorithm_name="librosa_beats",
        element_type="beat", marks=marks, quality_score=0.85,
    )


def _build_bars(duration_ms: int, bpm: float) -> TimingTrack:
    """Generate a bar track (every 4 beats)."""
    bar_interval_ms = int(4 * 60000 / bpm)
    marks = [
        TimingMark(time_ms=i * bar_interval_ms, confidence=0.90)
        for i in range(duration_ms // bar_interval_ms)
    ]
    return TimingTrack(
        name="bars", algorithm_name="librosa_beats",
        element_type="bar", marks=marks, quality_score=0.80,
    )


# ── Scenario Builders ───────────────────────────────────────────────────────


def build_pop_anthem() -> ValidationScenario:
    """Classic pop song: intro -> verse -> chorus -> verse -> chorus -> bridge -> chorus -> outro.

    ~3:30, 128 BPM, clear energy arc (builds to choruses, drops at bridge).
    Tests: theme variety, energy tracking, tier escalation on choruses.
    """
    duration_ms = 210000  # 3:30
    bpm = 128.0
    fps = 4

    sections = [
        TimingMark(time_ms=0,      confidence=1.0, label="intro",   duration_ms=15000),
        TimingMark(time_ms=15000,  confidence=1.0, label="verse",   duration_ms=30000),
        TimingMark(time_ms=45000,  confidence=1.0, label="chorus",  duration_ms=30000),
        TimingMark(time_ms=75000,  confidence=1.0, label="verse",   duration_ms=30000),
        TimingMark(time_ms=105000, confidence=1.0, label="chorus",  duration_ms=30000),
        TimingMark(time_ms=135000, confidence=1.0, label="bridge",  duration_ms=20000),
        TimingMark(time_ms=155000, confidence=1.0, label="chorus",  duration_ms=35000),
        TimingMark(time_ms=190000, confidence=1.0, label="outro",   duration_ms=20000),
    ]

    energy_profile = [
        (0.0, 20),    # intro: quiet
        (0.07, 35),   # intro builds
        (0.07, 45),   # verse start
        (0.21, 55),   # verse builds
        (0.21, 75),   # chorus hit
        (0.36, 85),   # chorus peak
        (0.36, 45),   # verse 2 start
        (0.50, 60),   # verse 2 builds
        (0.50, 80),   # chorus 2 hit
        (0.64, 90),   # chorus 2 peak
        (0.64, 35),   # bridge: drop
        (0.74, 40),   # bridge stays low
        (0.74, 85),   # final chorus: big hit
        (0.90, 95),   # final chorus peak
        (0.90, 50),   # outro starts
        (1.0, 10),    # outro fades
    ]

    # Impacts at chorus entries and bridge resolution
    impacts = [
        TimingMark(time_ms=45000, confidence=1.0),   # chorus 1
        TimingMark(time_ms=105000, confidence=1.0),  # chorus 2
        TimingMark(time_ms=155000, confidence=1.0),  # final chorus
    ]

    hierarchy = HierarchyResult(
        schema_version="2.0.0",
        source_file="pop_anthem.mp3",
        source_hash="pop_anthem_abc123",
        duration_ms=duration_ms,
        estimated_bpm=bpm,
        sections=sections,
        beats=_build_beats(duration_ms, bpm),
        bars=_build_bars(duration_ms, bpm),
        energy_curves={"full_mix": _build_energy_curve(duration_ms, fps, energy_profile)},
        energy_impacts=impacts,
    )

    return ValidationScenario(
        name="pop_anthem",
        description="Classic pop song with verse/chorus/bridge structure, 128 BPM",
        hierarchy=hierarchy,
        props=_standard_props(),
        groups=_standard_groups(),
        config_overrides={"genre": "pop", "occasion": "general"},
    )


def build_christmas_ballad() -> ValidationScenario:
    """Slow Christmas ballad: intro -> verse -> verse -> chorus -> verse -> chorus -> outro.

    ~4:00, 72 BPM, gentle energy arc, ethereal mood dominant.
    Tests: theme coherence with low energy, occasion-specific themes.
    """
    duration_ms = 240000  # 4:00
    bpm = 72.0
    fps = 4

    sections = [
        TimingMark(time_ms=0,      confidence=1.0, label="intro",   duration_ms=20000),
        TimingMark(time_ms=20000,  confidence=1.0, label="verse",   duration_ms=40000),
        TimingMark(time_ms=60000,  confidence=1.0, label="verse",   duration_ms=40000),
        TimingMark(time_ms=100000, confidence=1.0, label="chorus",  duration_ms=35000),
        TimingMark(time_ms=135000, confidence=1.0, label="verse",   duration_ms=40000),
        TimingMark(time_ms=175000, confidence=1.0, label="chorus",  duration_ms=40000),
        TimingMark(time_ms=215000, confidence=1.0, label="outro",   duration_ms=25000),
    ]

    energy_profile = [
        (0.0, 10),    # intro: very quiet
        (0.08, 15),
        (0.08, 20),   # verse 1
        (0.25, 25),
        (0.25, 25),   # verse 2
        (0.42, 30),
        (0.42, 45),   # chorus 1: gentle lift
        (0.56, 55),
        (0.56, 25),   # verse 3: back down
        (0.73, 35),
        (0.73, 50),   # chorus 2: slightly bigger
        (0.90, 60),
        (0.90, 20),   # outro: gentle fade
        (1.0, 5),
    ]

    impacts = [
        TimingMark(time_ms=100000, confidence=0.8),  # chorus 1
        TimingMark(time_ms=175000, confidence=0.8),  # chorus 2
    ]

    hierarchy = HierarchyResult(
        schema_version="2.0.0",
        source_file="christmas_ballad.mp3",
        source_hash="xmas_ballad_def456",
        duration_ms=duration_ms,
        estimated_bpm=bpm,
        sections=sections,
        beats=_build_beats(duration_ms, bpm),
        bars=_build_bars(duration_ms, bpm),
        energy_curves={"full_mix": _build_energy_curve(duration_ms, fps, energy_profile)},
        energy_impacts=impacts,
    )

    return ValidationScenario(
        name="christmas_ballad",
        description="Slow Christmas ballad, 72 BPM, gentle energy arc",
        hierarchy=hierarchy,
        props=_standard_props(),
        groups=_standard_groups(),
        config_overrides={"genre": "pop", "occasion": "christmas"},
    )


def build_edm_banger() -> ValidationScenario:
    """High-energy EDM track: intro -> build -> drop -> break -> build -> drop -> outro.

    ~3:00, 140 BPM, extreme dynamic range, aggressive mood dominant.
    Tests: tier utilization under high energy, variety under aggressive mood.
    """
    duration_ms = 180000  # 3:00
    bpm = 140.0
    fps = 4

    sections = [
        TimingMark(time_ms=0,      confidence=1.0, label="intro",    duration_ms=16000),
        TimingMark(time_ms=16000,  confidence=1.0, label="build",    duration_ms=16000),
        TimingMark(time_ms=32000,  confidence=1.0, label="drop",     duration_ms=32000),
        TimingMark(time_ms=64000,  confidence=1.0, label="break",    duration_ms=16000),
        TimingMark(time_ms=80000,  confidence=1.0, label="build",    duration_ms=16000),
        TimingMark(time_ms=96000,  confidence=1.0, label="drop",     duration_ms=48000),
        TimingMark(time_ms=144000, confidence=1.0, label="break",    duration_ms=16000),
        TimingMark(time_ms=160000, confidence=1.0, label="outro",    duration_ms=20000),
    ]

    energy_profile = [
        (0.0, 30),     # intro
        (0.09, 40),
        (0.09, 45),    # build 1: ramp up
        (0.18, 75),
        (0.18, 95),    # drop 1: massive
        (0.36, 90),
        (0.36, 25),    # break: dramatic contrast
        (0.44, 30),
        (0.44, 50),    # build 2: ramp up again
        (0.53, 80),
        (0.53, 100),   # drop 2: even bigger
        (0.80, 95),
        (0.80, 30),    # break 2
        (0.89, 25),
        (0.89, 20),    # outro
        (1.0, 5),
    ]

    impacts = [
        TimingMark(time_ms=32000, confidence=1.0),   # drop 1
        TimingMark(time_ms=48000, confidence=0.9),   # mid-drop impact
        TimingMark(time_ms=96000, confidence=1.0),   # drop 2
        TimingMark(time_ms=120000, confidence=0.9),  # mid-drop 2 impact
    ]

    hierarchy = HierarchyResult(
        schema_version="2.0.0",
        source_file="edm_banger.mp3",
        source_hash="edm_banger_ghi789",
        duration_ms=duration_ms,
        estimated_bpm=bpm,
        sections=sections,
        beats=_build_beats(duration_ms, bpm),
        bars=_build_bars(duration_ms, bpm),
        energy_curves={"full_mix": _build_energy_curve(duration_ms, fps, energy_profile)},
        energy_impacts=impacts,
    )

    return ValidationScenario(
        name="edm_banger",
        description="High-energy EDM with build/drop structure, 140 BPM",
        hierarchy=hierarchy,
        props=_standard_props(),
        groups=_standard_groups(),
        config_overrides={"genre": "rock", "occasion": "general"},
    )


def build_orchestral_piece() -> ValidationScenario:
    """Classical/orchestral piece: slow build to climax then resolution.

    ~5:00, 80 BPM, wide dynamic range, structural/dark mood.
    Tests: handling long sections, gradual energy changes, tier restraint.
    """
    duration_ms = 300000  # 5:00
    bpm = 80.0
    fps = 4

    sections = [
        TimingMark(time_ms=0,      confidence=1.0, label="intro",       duration_ms=40000),
        TimingMark(time_ms=40000,  confidence=1.0, label="exposition",  duration_ms=60000),
        TimingMark(time_ms=100000, confidence=1.0, label="development", duration_ms=60000),
        TimingMark(time_ms=160000, confidence=1.0, label="climax",      duration_ms=40000),
        TimingMark(time_ms=200000, confidence=1.0, label="resolution",  duration_ms=60000),
        TimingMark(time_ms=260000, confidence=1.0, label="coda",        duration_ms=40000),
    ]

    energy_profile = [
        (0.0, 10),     # intro: very quiet
        (0.13, 20),
        (0.13, 25),    # exposition: gentle
        (0.33, 40),
        (0.33, 45),    # development: growing
        (0.53, 70),
        (0.53, 85),    # climax: peak
        (0.67, 95),
        (0.67, 50),    # resolution: winding down
        (0.87, 30),
        (0.87, 20),    # coda: gentle close
        (1.0, 5),
    ]

    impacts = [
        TimingMark(time_ms=160000, confidence=1.0),  # climax entry
        TimingMark(time_ms=180000, confidence=0.8),  # climax peak
    ]

    hierarchy = HierarchyResult(
        schema_version="2.0.0",
        source_file="orchestral_piece.mp3",
        source_hash="orchestral_jkl012",
        duration_ms=duration_ms,
        estimated_bpm=bpm,
        sections=sections,
        beats=_build_beats(duration_ms, bpm),
        bars=_build_bars(duration_ms, bpm),
        energy_curves={"full_mix": _build_energy_curve(duration_ms, fps, energy_profile)},
        energy_impacts=impacts,
    )

    return ValidationScenario(
        name="orchestral_piece",
        description="Classical orchestral piece with exposition/climax/resolution, 80 BPM",
        hierarchy=hierarchy,
        props=_standard_props(),
        groups=_standard_groups(),
        config_overrides={"genre": "classical", "occasion": "general"},
    )


def build_short_jingle() -> ValidationScenario:
    """Very short jingle/bumper: just intro -> hook -> tag.

    ~0:45, 110 BPM. Edge case: very few sections, short duration.
    Tests: handling short songs gracefully.
    """
    duration_ms = 45000  # 0:45
    bpm = 110.0
    fps = 4

    sections = [
        TimingMark(time_ms=0,     confidence=1.0, label="intro", duration_ms=10000),
        TimingMark(time_ms=10000, confidence=1.0, label="hook",  duration_ms=25000),
        TimingMark(time_ms=35000, confidence=1.0, label="tag",   duration_ms=10000),
    ]

    energy_profile = [
        (0.0, 30),
        (0.22, 50),
        (0.22, 70),
        (0.78, 80),
        (0.78, 40),
        (1.0, 15),
    ]

    impacts = [
        TimingMark(time_ms=10000, confidence=1.0),  # hook entry
    ]

    hierarchy = HierarchyResult(
        schema_version="2.0.0",
        source_file="short_jingle.mp3",
        source_hash="jingle_mno345",
        duration_ms=duration_ms,
        estimated_bpm=bpm,
        sections=sections,
        beats=_build_beats(duration_ms, bpm),
        bars=_build_bars(duration_ms, bpm),
        energy_curves={"full_mix": _build_energy_curve(duration_ms, fps, energy_profile)},
        energy_impacts=impacts,
    )

    return ValidationScenario(
        name="short_jingle",
        description="Very short 45-second jingle, edge case for short songs",
        hierarchy=hierarchy,
        props=_standard_props(),
        groups=_standard_groups(),
        config_overrides={"genre": "pop", "occasion": "general"},
    )


# ── Scenario Registry ───────────────────────────────────────────────────────


ALL_SCENARIOS = {
    "pop_anthem": build_pop_anthem,
    "christmas_ballad": build_christmas_ballad,
    "edm_banger": build_edm_banger,
    "orchestral_piece": build_orchestral_piece,
    "short_jingle": build_short_jingle,
}


def load_all_scenarios() -> list[ValidationScenario]:
    """Build and return all validation scenarios."""
    return [builder() for builder in ALL_SCENARIOS.values()]
