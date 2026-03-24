"""Cross-stem musical interaction analysis."""
from __future__ import annotations

from typing import Optional

import numpy as np

from src.analyzer.result import (
    HandoffEvent,
    InteractionResult,
    LeaderTrack,
    LeaderTransition,
    SidechainedCurve,
    TightnessResult,
    TightnessWindow,
)


# ── Leader track ──────────────────────────────────────────────────────────────

def compute_leader_track(
    stem_audio: dict[str, np.ndarray],
    sample_rate: int,
    fps: int = 20,
    hold_ms: int = 250,
    delta_db: float = 6.0,
) -> LeaderTrack:
    """Per-frame dominant stem via RMS (0.7) + spectral flux (0.3), with hold state machine."""
    hop = sample_rate // fps
    stem_names = list(stem_audio.keys())

    n_frames = min(len(y) for y in stem_audio.values()) // hop
    scores = np.zeros((len(stem_names), n_frames), dtype=np.float64)

    for si, name in enumerate(stem_names):
        y = stem_audio[name]
        for fi in range(n_frames):
            chunk = y[fi * hop : (fi + 1) * hop]
            rms = float(np.sqrt(np.mean(chunk ** 2)) + 1e-9)
            if len(chunk) >= 2:
                spec = np.abs(np.fft.rfft(chunk))
                flux = float(np.mean(np.abs(np.diff(spec)))) + 1e-9
            else:
                flux = 1e-9
            scores[si, fi] = 0.7 * rms + 0.3 * flux

    hold_frames = max(1, int(hold_ms * fps / 1000))
    frames: list[str] = []
    transitions: list[LeaderTransition] = []

    current_leader_idx = int(np.argmax(scores[:, 0])) if n_frames > 0 else 0
    hold_remaining = 0

    for fi in range(n_frames):
        frame_scores = scores[:, fi]
        best_idx = int(np.argmax(frame_scores))

        if best_idx != current_leader_idx:
            current_db = 20.0 * np.log10(frame_scores[current_leader_idx] + 1e-9)
            best_db = 20.0 * np.log10(frame_scores[best_idx] + 1e-9)
            db_diff = best_db - current_db

            if db_diff >= delta_db or hold_remaining <= 0:
                old_leader = stem_names[current_leader_idx]
                current_leader_idx = best_idx
                hold_remaining = hold_frames
                transitions.append(LeaderTransition(
                    time_ms=int(fi * 1000 / fps),
                    from_stem=old_leader,
                    to_stem=stem_names[current_leader_idx],
                ))
            else:
                hold_remaining -= 1
        else:
            hold_remaining = max(0, hold_remaining - 1)

        frames.append(stem_names[current_leader_idx])

    return LeaderTrack(fps=fps, frames=frames, transitions=transitions)


# ── Kick-bass tightness ───────────────────────────────────────────────────────

