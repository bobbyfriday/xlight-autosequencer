"""XTimingWriter: generate xLights .xtiming XML from PhonemeResult."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from src.analyzer.phonemes import PhonemeResult


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
