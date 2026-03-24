"""Tests for stem_inspector: inspect_stems(), generate_sweep_configs(), interactive_review()."""
from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.analyzer.stem_inspector import (
    StemMetrics,
    _bpm_sweep,
    _sensitivity_range,
    generate_sweep_configs,
    inspect_stems,
)
from src.analyzer.result import StemSelection


# ── Fixtures: synthetic audio arrays ──────────────────────────────────────────

SR = 22050  # sample rate for all synthetic stems


def _silent(duration_s: float = 3.0) -> np.ndarray:
    """Near-silent audio — RMS well below 0.005 threshold."""
    return np.zeros(int(duration_s * SR))


def _sparse(duration_s: float = 3.0, active_frac: float = 0.15) -> np.ndarray:
    """Audio active only active_frac of the time — should trigger REVIEW."""
    y = np.zeros(int(duration_s * SR))
    n_active = int(len(y) * active_frac)
    y[:n_active] = np.random.default_rng(0).normal(0, 0.1, n_active)
    return y


def _active(duration_s: float = 3.0) -> np.ndarray:
    """Full-energy, consistently active audio — should trigger KEEP."""
    return np.random.default_rng(42).normal(0, 0.05, int(duration_s * SR))


def _stem_metrics(name: str, verdict: str, rms: float = 0.05,
                  coverage: float = 0.9, crest_db: float = 18.0,
                  centroid_hz: float = 2000.0) -> StemMetrics:
    return StemMetrics(
        name=name, rms=rms, peak=rms * 10,
        crest_db=crest_db, coverage=coverage,
        spectral_centroid_hz=centroid_hz,
        verdict=verdict, reason="test reason",
    )


# ── T004: inspect_stems() verdict thresholds ──────────────────────────────────

class TestInspectStemsVerdicts:
    """T004 — verify SKIP / REVIEW / KEEP thresholds."""

    def test_silent_stem_is_skipped(self, tmp_path):
        """Nearly silent audio (RMS < 0.005) must receive verdict='skip'."""
        metrics = _make_metrics_for(_silent(), SR, "other")
        assert metrics.verdict == "skip", f"Expected skip, got {metrics.verdict}"

    def test_sparse_stem_is_reviewed(self, tmp_path):
        """Stem active < 40% must receive verdict='review'."""
        metrics = _make_metrics_for(_sparse(active_frac=0.20), SR, "guitar")
        assert metrics.verdict == "review", f"Expected review, got {metrics.verdict}"

    def test_active_stem_is_kept(self):
        """Full-energy consistently active stem must receive verdict='keep'."""
        metrics = _make_metrics_for(_active(), SR, "drums")
        assert metrics.verdict == "keep", f"Expected keep, got {metrics.verdict}"

    def test_coverage_boundary_skip(self):
        """Coverage exactly at the skip threshold (12%) yields skip."""
        metrics = _make_metrics_for(_sparse(active_frac=0.10), SR, "piano")
        assert metrics.verdict == "skip"

    def test_coverage_boundary_review(self):
        """Coverage between 12% and 40% yields review."""
        metrics = _make_metrics_for(_sparse(active_frac=0.30), SR, "piano")
        assert metrics.verdict == "review"


def _make_metrics_for(y: np.ndarray, sr: int, name: str) -> StemMetrics:
    """Call the private _compute_metrics helper directly."""
    from src.analyzer.stem_inspector import _compute_metrics
    return _compute_metrics(name, y, sr)


# ── T005: verdicts include meaningful reason strings ──────────────────────────

class TestInspectStemsReasonStrings:
    """T005 — every verdict must include a reason referencing relevant measurements."""

    def test_skip_reason_references_energy_or_coverage(self):
        metrics = _make_metrics_for(_silent(), SR, "bass")
        assert metrics.reason, "reason must not be empty"
        low = metrics.reason.lower()
        assert any(kw in low for kw in ("silent", "rms", "sparse", "active")), (
            f"skip reason should mention energy/coverage: {metrics.reason}"
        )

    def test_review_reason_references_coverage(self):
        metrics = _make_metrics_for(_sparse(active_frac=0.25), SR, "vocals")
        low = metrics.reason.lower()
        assert any(kw in low for kw in ("active", "intermittent", "coverage", "%")), (
            f"review reason should mention coverage: {metrics.reason}"
        )

    def test_keep_reason_references_content_character(self):
        metrics = _make_metrics_for(_active(), SR, "drums")
        low = metrics.reason.lower()
        # should mention activity level, crest, or centroid
        assert any(kw in low for kw in ("active", "crest", "centroid", "hz", "%", "db")), (
            f"keep reason should describe character: {metrics.reason}"
        )


