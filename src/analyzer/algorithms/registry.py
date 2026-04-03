"""Centralized algorithm registry — single source of truth for all algorithm discovery.

Instead of duplicating try/import/except blocks in runner.py, vamp_runner.py, and
orchestrator.py, all algorithm classes are registered here. Consumers call
get_algorithms() or get_algorithm_map() to discover what's available.
"""
from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.analyzer.algorithms.base import Algorithm


# Each entry: (import_path, class_name, registry_name, library)
# registry_name is the canonical name used by vamp_runner protocol
_ALGORITHM_DEFS: list[tuple[str, str, str, str]] = [
    # ── librosa (always available) ──────────────────────────────────────────
    ("src.analyzer.algorithms.librosa_beats", "LibrosaBeatAlgorithm", "librosa_beats", "librosa"),
    ("src.analyzer.algorithms.librosa_beats", "LibrosaBarAlgorithm", "librosa_bars", "librosa"),
    ("src.analyzer.algorithms.librosa_onset", "LibrosaOnsetAlgorithm", "librosa_onsets", "librosa"),
    ("src.analyzer.algorithms.librosa_bands", "LibrosaBassAlgorithm", "librosa_bass", "librosa"),
    ("src.analyzer.algorithms.librosa_bands", "LibrosaMidAlgorithm", "librosa_mid", "librosa"),
    ("src.analyzer.algorithms.librosa_bands", "LibrosaTrebleAlgorithm", "librosa_treble", "librosa"),
    ("src.analyzer.algorithms.librosa_hpss", "LibrosaDrumsAlgorithm", "librosa_drums", "librosa"),
    ("src.analyzer.algorithms.librosa_hpss", "LibrosaHarmonicAlgorithm", "librosa_harmonic", "librosa"),
    # ── madmom ──────────────────────────────────────────────────────────────
    ("src.analyzer.algorithms.madmom_beat", "MadmomBeatAlgorithm", "madmom_beats", "madmom"),
    ("src.analyzer.algorithms.madmom_beat", "MadmomDownbeatAlgorithm", "madmom_downbeats", "madmom"),
    # ── vamp: beats ─────────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_beats", "QMBeatAlgorithm", "qm_beats", "vamp"),
    ("src.analyzer.algorithms.vamp_beats", "QMBarAlgorithm", "qm_bars", "vamp"),
    ("src.analyzer.algorithms.vamp_beats", "BeatRootAlgorithm", "beatroot", "vamp"),
    # ── vamp: onsets ────────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_onsets", "QMOnsetComplexAlgorithm", "qm_onsets_complex", "vamp"),
    ("src.analyzer.algorithms.vamp_onsets", "QMOnsetHFCAlgorithm", "qm_onsets_hfc", "vamp"),
    ("src.analyzer.algorithms.vamp_onsets", "QMOnsetPhaseAlgorithm", "qm_onsets_phase", "vamp"),
    # ── vamp: structure ─────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_structure", "QMSegmenterAlgorithm", "qm_segments", "vamp"),
    ("src.analyzer.algorithms.vamp_structure", "QMTempoAlgorithm", "qm_tempo", "vamp"),
    # ── vamp: pitch ─────────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_pitch", "PYINNotesAlgorithm", "pyin_notes", "vamp"),
    ("src.analyzer.algorithms.vamp_pitch", "PYINPitchChangesAlgorithm", "pyin_pitch_changes", "vamp"),
    # ── vamp: harmony ───────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_harmony", "ChordinoAlgorithm", "chordino_chords", "vamp"),
    ("src.analyzer.algorithms.vamp_harmony", "NNLSChromaAlgorithm", "nnls_chroma", "vamp"),
    # ── vamp: segmentation ──────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_segmentation", "SegmentinoAlgorithm", "segmentino", "vamp"),
    # ── vamp: aubio ─────────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_aubio", "AubioOnsetAlgorithm", "aubio_onset", "vamp"),
    ("src.analyzer.algorithms.vamp_aubio", "AubioTempoAlgorithm", "aubio_tempo", "vamp"),
    ("src.analyzer.algorithms.vamp_aubio", "AubioNotesAlgorithm", "aubio_notes", "vamp"),
    # ── vamp: BBC ───────────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_bbc", "BBCEnergyAlgorithm", "bbc_energy", "vamp"),
    ("src.analyzer.algorithms.vamp_bbc", "BBCSpectralFluxAlgorithm", "bbc_spectral_flux", "vamp"),
    ("src.analyzer.algorithms.vamp_bbc", "BBCPeaksAlgorithm", "bbc_peaks", "vamp"),
    ("src.analyzer.algorithms.vamp_bbc", "BBCRhythmAlgorithm", "bbc_rhythm", "vamp"),
    # ── vamp: extra ─────────────────────────────────────────────────────────
    ("src.analyzer.algorithms.vamp_extra", "QMKeyAlgorithm", "qm_key", "vamp"),
    ("src.analyzer.algorithms.vamp_extra", "QMTranscriptionAlgorithm", "qm_transcription", "vamp"),
    ("src.analyzer.algorithms.vamp_extra", "SilvetNotesAlgorithm", "silvet_notes", "vamp"),
    ("src.analyzer.algorithms.vamp_extra", "PercussionOnsetsAlgorithm", "percussion_onsets", "vamp"),
    ("src.analyzer.algorithms.vamp_extra", "AmplitudeFollowerAlgorithm", "amplitude_follower", "vamp"),
    ("src.analyzer.algorithms.vamp_extra", "TempogramAlgorithm", "tempogram", "vamp"),
]

