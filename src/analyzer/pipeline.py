"""Automated end-to-end analysis pipeline (US7)."""
from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from src.analyzer.conditioning import condition_curve
from src.analyzer.result import (
    ConditionedCurve,
    ExportManifest,
    TimingTrackExport,
)
from src.analyzer.stem_inspector import inspect_stems, interactive_review
from src.analyzer.xtiming import write_timing_tracks
from src.analyzer.xvc_export import XvcExporter

logger = logging.getLogger(__name__)


def run_pipeline(
    audio_path: str,
    stem_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    fps: int = 20,
    top_n: int = 5,
    interactive: bool = False,
    no_sweep: bool = False,
) -> ExportManifest:
    """
    Full pipeline: inspect → (optional review) → analyze → condition → export.

    Returns ExportManifest with paths to all output files.
    Gracefully degrades to full-mix-only analysis when no stems are available.
    """
    audio_path_p = Path(audio_path)
    stem_dir_p = Path(stem_dir) if stem_dir else None

    if output_dir is None:
        out_dir = audio_path_p.parent / "analysis"
    else:
        out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []

    # ── 1. Stem inspection ────────────────────────────────────────────────────
    try:
        stem_metrics = inspect_stems(str(audio_path_p), stem_dir=stem_dir_p)
    except Exception as exc:
        warnings.append(f"Stem inspection failed: {exc} — using full_mix only")
        stem_metrics = []

    stems_used = ["full_mix"]

    if stem_metrics:
        if interactive:
            selection = interactive_review(stem_metrics)
        else:
            from src.analyzer.stem_inspector import interactive_review as _ir
            selection = _ir(stem_metrics, auto_accept=True)
        stems_used = selection.kept_stems or ["full_mix"]

    # ── 2. Audio analysis (run existing analyzer) ─────────────────────────────
    from src.analyzer.runner import AnalysisRunner, default_algorithms

    try:
        runner = AnalysisRunner(default_algorithms())
        analysis_result = runner.run(str(audio_path_p))
    except Exception as exc:
        raise RuntimeError(f"Analysis failed: {exc}") from exc

    timing_tracks = analysis_result.timing_tracks
    if top_n and top_n > 0:
        timing_tracks = sorted(
            timing_tracks, key=lambda t: t.quality_score, reverse=True
        )[:top_n]

    # ── 3. Interaction analysis ───────────────────────────────────────────────
    interaction_result = None
    if len(stems_used) > 1:
        try:
            import librosa
            stem_audio: dict[str, np.ndarray] = {}
            for stem_name in stems_used:
                if stem_name == "full_mix":
                    y, _ = librosa.load(str(audio_path_p), mono=True)
                    stem_audio["full_mix"] = y
                elif stem_dir_p:
                    stem_file = stem_dir_p / f"{stem_name}.mp3"
                    if stem_file.exists():
                        y, _ = librosa.load(str(stem_file), mono=True)
                        stem_audio[stem_name] = y
            if len(stem_audio) > 1:
                from src.analyzer.interaction import analyze_interactions
                sr = 22050
                interaction_result = analyze_interactions(stem_audio, sr, fps=fps)
                analysis_result = analysis_result.__class__(
                    **{**analysis_result.__dict__, "interaction_result": interaction_result}
                )
        except Exception as exc:
            warnings.append(f"Interaction analysis failed: {exc}")

    # ── 4. Condition and export value curves ──────────────────────────────────
    exporter = XvcExporter()
    xvc_exports = []

    for track in timing_tracks:
        if not track.marks:
            continue
        try:
            # Build a simple onset-density curve from mark positions
            duration_ms = track.marks[-1].time_ms + 50
            n_frames = max(1, round(duration_ms * fps / 1000))
            raw = np.zeros(n_frames)
            source_sr = 22050
            source_hop = source_sr // fps
            for mark in track.marks:
                fi = min(int(mark.time_ms * fps / 1000), n_frames - 1)
                raw[fi] += 1.0
            stem = getattr(track, "stem_source", None) or "full_mix"
            curve = condition_curve(
                raw, source_sr, source_hop, fps,
                name=track.name, stem=stem, feature=track.element_type,
            )
            if curve.is_flat:
                warnings.append(f"Flat curve for {track.name} — may not animate")
            xvc_exports.extend(exporter.write_all([curve], str(out_dir)))
        except Exception as exc:
            warnings.append(f"Curve conditioning failed for {track.name}: {exc}")

    # ── 5. Export timing tracks ───────────────────────────────────────────────
    xtiming_path = str(out_dir / f"{audio_path_p.stem}_timing.xtiming")
    write_timing_tracks(timing_tracks, xtiming_path)

    timing_exports = [
        TimingTrackExport(
            file_path=xtiming_path,
            track_name=t.name,
            source_stem=getattr(t, "stem_source", None) or "full_mix",
            element_type=t.element_type,
            mark_count=t.mark_count,
        )
        for t in timing_tracks
    ]

    # ── 6. Write manifest ─────────────────────────────────────────────────────
    manifest = ExportManifest(
        song_file=str(audio_path_p),
        export_dir=str(out_dir),
        exported_at=datetime.datetime.now().isoformat(),
        stems_used=stems_used,
        timing_tracks=timing_exports,
        value_curves=xvc_exports,
        warnings=warnings,
    )
    manifest_path = out_dir / "export_manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

    return manifest