# ── T006: full_mix is always included ─────────────────────────────────────────

class TestFullMixAlwaysIncluded:
    """T006 — inspect_stems always returns full_mix regardless of stem availability."""

    def test_full_mix_first_in_results(self, tmp_path):
        """First entry must always be full_mix."""
        # Create a tiny WAV fixture so librosa.load() works without a real MP3
        import soundfile as sf
        y = _active(duration_s=1.0)
        wav = tmp_path / "song.wav"
        sf.write(str(wav), y, SR)

        results = inspect_stems(str(wav))
        assert results, "Results must not be empty"
        assert results[0].name == "full_mix", (
            f"First result must be full_mix, got {results[0].name}"
        )

    def test_full_mix_present_even_with_no_stems_dir(self, tmp_path):
        import soundfile as sf
        y = _active(duration_s=1.0)
        wav = tmp_path / "song.wav"
        sf.write(str(wav), y, SR)

        results = inspect_stems(str(wav), stem_dir=None)
        names = [r.name for r in results]
        assert "full_mix" in names


# ── T021: _bpm_sweep() bracketing ─────────────────────────────────────────────

class TestBpmSweep:
    """T021 — _bpm_sweep returns three values bracketing the estimate."""

    def test_returns_three_values(self):
        vals = _bpm_sweep(120.0)
        assert len(vals) == 3

    def test_brackets_estimate(self):
        bpm = 120.0
        vals = _bpm_sweep(bpm)
        assert min(vals) < bpm < max(vals), (
            f"sweep {vals} should bracket {bpm}"
        )

    def test_0_8x_below(self):
        bpm = 120.0
        vals = _bpm_sweep(bpm)
        assert vals[0] == round(bpm * 0.8)

    def test_1_25x_above(self):
        bpm = 120.0
        vals = _bpm_sweep(bpm)
        assert vals[-1] == round(bpm * 1.25)

    def test_low_bpm_clamped(self):
        vals = _bpm_sweep(50.0)
        assert min(vals) >= 40

    def test_high_bpm_clamped(self):
        vals = _bpm_sweep(200.0)
        assert max(vals) <= 240

    def test_returns_sorted(self):
        vals = _bpm_sweep(100.0)
        assert vals == sorted(vals)


# ── T022: stem affinity — rhythmic vs tonal ───────────────────────────────────

class TestStemAffinity:
    """T022 — rhythmic stems preferred by beat algos; tonal by pitch/harmony algos."""

    def _run_sweep(self, metrics_list):
        """Helper: call generate_sweep_configs with mocked librosa."""
        mock_lib = MagicMock()
        mock_lib.load.return_value = (np.zeros(1000), SR)
        mock_lib.beat.beat_track.return_value = (np.array([120.0]), np.array([0, 1, 2]))
        mock_lib.frames_to_time.return_value = np.array([0.5, 1.0])
        with patch.dict("sys.modules", {"librosa": mock_lib}):
            configs, _ = generate_sweep_configs("fake.mp3", metrics_list)
        return {c["algorithm"]: c for c in configs}

    def test_beat_algo_prefers_drums_over_piano(self):
        metrics = [
            _stem_metrics("full_mix", "keep"),
            _stem_metrics("drums", "keep", crest_db=25.0, coverage=0.95),
            _stem_metrics("piano", "keep", crest_db=8.0, centroid_hz=3000.0),
        ]
        configs = self._run_sweep(metrics)
        qm_beats = configs.get("qm_beats", {})
        assert "drums" in qm_beats.get("stems", []), (
            f"qm_beats should prefer drums: {qm_beats.get('stems')}"
        )

    def test_pitch_algo_prefers_piano_over_drums(self):
        metrics = [
            _stem_metrics("full_mix", "keep"),
            _stem_metrics("drums", "keep", crest_db=25.0, coverage=0.95),
            _stem_metrics("piano", "keep", crest_db=8.0, centroid_hz=3000.0),
        ]
        configs = self._run_sweep(metrics)
        pyin = configs.get("pyin_notes", {})
        stems = pyin.get("stems", [])
        piano_pos = stems.index("piano") if "piano" in stems else 99
        drums_pos = stems.index("drums") if "drums" in stems else 99
        assert piano_pos < drums_pos, (
            f"pyin_notes should prefer piano over drums: {stems}"
        )


# ── T023: configs include rationale ───────────────────────────────────────────

