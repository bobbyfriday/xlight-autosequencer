"""T034: Vamp structural segmentation and tempo algorithms."""
from __future__ import annotations

import numpy as np

from src.analyzer.algorithms.base import Algorithm
from src.analyzer.result import TimingMark, TimingTrack


def _vamp_outputs_to_marks(outputs: list) -> list[TimingMark]:
    marks = []
    for output in outputs:
        t = output["timestamp"]
        t_sec = t.to_float() if hasattr(t, "to_float") else float(t)
        marks.append(TimingMark(time_ms=int(round(t_sec * 1000)), confidence=None))
    return marks


class QMSegmenterAlgorithm(Algorithm):
    """QM structural segmenter via Vamp qm-vamp-plugins:qm-segmenter."""

    name = "qm_segments"
    element_type = "structure"
    library = "vamp"
    plugin_key = "qm-vamp-plugins:qm-segmenter"
    parameters = {}

    def _run(self, audio: np.ndarray, sample_rate: int) -> TimingTrack:
        import vamp

        outputs = vamp.collect(audio, sample_rate, self.plugin_key, output="segmentation")
        marks = _vamp_outputs_to_marks(outputs.get("list", []))
        return TimingTrack(
            name=self.name,
            algorithm_name=self.name,
            element_type=self.element_type,
            marks=marks,
            quality_score=0.0,
        )


class QMTempoAlgorithm(Algorithm):
    """QM tempo tracker beat output via Vamp qm-vamp-plugins:qm-tempotracker."""

    name = "qm_tempo"
    element_type = "tempo"
    library = "vamp"
    plugin_key = "qm-vamp-plugins:qm-tempotracker"
    parameters = {"output": "tempo"}

    def _run(self, audio: np.ndarray, sample_rate: int) -> TimingTrack:
        import vamp

        outputs = vamp.collect(audio, sample_rate, self.plugin_key, output="tempo")
        marks = _vamp_outputs_to_marks(outputs.get("list", []))
        return TimingTrack(
            name=self.name,
            algorithm_name=self.name,
            element_type=self.element_type,
            marks=marks,
            quality_score=0.0,
        )
