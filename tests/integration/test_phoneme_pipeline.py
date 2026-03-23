"""Integration tests for end-to-end phoneme analysis pipeline (component-level)."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.phonemes import (
    LyricsBlock, PhonemeMark, PhonemeAnalyzer, PhonemeResult,
    PhonemeTrack, WordMark, WordTrack,
)
from src.analyzer.xtiming import XTimingWriter
from src import export as export_mod
from src.analyzer.result import AnalysisResult


# ── Shared mock factory ────────────────────────────────────────────────────────

def _make_whisperx_mock():
    """Return a whisperx mock simulating transcription of 'HELLO WORLD'."""
    mock_wx = MagicMock()
    mock_wx.load_model.return_value.transcribe.return_value = {
        "segments": [{"text": "hello world", "start": 1.0, "end": 3.0}],
        "language": "en",
    }
    mock_wx.load_audio.return_value = [0.0] * 160000  # 10 s at 16 kHz
    mock_wx.load_align_model.return_value = (MagicMock(), MagicMock())
    mock_wx.align.return_value = {
        "word_segments": [
            {"word": "hello", "start": 1.0, "end": 2.0, "score": 0.9},
            {"word": "world", "start": 2.1, "end": 3.0, "score": 0.85},
        ]
    }
    return mock_wx


@pytest.fixture()
def phoneme_result_from_analyzer(tmp_path):
    """Run PhonemeAnalyzer with mock whisperx; return the PhonemeResult."""
    fixture_wav = Path(__file__).parent.parent / "fixtures" / "10s_vocals.wav"
    if not fixture_wav.exists():
        pytest.skip("Fixture 10s_vocals.wav not found")

    mock_wx = _make_whisperx_mock()
    analyzer = PhonemeAnalyzer(model_name="base")
    # Inject tiny cmudict so we don't need nltk download
    analyzer._cmu_dict = {
        "hello": [["HH", "AH0", "L", "OW1"]],
        "world": [["W", "ER1", "L", "D"]],
    }

    with patch.dict("sys.modules", {"whisperx": mock_wx}):
        result = analyzer.analyze(str(fixture_wav), "test_song.mp3")
    return result


# ── T018: End-to-end pipeline tests ──────────────────────────────────────────

class TestPhonemePipeline:
    def test_analyzer_returns_phoneme_result(self, phoneme_result_from_analyzer):
        assert phoneme_result_from_analyzer is not None
        assert isinstance(phoneme_result_from_analyzer, PhonemeResult)

    def test_word_track_has_words(self, phoneme_result_from_analyzer):
        marks = phoneme_result_from_analyzer.word_track.marks
        assert len(marks) == 2
        assert marks[0].label == "HELLO"
        assert marks[1].label == "WORLD"

    def test_phoneme_track_not_empty(self, phoneme_result_from_analyzer):
        assert len(phoneme_result_from_analyzer.phoneme_track.marks) > 0

    def test_phoneme_labels_valid(self, phoneme_result_from_analyzer):
        valid = {"AI", "E", "O", "WQ", "L", "MBP", "FV", "etc"}
        for pm in phoneme_result_from_analyzer.phoneme_track.marks:
            assert pm.label in valid

    def test_phoneme_timing_contiguous_within_words(self, phoneme_result_from_analyzer):
        """Phoneme marks within a single word must be contiguous (no gaps)."""
        word_marks = phoneme_result_from_analyzer.word_track.marks
        phoneme_marks = phoneme_result_from_analyzer.phoneme_track.marks

        for wm in word_marks:
            # Find phonemes that belong to this word's time range
            word_phonemes = [
                pm for pm in phoneme_marks
                if pm.start_ms >= wm.start_ms and pm.end_ms <= wm.end_ms
            ]
            for a, b in zip(word_phonemes, word_phonemes[1:]):
                assert a.end_ms == b.start_ms, (
                    f"Gap within word {wm.label}: {a} vs {b}"
                )

    def test_xtiming_written_and_valid_xml(self, phoneme_result_from_analyzer, tmp_path):
        out = str(tmp_path / "test.xtiming")
        XTimingWriter().write(phoneme_result_from_analyzer, out)
        assert Path(out).exists()
        tree = ET.parse(out)
        assert tree.getroot().tag == "timings"

    def test_xtiming_has_three_layers(self, phoneme_result_from_analyzer, tmp_path):
        out = str(tmp_path / "test.xtiming")
        XTimingWriter().write(phoneme_result_from_analyzer, out)
        tree = ET.parse(out)
        timing = tree.getroot().find("timing")
        assert len(timing.findall("EffectLayer")) == 3

    def test_json_round_trip_with_phoneme_result(self, phoneme_result_from_analyzer, tmp_path):
        ar = AnalysisResult(
            schema_version="1.0",
            source_file="test_song.mp3",
            filename="test_song.mp3",
            duration_ms=10000,
            sample_rate=44100,
            estimated_tempo_bpm=120.0,
            run_timestamp="2026-03-22T10:00:00",
            algorithms=[],
            timing_tracks=[],
            phoneme_result=phoneme_result_from_analyzer,
        )
        out = tmp_path / "test.json"
        export_mod.write(ar, str(out))

        assert out.exists()
        loaded = export_mod.read(str(out))
        assert loaded.phoneme_result is not None
        assert loaded.phoneme_result.language == "en"
        assert len(loaded.phoneme_result.word_track.marks) == 2

    def test_json_without_phonemes_null(self, tmp_path):
        ar = AnalysisResult(
            schema_version="1.0",
            source_file="test_song.mp3",
            filename="test_song.mp3",
            duration_ms=10000,
            sample_rate=44100,
            estimated_tempo_bpm=120.0,
            run_timestamp="2026-03-22T10:00:00",
            algorithms=[],
            timing_tracks=[],
        )
        out = tmp_path / "test.json"
        export_mod.write(ar, str(out))
        data = json.loads(out.read_text())
        assert data["phoneme_result"] is None

    def test_backward_compat_old_json(self, tmp_path):
        """Old JSON files without phoneme_result load without error."""
        old_json = {
            "schema_version": "1.0",
            "source_file": "test.mp3",
            "filename": "test.mp3",
            "duration_ms": 10000,
            "sample_rate": 44100,
            "estimated_tempo_bpm": 120.0,
            "run_timestamp": "2026-01-01T00:00:00",
            "algorithms": [],
            "timing_tracks": [],
        }
        p = tmp_path / "old.json"
        p.write_text(json.dumps(old_json))
        loaded = export_mod.read(str(p))
        assert loaded.phoneme_result is None
