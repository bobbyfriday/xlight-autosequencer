"""Tests for interaction.py: cross-stem analysis functions."""
from __future__ import annotations

import numpy as np
import pytest

from src.analyzer.result import (
    HandoffEvent,
    InteractionResult,
    LeaderTrack,
    LeaderTransition,
    SidechainedCurve,
    TightnessResult,
)
from src.analyzer.interaction import (
    compute_leader_track,
    compute_sidechain,
    compute_tightness,
    detect_handoffs,
    classify_other_stem,
    analyze_interactions,
)


SR = 22050
FPS = 20
HOP = SR // FPS  # samples per frame


def _silence(dur_s: float = 3.0) -> np.ndarray:
    return np.zeros(int(dur_s * SR))


def _noise(dur_s: float = 3.0, amp: float = 0.1) -> np.ndarray:
    return np.random.default_rng(0).normal(0, amp, int(dur_s * SR)).astype(np.float32)


def _pulse_train(dur_s: float = 4.0, interval_s: float = 0.5) -> np.ndarray:
    """Periodic impulses at regular intervals — simulates a kick drum."""
    y = np.zeros(int(dur_s * SR))
    for t in np.arange(0.0, dur_s, interval_s):
        idx = int(t * SR)
        if idx < len(y):
            y[idx] = 1.0
    return y


# ── T027: compute_leader_track() ─────────────────────────────────────────────


class TestComputeLeaderTrack:
    """T027 — highest-RMS stem wins; 250ms hold prevents rapid switching; 6dB delta bypasses."""

    def test_returns_leader_track(self):
        stem_audio = {
            "drums": _noise(amp=0.3),
            "bass": _noise(amp=0.05),
        }
        result = compute_leader_track(stem_audio, SR, fps=FPS)
        assert isinstance(result, LeaderTrack)

    def test_frames_count_matches_duration(self):
        dur = 2.0
        stem_audio = {"drums": _noise(dur_s=dur, amp=0.2), "bass": _noise(dur_s=dur, amp=0.05)}
        result = compute_leader_track(stem_audio, SR, fps=FPS)
        expected_frames = int(dur * FPS)
        assert abs(len(result.frames) - expected_frames) <= 1

    def test_louder_stem_is_leader(self):
        """Stem with significantly higher RMS should dominate most frames."""
        stem_audio = {
            "drums": _noise(amp=0.3),
            "bass": _noise(amp=0.01),
        }
        result = compute_leader_track(stem_audio, SR, fps=FPS)
        drums_count = result.frames.count("drums")
        assert drums_count > len(result.frames) * 0.7, (
            f"Expected drums to lead >70% of frames, got {drums_count}/{len(result.frames)}"
        )

    def test_transitions_list_present(self):
        stem_audio = {"drums": _noise(amp=0.2), "bass": _noise(amp=0.05)}
        result = compute_leader_track(stem_audio, SR, fps=FPS)
        assert isinstance(result.transitions, list)

    def test_transitions_are_leader_transition_objects(self):
        # Two stems alternating by segment
        dur = 4.0
        n = int(dur * SR)
        drums = np.zeros(n, dtype=np.float32)
        bass = np.zeros(n, dtype=np.float32)
        half = n // 2
        drums[:half] = 0.5   # drums loud first half
        bass[half:] = 0.5    # bass loud second half
        result = compute_leader_track({"drums": drums, "bass": bass}, SR, fps=FPS, hold_ms=0)
        for t in result.transitions:
            assert isinstance(t, LeaderTransition)

    def test_hold_suppresses_rapid_switch(self):
        """With hold_ms > frame duration, a very brief louder burst should NOT cause a transition."""
        dur = 2.0
        n = int(dur * SR)
        drums = np.full(n, 0.3, dtype=np.float32)
        bass = np.zeros(n, dtype=np.float32)
        # Add a tiny 1-frame burst on bass
        one_frame = HOP
        bass[HOP * 5 : HOP * 6] = 0.5
        result = compute_leader_track(
            {"drums": drums, "bass": bass}, SR, fps=FPS, hold_ms=500
        )
        # After hold suppression, drums should still lead most frames
        drums_frac = result.frames.count("drums") / len(result.frames)
        assert drums_frac > 0.8, f"Hold didn't suppress switch; drums_frac={drums_frac:.2f}"

    def test_large_delta_bypasses_hold(self):
        """A large energy jump (>delta_db) should override the hold."""
        dur = 2.0
        n = int(dur * SR)
        drums = np.full(n, 0.01, dtype=np.float32)    # drums quiet
        bass = np.full(n, 0.5, dtype=np.float32)      # bass very loud
        result = compute_leader_track(
            {"drums": drums, "bass": bass}, SR, fps=FPS, hold_ms=5000, delta_db=6.0
        )
        # Despite enormous hold, bass should eventually win because delta >6dB
        bass_frac = result.frames.count("bass") / len(result.frames)
        assert bass_frac > 0.5, f"delta_db bypass didn't work; bass_frac={bass_frac:.2f}"