class TestConfigRationale:
    """T023 — every generated config must include a human-readable rationale."""

    def _mock_sweep(self, metrics):
        mock_lib = MagicMock()
        mock_lib.load.return_value = (np.zeros(1000), SR)
        mock_lib.beat.beat_track.return_value = (np.array([120.0]), np.array([0, 1, 2]))
        mock_lib.frames_to_time.return_value = np.array([0.5, 1.0])
        with patch.dict("sys.modules", {"librosa": mock_lib}):
            configs, _ = generate_sweep_configs("fake.mp3", metrics)
        return configs

    def test_beat_config_has_rationale(self):
        metrics = [_stem_metrics("full_mix", "keep")]
        configs = self._mock_sweep(metrics)
        for cfg in configs:
            meta = cfg.get("_meta", {})
            assert "rationale" in meta, f"{cfg['algorithm']} missing rationale"
            assert meta["rationale"], f"{cfg['algorithm']} rationale is empty"

    def test_rationale_mentions_bpm_for_beat_algos(self):
        metrics = [_stem_metrics("full_mix", "keep")]
        configs = self._mock_sweep(metrics)
        beat_cfgs = [c for c in configs if c["algorithm"] in ("qm_beats", "qm_bars")]
        for cfg in beat_cfgs:
            assert "bpm" in cfg["_meta"]["rationale"].lower() or \
                   "tempo" in cfg["_meta"]["rationale"].lower(), (
                f"Beat algo rationale should mention BPM/tempo: {cfg['_meta']['rationale']}"
            )


# ── T024: low-energy stem → higher sensitivity ────────────────────────────────

class TestSensitivityRange:
    """T024 — low-RMS stems should produce higher sensitivity values."""

    def test_quiet_stem_gets_higher_sensitivity_than_loud(self):
        quiet = [_stem_metrics("bass", "keep", rms=0.005)]
        loud = [_stem_metrics("drums", "keep", rms=0.12)]
        stem_map_quiet = {"bass": quiet[0]}
        stem_map_loud = {"drums": loud[0]}

        sens_quiet = _sensitivity_range(["bass"], stem_map_quiet)
        sens_loud = _sensitivity_range(["drums"], stem_map_loud)

        # Higher sensitivity values for quieter stem
        assert max(sens_quiet) > max(sens_loud), (
            f"Quiet stem should have higher max sensitivity: "
            f"quiet={sens_quiet}, loud={sens_loud}"
        )

    def test_returns_four_values(self):
        stem_map = {"drums": _stem_metrics("drums", "keep", rms=0.08)}
        vals = _sensitivity_range(["drums"], stem_map)
        assert len(vals) == 4

    def test_values_in_valid_range(self):
        stem_map = {"bass": _stem_metrics("bass", "keep", rms=0.01)}
        vals = _sensitivity_range(["bass"], stem_map)
        for v in vals:
            assert 10 <= v <= 90, f"Sensitivity {v} out of range [10, 90]"


# ── T017: interactive_review() ────────────────────────────────────────────────

class TestInteractiveReview:
    """T017 — interactive_review() accepts/overrides verdicts and returns StemSelection."""

    def test_accept_all_yields_no_overrides(self):
        from src.analyzer.stem_inspector import interactive_review
        metrics = [
            _stem_metrics("full_mix", "keep"),
            _stem_metrics("drums", "keep"),
        ]
        # Simulate pressing Enter (accept) for each stem
        with patch("builtins.input", return_value=""):
            result = interactive_review(metrics)
        assert isinstance(result, StemSelection)
        assert result.overrides == []

    def test_override_skip_to_keep(self):
        from src.analyzer.stem_inspector import interactive_review
        metrics = [
            _stem_metrics("full_mix", "keep"),
            _stem_metrics("other", "skip"),
        ]
        # Accept full_mix (Enter), override other to Keep
        inputs = iter(["", "k"])
        with patch("builtins.input", side_effect=inputs):
            result = interactive_review(metrics)
        assert result.stems.get("other") == "keep"
        assert "other" in result.overrides

    def test_all_skip_triggers_fallback(self):
        from src.analyzer.stem_inspector import interactive_review
        metrics = [
            _stem_metrics("drums", "keep"),
        ]
        # User explicitly skips everything
        with patch("builtins.input", return_value="s"):
            result = interactive_review(metrics)
        assert result.fallback_to_mix is True

    def test_auto_accept_skips_prompts(self):
        from src.analyzer.stem_inspector import interactive_review
        metrics = [_stem_metrics("full_mix", "keep"), _stem_metrics("drums", "keep")]
        result = interactive_review(metrics, auto_accept=True)
        assert isinstance(result, StemSelection)
        assert result.overrides == []
