"""T016: AnalysisRunner — orchestrates all algorithm runs for a single audio file."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import librosa
import numpy as np

from src.analyzer.audio import AudioFile, load
from src.analyzer.algorithms.base import Algorithm
from src.analyzer.result import AnalysisAlgorithm, AnalysisResult, TimingTrack
from src.analyzer.scorer import score_track
from src.analyzer.stems import StemSet


class AnalysisRunner:
    """
    Runs a list of Algorithm instances against a single audio file.

    Usage:
        runner = AnalysisRunner(algorithms=default_algorithms())
        result = runner.run("path/to/song.mp3")
    """

    def __init__(self, algorithms: list[Algorithm]) -> None:
        self._algorithms = algorithms

    def run(
        self,
        audio_path: str,
        progress_callback=None,
        stems: StemSet | None = None,
    ) -> AnalysisResult:
        """
        Load audio once, run all algorithms, score tracks, assemble result.

        progress_callback: optional callable(index, total, name, mark_count)
        stems: optional StemSet from stem separation; when provided, algorithms
               are routed to their preferred_stem array. Falls back to full-mix
               when preferred_stem is "full_mix" or the stem is absent.
        """
        audio, sr, meta = load(audio_path)

        # Estimate overall tempo for metadata
        try:
            tempo_arr, _ = librosa.beat.beat_track(y=audio, sr=sr, hop_length=512)
            estimated_bpm = float(np.atleast_1d(tempo_arr)[0])
        except Exception:
            estimated_bpm = 0.0

        tracks: list[TimingTrack] = []
        used_algorithms: list[AnalysisAlgorithm] = []
        total = len(self._algorithms)

        for idx, algo in enumerate(self._algorithms):
            # Route to stem audio when stems are available
            algo_audio, algo_sr = _select_audio(algo, audio, sr, stems)
            track = algo.run(algo_audio, algo_sr)
            if track is not None:
                track.quality_score = score_track(track)
                track.stem_source = algo.preferred_stem if stems is not None else "full_mix"
                tracks.append(track)
                used_algorithms.append(algo.metadata())

            if progress_callback:
                progress_callback(
                    idx + 1,
                    total,
                    algo.name,
                    track.mark_count if track else 0,
                )

        stem_cache_str: str | None = None
        if stems is not None:
            # Record stem cache path relative to source file if possible
            stems_dir = Path(meta.path).parent / ".stems"
            if stems_dir.exists():
                stem_cache_str = str(stems_dir)

        return AnalysisResult(
            schema_version="1.0",
            source_file=meta.path,
            filename=meta.filename,
            duration_ms=meta.duration_ms,
            sample_rate=meta.sample_rate,
            estimated_tempo_bpm=round(estimated_bpm, 2),
            run_timestamp=datetime.now(timezone.utc).isoformat(),
            algorithms=used_algorithms,
            timing_tracks=tracks,
            stem_separation=stems is not None,
            stem_cache=stem_cache_str,
        )


def _select_audio(
    algo: Algorithm,
    full_mix: np.ndarray,
    full_mix_sr: int,
    stems: StemSet | None,
) -> tuple[np.ndarray, int]:
    """
    Return the (audio, sample_rate) pair the algorithm should use.

    When stems is None or the algorithm prefers "full_mix", returns the full-mix
    array. Otherwise returns the matching stem array, resampled to full_mix_sr
    when the stem sample rate differs.
    """
    if stems is None or algo.preferred_stem == "full_mix":
        return full_mix, full_mix_sr

    stem_arr = stems.get(algo.preferred_stem)
    if stem_arr is None:
        return full_mix, full_mix_sr

    stem_sr = stems.sample_rate
    if stem_sr != full_mix_sr:
        import librosa as _librosa
        stem_arr = _librosa.resample(stem_arr, orig_sr=stem_sr, target_sr=full_mix_sr)
        stem_sr = full_mix_sr

    return stem_arr, stem_sr


def default_algorithms(
    include_vamp: bool = True,
    include_madmom: bool = True,
) -> list[Algorithm]:
    """
    Return the full list of algorithm instances.
    Algorithms that require unavailable libraries are silently omitted.
    """
    algorithms: list[Algorithm] = []

    # --- librosa algorithms (always available) ---
    from src.analyzer.algorithms.librosa_beats import LibrosaBeatAlgorithm, LibrosaBarAlgorithm
    from src.analyzer.algorithms.librosa_bands import (
        LibrosaBassAlgorithm,
        LibrosaMidAlgorithm,
        LibrosaTrebleAlgorithm,
    )
    from src.analyzer.algorithms.librosa_hpss import LibrosaDrumsAlgorithm, LibrosaHarmonicAlgorithm
    from src.analyzer.algorithms.librosa_onset import LibrosaOnsetAlgorithm

    algorithms += [
        LibrosaBeatAlgorithm(),
        LibrosaBarAlgorithm(),
        LibrosaOnsetAlgorithm(),
        LibrosaBassAlgorithm(),
        LibrosaMidAlgorithm(),
        LibrosaTrebleAlgorithm(),
        LibrosaDrumsAlgorithm(),
        LibrosaHarmonicAlgorithm(),
    ]

    # --- madmom algorithms (optional) ---
    if include_madmom:
        try:
            from src.analyzer.algorithms.madmom_beat import (
                MadmomBeatAlgorithm,
                MadmomDownbeatAlgorithm,
            )
            algorithms += [MadmomBeatAlgorithm(), MadmomDownbeatAlgorithm()]
        except ImportError:
            print(
                "INFO: madmom not available — madmom_beats and madmom_downbeats skipped.",
                file=sys.stderr,
            )

    # --- Vamp algorithms (optional) ---
    if include_vamp:
        try:
            from src.analyzer.algorithms.vamp_beats import QMBeatAlgorithm, QMBarAlgorithm, BeatRootAlgorithm
            from src.analyzer.algorithms.vamp_onsets import (
                QMOnsetComplexAlgorithm,
                QMOnsetHFCAlgorithm,
                QMOnsetPhaseAlgorithm,
            )
            from src.analyzer.algorithms.vamp_structure import QMSegmenterAlgorithm, QMTempoAlgorithm
            from src.analyzer.algorithms.vamp_pitch import PYINNotesAlgorithm, PYINPitchChangesAlgorithm
            from src.analyzer.algorithms.vamp_harmony import ChordinoAlgorithm, NNLSChromaAlgorithm

            algorithms += [
                QMBeatAlgorithm(),
                QMBarAlgorithm(),
                BeatRootAlgorithm(),
                QMOnsetComplexAlgorithm(),
                QMOnsetHFCAlgorithm(),
                QMOnsetPhaseAlgorithm(),
                QMSegmenterAlgorithm(),
                QMTempoAlgorithm(),
                PYINNotesAlgorithm(),
                PYINPitchChangesAlgorithm(),
                ChordinoAlgorithm(),
                NNLSChromaAlgorithm(),
            ]
        except ImportError:
            print(
                "INFO: vamp Python package not available — Vamp plugin algorithms skipped.",
                file=sys.stderr,
            )

    return algorithms