# ── T028: compute_tightness() ─────────────────────────────────────────────────


class TestComputeTightness:
    """T028 — onset-envelope cross-correlation labels: unison ≥0.7, independent ≤0.3."""

    def test_returns_tightness_result_or_none(self):
        result = compute_tightness(_pulse_train(), _pulse_train(), SR, bpm=120.0, fps=FPS)
        assert result is None or isinstance(result, TightnessResult)

    def test_synchronized_onsets_score_high(self):
        """Identical pulse trains → very high tightness score."""
        kick = _pulse_train(dur_s=8.0, interval_s=0.5)
        bass = _pulse_train(dur_s=8.0, interval_s=0.5)
        result = compute_tightness(kick, bass, SR, bpm=120.0, fps=FPS)
        assert result is not None
        assert len(result.windows) > 0
        avg_score = np.mean([w.score for w in result.windows])
        assert avg_score >= 0.6, f"Expected high score for sync onsets, got {avg_score:.2f}"

    def test_desynchronized_onsets_score_low(self):
        """Offset pulse trains → low tightness score."""
        kick = _pulse_train(dur_s=8.0, interval_s=0.5)
        # bass is exactly halfway between kick pulses
        bass = _pulse_train(dur_s=8.0, interval_s=0.5)
        bass = np.roll(bass, int(0.25 * SR))
        result = compute_tightness(kick, bass, SR, bpm=120.0, fps=FPS)
        assert result is not None
        avg_score = np.mean([w.score for w in result.windows])
        assert avg_score <= 0.5, f"Expected low score for desync onsets, got {avg_score:.2f}"

    def test_missing_bass_returns_none(self):
        result = compute_tightness(_pulse_train(), _silence(), SR, bpm=120.0, fps=FPS)
        assert result is None

    def test_windows_have_labels(self):
        kick = _pulse_train(dur_s=8.0, interval_s=0.5)
        bass = _pulse_train(dur_s=8.0, interval_s=0.5)
        result = compute_tightness(kick, bass, SR, bpm=120.0, fps=FPS)
        if result:
            for w in result.windows:
                assert w.label in ("unison", "independent", "mixed"), f"Bad label: {w.label}"


# ── T029: compute_sidechain() ─────────────────────────────────────────────────


class TestComputeSidechain:
    """T029 — values at drum onset frames are attenuated; boost_values are elevated."""

    def _onset_ms(self, bpm: float = 120.0, n: int = 4, start_ms: int = 0) -> list[int]:
        interval_ms = int(60000 / bpm)
        return [start_ms + i * interval_ms for i in range(n)]

    def test_returns_sidechained_curve(self):
        values = [80] * 40
        onsets = self._onset_ms()
        result = compute_sidechain(values, onsets, fps=FPS)
        assert isinstance(result, SidechainedCurve)

    def test_values_dip_at_onset_frames(self):
        """Sidechain attenuates brightness at onset positions."""
        values = [80] * 40
        onsets = [0]  # onset at frame 0
        result = compute_sidechain(values, onsets, fps=FPS, depth=0.4)
        assert result.values[0] < 80, f"Expected dip at onset, got {result.values[0]}"

    def test_values_recover_after_onset(self):
        """After the onset, values recover toward original."""
        values = [80] * 40
        onsets = [0]
        result = compute_sidechain(values, onsets, fps=FPS, depth=0.4, release_frames=3)
        # Several frames after onset, value should be closer to 80
        assert result.values[5] > result.values[0], "Values should recover after onset"

    def test_all_values_in_0_100_range(self):
        values = [50] * 60
        onsets = self._onset_ms(n=8)
        result = compute_sidechain(values, onsets, fps=FPS)
        for v in result.values:
            assert 0 <= v <= 100, f"Value {v} out of [0, 100]"
        for v in result.boost_values:
            assert 0 <= v <= 100, f"Boost value {v} out of [0, 100]"

    def test_boost_values_elevated_at_onset(self):
        """Boost dimension should be elevated at onset frames."""
        values = [40] * 40
        onsets = [500]  # 500ms → frame 10 at 20fps
        result = compute_sidechain(values, onsets, fps=FPS)
        frame_10 = result.boost_values[10]
        assert frame_10 > values[10], f"Boost at onset frame should exceed input; got {frame_10}"

    def test_output_length_matches_input(self):
        values = list(range(50))
        result = compute_sidechain(values, [], fps=FPS)
        assert len(result.values) == len(values)
        assert len(result.boost_values) == len(values)


