"""Tests for librosa onset algorithm."""
from __future__ import annotations

import pytest
from src.analyzer.algorithms.librosa_onset import LibrosaOnsetAlgorithm
from src.analyzer.audio import load


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


def test_produces_timing_track(beat_audio):
    audio, sr = beat_audio
    track = LibrosaOnsetAlgorithm().run(audio, sr)
    assert track is not None
    assert track.name == "librosa_onsets"
    assert track.element_type == "onset"
    assert track.mark_count > 0


def test_onsets_have_more_marks_than_beats(beat_audio):
    """Onset detection is less filtered than beat tracking."""
    from src.analyzer.algorithms.librosa_beats import LibrosaBeatAlgorithm
    audio, sr = beat_audio
    beats = LibrosaBeatAlgorithm().run(audio, sr)
    onsets = LibrosaOnsetAlgorithm().run(audio, sr)
    assert onsets.mark_count >= beats.mark_count
