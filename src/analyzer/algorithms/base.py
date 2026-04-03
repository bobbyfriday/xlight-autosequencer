"""T010: Abstract base class for all analysis algorithms."""
from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod

import numpy as np

from src.analyzer.result import AnalysisAlgorithm, TimingTrack


class Algorithm(ABC):
    """
    Each algorithm implementation must inherit from this class.

    Subclasses declare `name`, `element_type`, `library`, `plugin_key`,
    and `parameters`, then implement `_run()`.

    The public `run()` method wraps `_run()` with exception handling so
    that a single failing algorithm never crashes the runner.
    """

    name: str
    element_type: str
    library: str
    plugin_key: str | None = None
    parameters: dict = {}
    preferred_stem: str = "full_mix"
    vamp_output: str | None = None
    # T034: explicit dependency declaration for pipeline ordering.
    # full_mix algorithms use ["audio_load"]; stem algorithms use ["stem_separation"].
    depends_on: list[str] = []

    @abstractmethod
    def _run(self, audio: np.ndarray, sample_rate: int) -> TimingTrack:
        """Execute analysis and return a TimingTrack. Raise on failure."""
        raise NotImplementedError

    def run(self, audio: np.ndarray, sample_rate: int) -> TimingTrack | None:
        """
        Public entry point. Returns TimingTrack on success, None on failure.
        Recoverable failures are logged to stderr but do NOT propagate.
        MemoryError, SystemExit, and KeyboardInterrupt always propagate.
        """
        try:
            track = self._run(audio, sample_rate)
            return track
        except (MemoryError, SystemExit, KeyboardInterrupt):
            raise
        except Exception as exc:
            import traceback
            print(
                f"WARNING: {self.name} failed ({type(exc).__name__}): {exc}",
                file=sys.stderr,
            )
            if os.environ.get("XLIGHT_VERBOSE"):
                traceback.print_exc(file=sys.stderr)
            return None

    def metadata(self) -> AnalysisAlgorithm:
        """Return an AnalysisAlgorithm descriptor for this instance."""
        return AnalysisAlgorithm(
            name=self.name,
            element_type=self.element_type,
            library=self.library,
            plugin_key=self.plugin_key,
            parameters=dict(self.parameters),
        )
