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