def compute_tightness(
    drums_audio: np.ndarray,
    bass_audio: np.ndarray,
    sample_rate: int,
    bpm: float,
    fps: int = 20,
) -> Optional[TightnessResult]:
    """Windowed onset-envelope cross-correlation for kick-bass tightness."""
    if float(np.sqrt(np.mean(bass_audio ** 2))) < 1e-4:
        return None

    hop = sample_rate // fps

    def onset_envelope(y: np.ndarray) -> np.ndarray:
        n_frames = len(y) // hop
        env = np.array([
            float(np.sqrt(np.mean(y[i * hop : (i + 1) * hop] ** 2)))
            for i in range(n_frames)
        ])
        d = np.diff(env, prepend=env[0])
        return np.maximum(d, 0)

    drums_env = onset_envelope(drums_audio)
    bass_env = onset_envelope(bass_audio)
    n_frames = min(len(drums_env), len(bass_env))
    drums_env = drums_env[:n_frames]
    bass_env = bass_env[:n_frames]

    frames_per_beat = max(1, int(fps * 60 / bpm))
    window_frames = frames_per_beat * 4 * 4  # 4 bars
    hop_frames = max(1, window_frames // 2)

    windows: list[TightnessWindow] = []
    i = 0
    while i + window_frames <= n_frames:
        d_win = drums_env[i : i + window_frames]
        b_win = bass_env[i : i + window_frames]

        d_norm = d_win - d_win.mean()
        b_norm = b_win - b_win.mean()
        d_std = d_norm.std() + 1e-9
        b_std = b_norm.std() + 1e-9
        corr = float(np.dot(d_norm / d_std, b_norm / b_std) / window_frames)
        score = max(0.0, min(1.0, (corr + 1.0) / 2.0))

        if score >= 0.7:
            label = "unison"
        elif score <= 0.3:
            label = "independent"
        else:
            label = "mixed"

        windows.append(TightnessWindow(
            start_ms=int(i * 1000 / fps),
            end_ms=int((i + window_frames) * 1000 / fps),
            score=score,
            label=label,
        ))
        i += hop_frames

    return TightnessResult(windows=windows)


# ── Visual sidechaining ───────────────────────────────────────────────────────

def compute_sidechain(
    vocal_values: list[float],
    drum_onset_ms: list[int],
    fps: int = 20,
    depth: float = 0.4,
    release_frames: int = 3,
) -> SidechainedCurve:
    """Multiplicative gain envelope at drum onsets, with exponential recovery."""
    n = len(vocal_values)
    gain = np.ones(n, dtype=np.float64)
    boost = np.zeros(n, dtype=np.float64)

    for onset_ms in drum_onset_ms:
        frame_idx = int(onset_ms * fps / 1000)
        if frame_idx >= n:
            continue
        gain[frame_idx] = 1.0 - depth
        boost[frame_idx] = min(100.0, vocal_values[frame_idx] + 30.0)
        for r in range(1, release_frames + 1):
            fi = frame_idx + r
            if fi >= n:
                break
            recovery = 1.0 - depth * np.exp(-r)
            gain[fi] = min(1.0, max(gain[fi], recovery))

    values_out = [int(round(max(0.0, min(100.0, vocal_values[i] * gain[i])))) for i in range(n)]
    boost_out = [int(round(max(0.0, min(100.0, boost[i])))) for i in range(n)]

    return SidechainedCurve(
        source_stem="vocals",
        feature="brightness",
        fps=fps,
        values=values_out,
        boost_values=boost_out,
    )


# ── Handoff detection ─────────────────────────────────────────────────────────

_MELODIC_STEMS = {"vocals", "guitar", "piano", "other"}


def detect_handoffs(
    stem_energy: dict[str, np.ndarray],
    sample_rate: int,
    fps: int = 20,
    max_gap_ms: int = 500,
) -> list[HandoffEvent]:
    """Energy-envelope gap analysis for melodic stem handoffs."""
    hop = sample_rate // fps
    max_gap_frames = max(1, int(max_gap_ms * fps / 1000))

    melodic = {k: v for k, v in stem_energy.items() if k in _MELODIC_STEMS}
    if len(melodic) < 2:
        return []

    masks: dict[str, np.ndarray] = {}
    for name, y in melodic.items():
        n_frames = len(y) // hop
        env = np.array([
            float(np.sqrt(np.mean(y[i * hop : (i + 1) * hop] ** 2)))
            for i in range(n_frames)
        ])
        threshold = max(env.max() * 0.1, 1e-3)
        masks[name] = env > threshold

    stem_list = list(masks.keys())
    events: list[HandoffEvent] = []

    for ai, stem_a in enumerate(stem_list):
        for stem_b in stem_list[ai + 1:]:
            mask_a = masks[stem_a]
            mask_b = masks[stem_b]
            n = min(len(mask_a), len(mask_b))

            for fi in range(n - 1):
                if mask_a[fi] and not mask_a[fi + 1]:
                    for fj in range(fi + 1, min(fi + max_gap_frames + 1, n)):
                        if mask_b[fj]:
                            gap_frames = fj - fi
                            confidence = max(0.0, 1.0 - gap_frames / max_gap_frames)
                            events.append(HandoffEvent(
                                time_ms=int((fi + fj) // 2 * 1000 / fps),
                                from_stem=stem_a,
                                to_stem=stem_b,
                                confidence=confidence,
                            ))
                            break

    return events


# ── Other stem classification ─────────────────────────────────────────────────

def classify_other_stem(other_audio: np.ndarray, sample_rate: int) -> str:
    """Classify the 'other' stem as spatial, timing, or ambiguous."""
    if len(other_audio) == 0 or float(np.sqrt(np.mean(other_audio ** 2))) < 1e-5:
        return "ambiguous"

    n_fft = min(2048, len(other_audio))
    spec = np.abs(np.fft.rfft(other_audio[:n_fft]))
    spectral_var = float(np.var(spec))

    d = np.diff(other_audio)
    rms_d = float(np.sqrt(np.mean(d ** 2))) + 1e-9
    peak_d = float(np.max(np.abs(d))) + 1e-9
    crest = peak_d / rms_d

    if crest > 20.0:
        return "timing"
    elif spectral_var > 1.0 and crest < 10.0:
        return "spatial"
    return "ambiguous"


# ── Top-level orchestrator ────────────────────────────────────────────────────

def analyze_interactions(
    stem_audio: dict[str, np.ndarray],
    sample_rate: int,
    fps: int = 20,
    bpm: float = 120.0,
) -> InteractionResult:
    """Orchestrate all interaction analysis and return a complete InteractionResult."""
    leader_track = compute_leader_track(stem_audio, sample_rate, fps=fps)

    drums = stem_audio.get("drums")
    bass = stem_audio.get("bass")
    tightness = None
    if drums is not None and bass is not None:
        tightness = compute_tightness(drums, bass, sample_rate, bpm=bpm, fps=fps)

    vocals = stem_audio.get("vocals")
    sidechained_curves = []
    if vocals is not None and drums is not None:
        hop = sample_rate // fps
        n_frames = len(vocals) // hop
        vocal_values = [
            min(100.0, float(np.sqrt(np.mean(vocals[i * hop:(i + 1) * hop] ** 2))) * 1000)
            for i in range(n_frames)
        ]
        drum_env = np.array([
            float(np.sqrt(np.mean(drums[i * hop:(i + 1) * hop] ** 2)))
            for i in range(min(n_frames, len(drums) // hop))
        ])
        threshold = max(drum_env.max() * 0.3, 1e-4)
        onset_ms = [int(i * 1000 / fps) for i in range(len(drum_env)) if drum_env[i] > threshold]
        sidechained_curves.append(
            compute_sidechain(vocal_values, onset_ms, fps=fps)
        )

    handoffs = detect_handoffs(stem_audio, sample_rate, fps=fps, max_gap_ms=500)

    other_stem_class = None
    other = stem_audio.get("other")
    if other is not None:
        other_stem_class = classify_other_stem(other, sample_rate)

    return InteractionResult(
        leader_track=leader_track,
        tightness=tightness,
        sidechained_curves=sidechained_curves,
        handoffs=handoffs,
        other_stem_class=other_stem_class,
    )
