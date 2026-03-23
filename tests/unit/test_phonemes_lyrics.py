"""T019-T020: US2 tests for lyrics-assisted alignment and mismatch detection."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_aligned_wx(word_segments):
    """Factory for a whisperx mock with the given word_segments."""
    mock_wx = MagicMock()
    mock_wx.load_model.return_value.transcribe.return_value = {
        "segments": [{"text": "hello world", "start": 0.0, "end": 3.0}],
        "language": "en",
    }
    mock_wx.load_audio.return_value = [0.0] * 160000
    mock_wx.load_align_model.return_value = (MagicMock(), MagicMock())
    mock_wx.align.return_value = {"word_segments": word_segments}
    return mock_wx


@pytest.fixture()
def tiny_cmu():
    return {
        "hello": [["HH", "AH0", "L", "OW1"]],
        "world": [["W", "ER1", "L", "D"]],
    }


@pytest.fixture()
def fixture_wav(tmp_path):
    """Minimal WAV placeholder (PhonemeAnalyzer uses whisperx.load_audio mock)."""
    p = tmp_path / "vocals.wav"
    p.write_bytes(b"RIFF" + b"\x00" * 36)
    return str(p)


@pytest.fixture()
def lyrics_file(tmp_path):
    p = tmp_path / "lyrics.txt"
    p.write_text("hello world")
    return str(p)


# ── T019: Lyrics-assisted alignment ───────────────────────────────────────────

class TestLyricsAssistedAlignment:
    def test_lyrics_source_is_provided_when_lyrics_given(
        self, fixture_wav, lyrics_file, tiny_cmu
    ):
        """When --lyrics is used and alignment succeeds, lyrics_source == 'provided'."""
        word_segs = [
            {"word": "hello", "start": 0.5, "end": 1.5, "score": 0.9},
            {"word": "world", "start": 1.6, "end": 2.5, "score": 0.85},
        ]
        mock_wx = _make_aligned_wx(word_segs)

        from src.analyzer.phonemes import PhonemeAnalyzer
        a = PhonemeAnalyzer()
        a._cmu_dict = tiny_cmu

        with patch.dict("sys.modules", {"whisperx": mock_wx}):
            result = a.analyze(fixture_wav, "song.mp3", lyrics_path=lyrics_file)

        assert result is not None
        assert result.word_track.lyrics_source == "provided"

    def test_words_from_lyrics_not_transcription(
        self, fixture_wav, lyrics_file, tiny_cmu
    ):
        """Words come from the alignment of provided lyrics, not auto-transcription."""
        # Mock provides word segments that match the lyrics
        word_segs = [
            {"word": "hello", "start": 0.5, "end": 1.5, "score": 0.9},
            {"word": "world", "start": 1.6, "end": 2.5, "score": 0.85},
        ]
        mock_wx = _make_aligned_wx(word_segs)

        from src.analyzer.phonemes import PhonemeAnalyzer
        a = PhonemeAnalyzer()
        a._cmu_dict = tiny_cmu

        with patch.dict("sys.modules", {"whisperx": mock_wx}):
            result = a.analyze(fixture_wav, "song.mp3", lyrics_path=lyrics_file)

        labels = [m.label for m in result.word_track.marks]
        assert "HELLO" in labels
        assert "WORLD" in labels

    def test_lyrics_alignment_produces_phonemes(
        self, fixture_wav, lyrics_file, tiny_cmu
    ):
        word_segs = [
            {"word": "hello", "start": 0.5, "end": 1.5, "score": 0.9},
            {"word": "world", "start": 1.6, "end": 2.5, "score": 0.85},
        ]
        mock_wx = _make_aligned_wx(word_segs)

        from src.analyzer.phonemes import PhonemeAnalyzer
        a = PhonemeAnalyzer()
        a._cmu_dict = tiny_cmu

        with patch.dict("sys.modules", {"whisperx": mock_wx}):
            result = a.analyze(fixture_wav, "song.mp3", lyrics_path=lyrics_file)

        assert len(result.phoneme_track.marks) > 0

    def test_missing_lyrics_file_falls_back_to_audio_only(
        self, fixture_wav, tiny_cmu
    ):
        """If lyrics file doesn't exist, fall back to audio-only and emit warning."""
        word_segs = [
            {"word": "hello", "start": 0.5, "end": 1.5, "score": 0.9},
        ]
        mock_wx = _make_aligned_wx(word_segs)

        from src.analyzer.phonemes import PhonemeAnalyzer
        a = PhonemeAnalyzer()
        a._cmu_dict = tiny_cmu

        with patch.dict("sys.modules", {"whisperx": mock_wx}):
            result = a.analyze(fixture_wav, "song.mp3", lyrics_path="/nonexistent/lyrics.txt")

        # Should fall back to auto mode
        assert result is not None
        assert result.word_track.lyrics_source == "auto"
        assert any("Cannot read lyrics" in w for w in a.warnings)


# ── T020: Mismatch detection ───────────────────────────────────────────────────

