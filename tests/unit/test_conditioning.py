"""Tests for conditioning.py: downsample, smooth, normalize, condition_curve."""
from __future__ import annotations

import math

import numpy as np
import pytest

from src.analyzer.result import ConditionedCurve
from src.analyzer.conditioning import condition_curve, downsample, normalize, smooth


SR = 22050
HOP = 512  # typical librosa hop


# ── T038: downsample() ────────────────────────────────────────────────────────


class TestDownsample:
    """T038 — output length matches target_fps, values are interpolated."""

    def test_output_length_at_20fps(self):
        n_frames = 100
        values = np.linspace(0.0, 1.0, n_frames)
        # source: SR=22050, hop=512 → ~43 fps; target: 20 fps
        result = downsample(values, source_sr=SR, source_hop=HOP, target_fps=20)
        duration_s = n_frames * HOP / SR
        expected_len = max(1, round(duration_s * 20))
        assert abs(len(result) - expected_len) <= 1

    def test_output_length_at_10fps(self):
        n_frames = 200
        values = np.ones(n_frames) * 0.5
        result = downsample(values, source_sr=SR, source_hop=HOP, target_fps=10)
        duration_s = n_frames * HOP / SR
        expected_len = max(1, round(duration_s * 10))
        assert abs(len(result) - expected_len) <= 1

    def test_constant_signal_preserved(self):
        values = np.full(100, 0.5)
        result = downsample(values, source_sr=SR, source_hop=HOP, target_fps=20)
        assert np.allclose(result, 0.5, atol=0.01)

    def test_monotonic_signal_remains_monotonic(self):
        values = np.linspace(0.0, 1.0, 200)
        result = downsample(values, source_sr=SR, source_hop=HOP, target_fps=20)
        assert np.all(np.diff(result) >= -0.01), "Downsampled monotonic signal should stay monotonic"

    def test_returns_numpy_array(self):
        values = np.ones(50)
        result = downsample(values, source_sr=SR, source_hop=HOP, target_fps=20)
        assert isinstance(result, np.ndarray)


# ── T039: smooth() ────────────────────────────────────────────────────────────


class TestSmooth:
    """T039 — peaks preserved ≥90%; noise reduced; no time lag."""

    def test_returns_same_length(self):
        values = np.random.default_rng(0).normal(0, 0.1, 100)
        result = smooth(values)
        assert len(result) == len(values)

    def test_constant_signal_unchanged(self):
        values = np.full(50, 0.5)
        result = smooth(values)
        assert np.allclose(result, 0.5, atol=0.05)

    def test_noise_variance_reduced(self):
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 0.5, 100)
        result = smooth(noise)
        assert np.var(result) < np.var(noise), "Smoothing should reduce variance"

    def test_peak_preserved_at_90_percent(self):
        """A sharp isolated peak should be ≥90% of its original height after smoothing."""
        values = np.zeros(50)
        values[25] = 1.0  # isolated peak
        result = smooth(values, peak_restore_ratio=0.9)
        assert result[25] >= 0.9, f"Peak preservation failed: peak={result[25]:.3f}"

    def test_peak_position_unchanged(self):
        """The peak should remain at the same frame index."""
        values = np.zeros(50)
        values[20] = 1.0
        result = smooth(values)
        assert np.argmax(result) == 20, f"Peak shifted: argmax={np.argmax(result)}"

    def test_returns_numpy_array(self):
        values = np.ones(30)
        result = smooth(values)
        assert isinstance(result, np.ndarray)


# ── T040: normalize() ─────────────────────────────────────────────────────────


class TestNormalize:
    """T040 — integer output in [0,100]; flat curves flagged; dynamic curves span 0-100."""

    def test_returns_tuple(self):
        values = np.array([0.1, 0.5, 0.9])
        result = normalize(values)
        assert isinstance(result, tuple) and len(result) == 2

    def test_output_values_are_integers(self):
        values = np.linspace(0.0, 1.0, 50)
        out, _ = normalize(values)
        for v in out:
            assert isinstance(v, int), f"Expected int, got {type(v)}: {v}"

    def test_dynamic_curve_spans_0_to_100(self):
        values = np.linspace(0.0, 1.0, 100)
        out, _ = normalize(values)
        assert min(out) == 0
        assert max(out) == 100

    def test_all_values_in_0_100(self):
        values = np.random.default_rng(7).normal(0.5, 0.3, 200)
        out, _ = normalize(values)
        for v in out:
            assert 0 <= v <= 100, f"Value {v} out of [0, 100]"

    def test_flat_curve_is_flagged(self):
        """A constant signal (zero range) should set is_flat=True."""
        values = np.full(50, 0.5)
        _, is_flat = normalize(values)
        assert is_flat is True

    def test_dynamic_curve_is_not_flat(self):
        values = np.linspace(0.0, 1.0, 50)
        _, is_flat = normalize(values)
        assert is_flat is False

    def test_single_value_does_not_crash(self):
        values = np.array([0.3])
        out, is_flat = normalize(values)
        assert is_flat is True
        assert out[0] in (0, 100, 50)  # any valid int


# ── T041: condition_curve() ───────────────────────────────────────────────────


class TestConditionCurve:
    """T041 — full pipeline returns ConditionedCurve with correct metadata."""

    def _raw(self, n_frames: int = 200, amp: float = 0.3) -> np.ndarray:
        return np.abs(np.random.default_rng(1).normal(0, amp, n_frames))

    def test_returns_conditioned_curve(self):
        raw = self._raw()
        result = condition_curve(raw, SR, HOP, 20, "drums_rms", "drums", "rms")
        assert isinstance(result, ConditionedCurve)

    def test_name_preserved(self):
        raw = self._raw()
        result = condition_curve(raw, SR, HOP, 20, "my_curve", "bass", "flux")
        assert result.name == "my_curve"

    def test_stem_preserved(self):
        raw = self._raw()
        result = condition_curve(raw, SR, HOP, 20, "x", "guitar", "rms")
        assert result.stem == "guitar"

    def test_feature_preserved(self):
        raw = self._raw()
        result = condition_curve(raw, SR, HOP, 20, "x", "drums", "centroid")
        assert result.feature == "centroid"

    def test_fps_set_correctly(self):
        raw = self._raw()
        result = condition_curve(raw, SR, HOP, 20, "x", "drums", "rms")
        assert result.fps == 20

    def test_output_values_are_integers_in_range(self):
        raw = self._raw()
        result = condition_curve(raw, SR, HOP, 20, "x", "drums", "rms")
        for v in result.values:
            assert isinstance(v, int)
            assert 0 <= v <= 100

    def test_flat_input_sets_is_flat(self):
        raw = np.full(200, 0.5)
        result = condition_curve(raw, SR, HOP, 20, "x", "drums", "rms")
        assert result.is_flat is True

    def test_dynamic_input_not_flat(self):
        raw = np.linspace(0.0, 1.0, 200)
        result = condition_curve(raw, SR, HOP, 20, "x", "drums", "rms")
        assert result.is_flat is False

    def test_output_length_matches_target_fps(self):
        n_frames = 200
        raw = self._raw(n_frames)
        result = condition_curve(raw, SR, HOP, 20, "x", "drums", "rms")
        duration_s = n_frames * HOP / SR
        expected = max(1, round(duration_s * 20))
        assert abs(len(result.values) - expected) <= 1
