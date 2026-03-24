"""XTimingWriter: generate xLights .xtiming XML from PhonemeResult."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

from src.analyzer.phonemes import PhonemeResult

if TYPE_CHECKING:
    from src.analyzer.result import TimingTrack


def _sanitize_name(filename: str) -> str:
    """Strip extension and replace non-alphanumeric chars with underscores."""
    stem = Path(filename).stem
    return re.sub(r"[^A-Za-z0-9_\-]", "_", stem)


class XTimingWriter:
    """Write a PhonemeResult to a .xtiming XML file in xLights format."""

    SOURCE_VERSION = "2024.01"

    def write(self, result: PhonemeResult, output_path: str) -> None:
        """
        Generate .xtiming XML and write to output_path.

        Structure:
            timings
              timing name="{song_name}" SourceVersion="2024.01"
                EffectLayer  (layer 1: full lyrics block)
                EffectLayer  (layer 2: words)
                EffectLayer  (layer 3: phonemes)
        """
        song_name = _sanitize_name(result.source_file)

        root = ET.Element("timings")
        timing_el = ET.SubElement(root, "timing")
        timing_el.set("name", song_name)
        timing_el.set("SourceVersion", self.SOURCE_VERSION)

        # Layer 1: full lyrics as a single Effect
        layer1 = ET.SubElement(timing_el, "EffectLayer")
        lb = result.lyrics_block
        ET.SubElement(layer1, "Effect").attrib.update({
            "label": lb.text,
            "starttime": str(lb.start_ms),
            "endtime": str(lb.end_ms),
        })

        # Layer 2: word-level timing
        layer2 = ET.SubElement(timing_el, "EffectLayer")
        for wm in result.word_track.marks:
            ET.SubElement(layer2, "Effect").attrib.update({
                "label": wm.label,
                "starttime": str(wm.start_ms),
                "endtime": str(wm.end_ms),
            })

        # Layer 3: phoneme-level timing
        layer3 = ET.SubElement(timing_el, "EffectLayer")
        for pm in result.phoneme_track.marks:
            ET.SubElement(layer3, "Effect").attrib.update({
                "label": pm.label,
                "starttime": str(pm.start_ms),
                "endtime": str(pm.end_ms),
            })

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(fh, encoding="unicode", xml_declaration=False)


_FRAME_DURATION_MS = 50  # default inter-mark duration when a single mark exists


def _build_timing_element(
    root: ET.Element,
    track: "TimingTrack",
    track_name: str,
) -> ET.Element:
    """Append a <timing> element with one EffectLayer to *root* and return it."""
    timing_el = ET.SubElement(root, "timing")
    timing_el.set("name", track_name)
    timing_el.set("SourceVersion", XTimingWriter.SOURCE_VERSION)

    layer = ET.SubElement(timing_el, "EffectLayer")
    marks = track.marks
    for i, mark in enumerate(marks):
        start = mark.time_ms
        if i + 1 < len(marks):
            end = marks[i + 1].time_ms
        else:
            end = start + _FRAME_DURATION_MS
        ET.SubElement(layer, "Effect").attrib.update({
            "label": track.element_type,
            "starttime": str(start),
            "endtime": str(end),
        })
    return timing_el


def _write_xml(root: ET.Element, output_path: str) -> None:
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(fh, encoding="unicode", xml_declaration=False)


def write_timing_track(
    track: "TimingTrack",
    output_path: str,
    track_name: str,
) -> None:
    """Export a single TimingTrack as a one-layer .xtiming file.

    Each mark becomes an <Effect> with starttime=mark.time_ms and
    endtime derived from the next mark (or starttime + 50 ms for the last mark).
    The label is set to the track's element_type.
    """
    root = ET.Element("timings")
    _build_timing_element(root, track, track_name)
    _write_xml(root, output_path)


def write_timing_tracks(
    tracks: "list[TimingTrack]",
    output_path: str,
) -> None:
    """Export multiple TimingTracks as separate <timing> elements in one file.

    Each track becomes its own <timing name=track.name> element containing
    a single EffectLayer.
    """
    root = ET.Element("timings")
    for track in tracks:
        _build_timing_element(root, track, track.name)
    _write_xml(root, output_path)