# ── T030: detect_handoffs() ───────────────────────────────────────────────────


class TestDetectHandoffs:
    """T030 — gap within 500ms between stem A offset and stem B onset yields HandoffEvent."""

    def _energy_dict(self, stems: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        return stems

    def test_returns_list(self):
        stem_energy = {"vocals": _silence(), "guitar": _silence()}
        result = detect_handoffs(stem_energy, SR, fps=FPS)
        assert isinstance(result, list)

    def test_close_gap_produces_handoff(self):
        """Vocals → guitar handoff with <500ms gap produces a HandoffEvent."""
        dur = 4.0
        n = int(dur * SR)
        vocals = np.zeros(n, dtype=np.float32)
        guitar = np.zeros(n, dtype=np.float32)
        half = n // 2
        # vocals active first half, guitar active second half, immediate switch
        vocals[:half] = 0.2
        guitar[half:] = 0.2
        result = detect_handoffs(
            {"vocals": vocals, "guitar": guitar}, SR, fps=FPS, max_gap_ms=500
        )
        assert len(result) >= 1, "Expected at least one handoff event"

    def test_handoff_event_has_correct_types(self):
        dur = 4.0
        n = int(dur * SR)
        vocals = np.zeros(n, dtype=np.float32)
        guitar = np.zeros(n, dtype=np.float32)
        vocals[: n // 2] = 0.2
        guitar[n // 2 :] = 0.2
        result = detect_handoffs({"vocals": vocals, "guitar": guitar}, SR, fps=FPS)
        for h in result:
            assert isinstance(h, HandoffEvent)
            assert 0.0 <= h.confidence <= 1.0

    def test_large_gap_produces_no_handoff(self):
        """A gap >1500ms between vocal offset and guitar onset should not yield a handoff."""
        dur = 8.0
        n = int(dur * SR)
        vocals = np.zeros(n, dtype=np.float32)
        guitar = np.zeros(n, dtype=np.float32)
        # vocals: 0-2s; gap: 2-5s (3s gap); guitar: 5-8s
        vocals[: int(2 * SR)] = 0.2
        guitar[int(5 * SR) :] = 0.2
        result = detect_handoffs(
            {"vocals": vocals, "guitar": guitar}, SR, fps=FPS, max_gap_ms=500
        )
        assert len(result) == 0, f"Expected no handoff across 3s gap, got {result}"

    def test_silence_produces_no_handoff(self):
        stem_energy = {"vocals": _silence(), "guitar": _silence()}
        result = detect_handoffs(stem_energy, SR, fps=FPS)
        assert len(result) == 0


# ── T031: classify_other_stem() ───────────────────────────────────────────────


class TestClassifyOtherStem:
    """T031 — high spectral variance → spatial; high transients → timing; else ambiguous."""

    def test_returns_string(self):
        label = classify_other_stem(_noise(amp=0.1), SR)
        assert isinstance(label, str)

    def test_returns_valid_label(self):
        valid = {"spatial", "timing", "ambiguous"}
        for _ in range(3):
            label = classify_other_stem(_noise(amp=0.1), SR)
            assert label in valid, f"Unexpected label: {label}"

    def test_high_transient_audio_is_timing(self):
        """A pulse train with sharp transients should be classified as 'timing'."""
        label = classify_other_stem(_pulse_train(interval_s=0.1), SR)
        assert label == "timing", f"Expected 'timing' for pulse train, got '{label}'"

    def test_silence_classified(self):
        """Silent audio should return a valid label without error."""
        label = classify_other_stem(_silence(), SR)
        assert label in {"spatial", "timing", "ambiguous"}


# ── analyze_interactions() integration ────────────────────────────────────────


class TestAnalyzeInteractions:
    """Smoke-test: analyze_interactions() returns InteractionResult."""

    def test_returns_interaction_result(self):
        stem_audio = {
            "drums": _noise(amp=0.3),
            "bass": _noise(amp=0.1),
            "vocals": _noise(amp=0.05),
        }
        result = analyze_interactions(stem_audio, SR, fps=FPS, bpm=120.0)
        assert isinstance(result, InteractionResult)

    def test_leader_track_present(self):
        stem_audio = {"drums": _noise(amp=0.3), "bass": _noise(amp=0.1)}
        result = analyze_interactions(stem_audio, SR, fps=FPS, bpm=120.0)
        assert isinstance(result.leader_track, LeaderTrack)
