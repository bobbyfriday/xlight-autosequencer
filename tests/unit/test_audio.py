"""T014: Unit tests for audio loader in src/analyzer/audio.py — RED before T013."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from src.analyzer.audio import AudioFile, load


class TestLoadValidFile:
    def test_returns_tuple(self, beat_fixture_path: Path):
        result = load(str(beat_fixture_path))
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_audio_is_float32_numpy_array(self, beat_fixture_path: Path):
        audio, sr, meta = load(str(beat_fixture_path))
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32

    def test_audio_is_mono(self, beat_fixture_path: Path):
        audio, sr, meta = load(str(beat_fixture_path))
        assert audio.ndim == 1

    def test_sample_rate_is_positive_int(self, beat_fixture_path: Path):
        audio, sr, meta = load(str(beat_fixture_path))
        assert isinstance(sr, int)
        assert sr > 0

    def test_audio_file_meta_populated(self, beat_fixture_path: Path):
        audio, sr, meta = load(str(beat_fixture_path))
        assert isinstance(meta, AudioFile)
        assert meta.filename == beat_fixture_path.name
        assert meta.duration_ms > 0
        assert meta.sample_rate == sr
        assert meta.channels >= 1

    def test_duration_ms_approximately_10_seconds(self, beat_fixture_path: Path):
        audio, sr, meta = load(str(beat_fixture_path))
        assert 9000 <= meta.duration_ms <= 11000

    def test_audio_values_in_range(self, beat_fixture_path: Path):
        audio, sr, meta = load(str(beat_fixture_path))
        assert np.max(np.abs(audio)) <= 1.0 + 1e-6  # librosa normalises


class TestLoadInvalidFile:
    def test_missing_file_raises_value_error(self, tmp_path: Path):
        with pytest.raises(ValueError, match="not found"):
            load(str(tmp_path / "nonexistent.wav"))

    def test_corrupt_file_raises_value_error(self, tmp_path: Path):
        bad = tmp_path / "bad.wav"
        bad.write_bytes(b"this is not audio")
        with pytest.raises(ValueError):
            load(str(bad))