# Aliases for backward compatibility
_ALIASES: dict[str, str] = {
    "beatroot_beats": "beatroot",
}


def _try_import(module_path: str, class_name: str) -> type | None:
    """Import a class from a module, returning None on ImportError."""
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except (ImportError, AttributeError):
        return None


def get_algorithm_map(
    libraries: set[str] | None = None,
) -> dict[str, type]:
    """Return {registry_name: AlgorithmClass} for available algorithms.

    Args:
        libraries: If provided, only include algorithms from these libraries
                   (e.g. {"vamp", "madmom"}). None means all.
    """
    result: dict[str, type] = {}
    failed_modules: set[str] = set()

    for module_path, class_name, reg_name, library in _ALGORITHM_DEFS:
        if libraries is not None and library not in libraries:
            continue
        if module_path in failed_modules:
            continue

        cls = _try_import(module_path, class_name)
        if cls is None:
            failed_modules.add(module_path)
            continue
        result[reg_name] = cls

    # Add aliases
    for alias, canonical in _ALIASES.items():
        if canonical in result and alias not in result:
            result[alias] = result[canonical]

    return result


def get_algorithms(
    include_vamp: bool = True,
    include_madmom: bool = True,
) -> list[Algorithm]:
    """Return instantiated Algorithm objects for available algorithms.

    This is the replacement for runner.default_algorithms().
    """
    libraries: set[str] = {"librosa"}
    if include_vamp:
        libraries.add("vamp")
    if include_madmom:
        libraries.add("madmom")

    algo_map = get_algorithm_map(libraries)

    if include_vamp:
        has_vamp = any(
            reg_name in algo_map
            for _, _, reg_name, lib in _ALGORITHM_DEFS
            if lib == "vamp"
        )
        if not has_vamp:
            print(
                "INFO: vamp Python package not available — Vamp plugin algorithms skipped.",
                file=sys.stderr,
            )

    if include_madmom:
        has_madmom = any(
            reg_name in algo_map
            for _, _, reg_name, lib in _ALGORITHM_DEFS
            if lib == "madmom"
        )
        if not has_madmom:
            print(
                "INFO: madmom not available — madmom_beats and madmom_downbeats skipped.",
                file=sys.stderr,
            )

    return [cls() for cls in algo_map.values()]


def get_available_libraries() -> dict[str, bool]:
    """Probe which algorithm libraries are importable."""
    algo_map = get_algorithm_map()
    return {
        lib: any(
            reg_name in algo_map
            for _, _, reg_name, lib_ in _ALGORITHM_DEFS
            if lib_ == lib
        )
        for lib in ("librosa", "vamp", "madmom")
    }
