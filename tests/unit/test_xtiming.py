"""Tests for XTimingWriter: XML structure and output correctness."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.analyzer.phonemes import (
    LyricsBlock,
    PhonemeMark,
    PhonemeResult,
    PhonemeTrack,
    WordMark,
    WordTrack,
)
from src.analyzer.xtiming import XTimingWriter, _sanitize_name


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_result():
    return PhonemeResult(
        lyrics_block=LyricsBlock(text="HELLO WORLD", start_ms=1000, end_ms=3000),
        word_track=WordTrack(
            name="whisperx-words",
            marks=[
                WordMark(label="HELLO", start_ms=1000, end_ms=2000),
                WordMark(label="WORLD", start_ms=2100, end_ms=3000),
            ],
            lyrics_source="auto",
        ),
        phoneme_track=PhonemeTrack(
            name="whisperx-phonemes",
            marks=[
                PhonemeMark(label="etc", start_ms=1000, end_ms=1100),
                PhonemeMark(label="AI", start_ms=1100, end_ms=1500),
                PhonemeMark(label="L", start_ms=1500, end_ms=1700),
                PhonemeMark(label="O", start_ms=1700, end_ms=2000),
                PhonemeMark(label="WQ", start_ms=2100, end_ms=2400),
                PhonemeMark(label="E", start_ms=2400, end_ms=2700),
                PhonemeMark(label="L", start_ms=2700, end_ms=2850),
                PhonemeMark(label="etc", start_ms=2850, end_ms=3000),
            ],
        ),
        source_file="/music/my song.mp3",
        language="en",
        model_name="base",
    )


@pytest.fixture()
def xtiming_file(tmp_path, sample_result):
    writer = XTimingWriter()
    out = str(tmp_path / "test.xtiming")
    writer.write(sample_result, out)
    return out


# ── T011: XML structure validation ───────────────────────────────────────────

class TestXTimingStructure:
    def test_file_is_valid_xml(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        assert tree is not None

    def test_root_element_is_timings(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        root = tree.getroot()
        assert root.tag == "timings"

    def test_has_timing_child(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        root = tree.getroot()
        timing = root.find("timing")
        assert timing is not None

    def test_timing_has_source_version(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        timing = tree.getroot().find("timing")
        assert timing.get("SourceVersion") == "2024.01"

    def test_timing_has_name_attribute(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        timing = tree.getroot().find("timing")
        assert timing.get("name") is not None

    def test_exactly_three_effect_layers(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        timing = tree.getroot().find("timing")
        layers = timing.findall("EffectLayer")
        assert len(layers) == 3

    def test_layer1_has_one_effect_lyrics(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        layers = tree.getroot().find("timing").findall("EffectLayer")
        effects = layers[0].findall("Effect")
        assert len(effects) == 1
        assert effects[0].get("label") == "HELLO WORLD"

    def test_layer1_lyrics_starttime(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        layers = tree.getroot().find("timing").findall("EffectLayer")
        effect = layers[0].find("Effect")
        assert effect.get("starttime") == "1000"
        assert effect.get("endtime") == "3000"

    def test_layer2_word_count(self, xtiming_file, sample_result):
        tree = ET.parse(xtiming_file)
        layers = tree.getroot().find("timing").findall("EffectLayer")
        word_effects = layers[1].findall("Effect")
        assert len(word_effects) == len(sample_result.word_track.marks)

    def test_layer2_word_labels(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        layers = tree.getroot().find("timing").findall("EffectLayer")
        labels = [e.get("label") for e in layers[1].findall("Effect")]
        assert labels == ["HELLO", "WORLD"]

    def test_layer2_word_starttime(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        layers = tree.getroot().find("timing").findall("EffectLayer")
        first_word = layers[1].findall("Effect")[0]
        assert first_word.get("starttime") == "1000"
        assert first_word.get("endtime") == "2000"

    def test_layer3_phoneme_count(self, xtiming_file, sample_result):
        tree = ET.parse(xtiming_file)
        layers = tree.getroot().find("timing").findall("EffectLayer")
        phoneme_effects = layers[2].findall("Effect")
        assert len(phoneme_effects) == len(sample_result.phoneme_track.marks)

    def test_layer3_phoneme_labels_valid(self, xtiming_file):
        valid = {"AI", "E", "O", "WQ", "L", "MBP", "FV", "etc"}
        tree = ET.parse(xtiming_file)
        layers = tree.getroot().find("timing").findall("EffectLayer")
        for effect in layers[2].findall("Effect"):
            assert effect.get("label") in valid

    def test_effect_attributes_starttime_endtime_present(self, xtiming_file):
        tree = ET.parse(xtiming_file)
        timing = tree.getroot().find("timing")
        for layer in timing.findall("EffectLayer"):
            for effect in layer.findall("Effect"):
                assert effect.get("starttime") is not None
                assert effect.get("endtime") is not None

    def test_xml_declaration_present(self, tmp_path, sample_result):
        out = str(tmp_path / "decl.xtiming")
        XTimingWriter().write(sample_result, out)
        content = Path(out).read_text(encoding="utf-8")
        assert content.startswith("<?xml")


# ── T008: write_timing_track() for beat/onset TimingTrack objects ─────────────

class TestWriteTimingTrack:
    """T008 — write_timing_track() exports a TimingTrack as a one-layer .xtiming file."""

    def _make_track(self, times_ms: list[int], element_type: str = "beat") -> "TimingTrack":
        from src.analyzer.result import TimingMark, TimingTrack
        marks = [TimingMark(time_ms=t, confidence=None) for t in times_ms]
        return TimingTrack(
            name=f"test_{element_type}",
            algorithm_name="test_algo",
            element_type=element_type,
            marks=marks,
            quality_score=0.8,
        )

    def test_produces_valid_xml(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        track = self._make_track([1000, 2000, 3000])
        out = str(tmp_path / "beats.xtiming")
        write_timing_track(track, out, track_name="drums_beats")
        tree = ET.parse(out)
        assert tree is not None

    def test_root_is_timings(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        track = self._make_track([1000, 2000])
        out = str(tmp_path / "beats.xtiming")
        write_timing_track(track, out, track_name="drums_beats")
        root = ET.parse(out).getroot()
        assert root.tag == "timings"

    def test_timing_name_attribute(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        track = self._make_track([1000, 2000])
        out = str(tmp_path / "beats.xtiming")
        write_timing_track(track, out, track_name="drums_beats_qm")
        timing = ET.parse(out).getroot().find("timing")
        assert timing.get("name") == "drums_beats_qm"

    def test_one_effect_per_mark(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        times = [500, 1000, 1500, 2000]
        track = self._make_track(times)
        out = str(tmp_path / "beats.xtiming")
        write_timing_track(track, out, track_name="test")
        timing = ET.parse(out).getroot().find("timing")
        layer = timing.find("EffectLayer")
        effects = layer.findall("Effect")
        assert len(effects) == len(times)

    def test_starttime_matches_mark(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        track = self._make_track([1500])
        out = str(tmp_path / "beats.xtiming")
        write_timing_track(track, out, track_name="test")
        timing = ET.parse(out).getroot().find("timing")
        effect = timing.find("EffectLayer").find("Effect")
        assert effect.get("starttime") == "1500"

    def test_endtime_after_starttime(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        track = self._make_track([1000])
        out = str(tmp_path / "beats.xtiming")
        write_timing_track(track, out, track_name="test")
        timing = ET.parse(out).getroot().find("timing")
        effect = timing.find("EffectLayer").find("Effect")
        assert int(effect.get("endtime")) > int(effect.get("starttime"))

    def test_label_is_element_type(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        track = self._make_track([1000], element_type="onset")
        out = str(tmp_path / "onsets.xtiming")
        write_timing_track(track, out, track_name="test")
        timing = ET.parse(out).getroot().find("timing")
        effect = timing.find("EffectLayer").find("Effect")
        assert effect.get("label") == "onset"

    def test_xml_declaration_present(self, tmp_path):
        from src.analyzer.xtiming import write_timing_track
        track = self._make_track([1000])
        out = str(tmp_path / "beats.xtiming")
        write_timing_track(track, out, track_name="test")
        content = Path(out).read_text(encoding="utf-8")
        assert content.startswith("<?xml")


class TestWriteTimingTracks:
    """write_timing_tracks() exports multiple tracks as separate <timing> elements."""

    def _make_track(self, name: str, times_ms: list[int]) -> "TimingTrack":
        from src.analyzer.result import TimingMark, TimingTrack
        marks = [TimingMark(time_ms=t, confidence=None) for t in times_ms]
        return TimingTrack(
            name=name, algorithm_name="test", element_type="beat",
            marks=marks, quality_score=0.8,
        )

    def test_multiple_timing_elements(self, tmp_path):
        from src.analyzer.xtiming import write_timing_tracks
        tracks = [
            self._make_track("beats", [1000, 2000]),
            self._make_track("onsets", [500, 1500, 2500]),
        ]
        out = str(tmp_path / "multi.xtiming")
        write_timing_tracks(tracks, out)
        root = ET.parse(out).getroot()
        assert len(root.findall("timing")) == 2

    def test_timing_names_preserved(self, tmp_path):
        from src.analyzer.xtiming import write_timing_tracks
        tracks = [
            self._make_track("my_beats", [1000]),
            self._make_track("my_onsets", [500]),
        ]
        out = str(tmp_path / "multi.xtiming")
        write_timing_tracks(tracks, out)
        root = ET.parse(out).getroot()
        names = [t.get("name") for t in root.findall("timing")]
        assert "my_beats" in names
        assert "my_onsets" in names


class TestSanitizeName:
    def test_strips_extension(self):
        assert _sanitize_name("song.mp3") == "song"

    def test_replaces_spaces_with_underscore(self):
        name = _sanitize_name("/music/my song.mp3")
        assert " " not in name
        assert "my_song" in name

    def test_allows_alphanumeric_hyphens_underscores(self):
        name = _sanitize_name("my-song_v2.mp3")
        assert name == "my-song_v2"

    def test_strips_special_chars(self):
        name = _sanitize_name("hello (feat. artist).mp3")
        assert "(" not in name
        assert "." not in name