class TestLyricsMismatchDetection:
    def test_low_coverage_falls_back_to_audio_only(
        self, fixture_wav, tiny_cmu, tmp_path
    ):
        """If < 50% of provided words align, fall back to audio-only with warning."""
        lyrics_file = tmp_path / "lyrics.txt"
        lyrics_file.write_text("hello world foo bar baz qux seven eight nine ten")

        # Only 2 of 10 words get timestamps → 20% coverage → should fall back
        word_segs_lyrics = [
            {"word": "hello", "start": 0.5, "end": 1.0, "score": 0.9},
            {"word": "world", "start": 1.1, "end": 1.5, "score": 0.8},
            # Other 8 words have no timestamps (score None)
            {"word": "foo", "start": None, "end": None, "score": None},
            {"word": "bar", "start": None, "end": None, "score": None},
            {"word": "baz", "start": None, "end": None, "score": None},
            {"word": "qux", "start": None, "end": None, "score": None},
            {"word": "seven", "start": None, "end": None, "score": None},
            {"word": "eight", "start": None, "end": None, "score": None},
            {"word": "nine", "start": None, "end": None, "score": None},
            {"word": "ten", "start": None, "end": None, "score": None},
        ]
        # After falling back, auto-transcription returns just hello/world
        word_segs_auto = [
            {"word": "hello", "start": 0.5, "end": 1.0, "score": 0.9},
            {"word": "world", "start": 1.1, "end": 1.5, "score": 0.8},
        ]

        mock_wx = MagicMock()
        mock_wx.load_model.return_value.transcribe.return_value = {
            "segments": [{"text": "hello world", "start": 0.0, "end": 3.0}],
            "language": "en",
        }
        mock_wx.load_audio.return_value = [0.0] * 160000
        mock_wx.load_align_model.return_value = (MagicMock(), MagicMock())
        # First call (lyrics alignment), second call (fallback auto alignment)
        mock_wx.align.side_effect = [
            {"word_segments": word_segs_lyrics},
            {"word_segments": word_segs_auto},
        ]

        from src.analyzer.phonemes import PhonemeAnalyzer
        a = PhonemeAnalyzer()
        a._cmu_dict = tiny_cmu

        with patch.dict("sys.modules", {"whisperx": mock_wx}):
            result = a.analyze(fixture_wav, "song.mp3", lyrics_path=str(lyrics_file))

        assert result is not None
        # Should have fallen back to auto
        assert result.word_track.lyrics_source == "auto"
        # Warning should mention mismatch
        assert any("mismatch" in w.lower() for w in a.warnings)

    def test_high_coverage_uses_provided_lyrics(
        self, fixture_wav, lyrics_file, tiny_cmu
    ):
        """If >= 50% of provided words align, use provided lyrics source."""
        word_segs = [
            {"word": "hello", "start": 0.5, "end": 1.5, "score": 0.9},
            {"word": "world", "start": 1.6, "end": 2.5, "score": 0.85},
        ]
        mock_wx = _make_aligned_wx(word_segs)

        from src.analyzer.phonemes import PhonemeAnalyzer
        a = PhonemeAnalyzer()
        a._cmu_dict = tiny_cmu

        with patch.dict("sys.modules", {"whisperx": mock_wx}):
            result = a.analyze(fixture_wav, "song.mp3", lyrics_path=lyrics_file)

        assert result.word_track.lyrics_source == "provided"
        assert not any("mismatch" in w.lower() for w in a.warnings)

    def test_mismatch_warning_contains_percentage(
        self, fixture_wav, tiny_cmu, tmp_path
    ):
        """The mismatch warning must include the alignment percentage."""
        lyrics_file = tmp_path / "lyrics.txt"
        lyrics_file.write_text("hello world foo bar baz qux seven eight nine ten")

        # Only 2 of 10 words aligned → 20%
        word_segs_lyrics = (
            [{"word": "hello", "start": 0.5, "end": 1.0, "score": 0.9},
             {"word": "world", "start": 1.1, "end": 1.5, "score": 0.8}]
            + [{"word": w, "start": None, "end": None, "score": None}
               for w in ["foo", "bar", "baz", "qux", "seven", "eight", "nine", "ten"]]
        )
        word_segs_auto = [
            {"word": "hello", "start": 0.5, "end": 1.0, "score": 0.9},
        ]

        mock_wx = MagicMock()
        mock_wx.load_model.return_value.transcribe.return_value = {
            "segments": [{"text": "hello", "start": 0.0, "end": 2.0}],
            "language": "en",
        }
        mock_wx.load_audio.return_value = [0.0] * 160000
        mock_wx.load_align_model.return_value = (MagicMock(), MagicMock())
        mock_wx.align.side_effect = [
            {"word_segments": word_segs_lyrics},
            {"word_segments": word_segs_auto},
        ]

        from src.analyzer.phonemes import PhonemeAnalyzer
        a = PhonemeAnalyzer()
        a._cmu_dict = tiny_cmu

        with patch.dict("sys.modules", {"whisperx": mock_wx}):
            a.analyze(fixture_wav, "song.mp3", lyrics_path=str(lyrics_file))

        mismatch_warnings = [w for w in a.warnings if "mismatch" in w.lower()]
        assert mismatch_warnings
        # Warning should contain a percentage like "20%"
        assert "%" in mismatch_warnings[0]
