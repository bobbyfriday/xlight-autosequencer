"""005: Parameter sweep runner for Vamp algorithms."""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np

from src.analyzer.audio import load
from src.analyzer.result import TimingTrack
from src.analyzer.scorer import score_track

_VALID_STEMS = {"full_mix", "drums", "bass", "vocals", "guitar", "piano", "other"}


# ---------------------------------------------------------------------------
# SweepConfig
# ---------------------------------------------------------------------------

@dataclass
class SweepConfig:
    """Defines which parameter values and stems to try for a single algorithm."""

    algorithm: str
    sweep_params: dict[str, list]
    fixed_params: dict = field(default_factory=dict)
    stems: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str) -> "SweepConfig":
        """Load and validate a sweep config from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        if "algorithm" not in data:
            raise KeyError("Sweep config is missing required key 'algorithm'")

        sweep = data.get("sweep", {})
        fixed = data.get("fixed", {})
        stems = data.get("stems", [])

        # Check for keys appearing in both sweep and fixed
        overlap = set(sweep) & set(fixed)
        if overlap:
            raise ValueError(
                f"Parameter(s) {sorted(overlap)} appear in both 'sweep' and 'fixed'"
            )

        return cls(
            algorithm=data["algorithm"],
            sweep_params=sweep,
            fixed_params=fixed,
            stems=list(stems),
        )

    def permutations(self, default_stem: str = "full_mix") -> Iterator[tuple[str, dict]]:
        """
        Yield (stem, params_dict) for every combination of stems × parameter values.

        When stems is empty, yields (default_stem, params_dict) for each param combo.
        """
        active_stems = self.stems if self.stems else [default_stem]

        if not self.sweep_params:
            for stem in active_stems:
                yield stem, dict(self.fixed_params)
            return

        keys = list(self.sweep_params.keys())
        value_lists = [self.sweep_params[k] for k in keys]

        for stem in active_stems:
            for combo in itertools.product(*value_lists):
                params = dict(zip(keys, combo))
                params.update(self.fixed_params)
                yield stem, params

    def permutation_count(self, default_stem: str = "full_mix") -> int:
        """Return the total number of permutations this config will run."""
        stem_count = len(self.stems) if self.stems else 1
        param_count = 1
        for values in self.sweep_params.values():
            param_count *= len(values)
        return stem_count * param_count

    def validate(
        self,
        plugin_key: str,
        discovery,
    ) -> list[str]:
        """
        Validate stem names and parameter values.

        Returns a list of error strings; empty = valid.
        """
        errors: list[str] = []

        for stem in self.stems:
            if stem not in _VALID_STEMS:
                errors.append(
                    f"Invalid stem '{stem}'. Valid stems: {sorted(_VALID_STEMS)}"
                )

        all_params = dict(self.fixed_params)
        for values in self.sweep_params.values():
            pass  # validate each unique value
        # Validate every distinct value for each sweep param
        for param_key, values in self.sweep_params.items():
            for v in values:
                param_errors = discovery.validate_params(plugin_key, {param_key: v})
                errors.extend(param_errors)
        # Validate fixed params as a batch
        if self.fixed_params:
            errors.extend(discovery.validate_params(plugin_key, self.fixed_params))

        return errors


# ---------------------------------------------------------------------------
# PermutationResult
# ---------------------------------------------------------------------------

@dataclass
class PermutationResult:
    """The outcome of one sweep run — one specific (stem, params) combination."""

    rank: int
    stem: str
    parameters: dict
    quality_score: float
    mark_count: int
    avg_interval_ms: int
    track: TimingTrack

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "stem": self.stem,
            "parameters": self.parameters,
            "quality_score": round(self.quality_score, 4),
            "mark_count": self.mark_count,
            "avg_interval_ms": self.avg_interval_ms,
            "marks": [
                {"time_ms": m.time_ms, "confidence": m.confidence}
                for m in self.track.marks
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PermutationResult":
        from src.analyzer.result import TimingMark
        marks = [
            TimingMark(time_ms=m["time_ms"], confidence=m.get("confidence"))
            for m in d.get("marks", [])
        ]
        track = TimingTrack(
            name="sweep_result",
            algorithm_name=d.get("parameters", {}).get("_algorithm", "unknown"),
            element_type="beat",
            marks=marks,
            quality_score=d.get("quality_score", 0.0),
        )
        return cls(
            rank=d["rank"],
            stem=d["stem"],
            parameters=d["parameters"],
            quality_score=d["quality_score"],
            mark_count=d["mark_count"],
            avg_interval_ms=d["avg_interval_ms"],
            track=track,
        )


# ---------------------------------------------------------------------------
# SweepReport
# ---------------------------------------------------------------------------

@dataclass
class SweepReport:
    """Complete output of a sweep run."""

    schema_version: str
    audio_file: str
    algorithm: str
    plugin_key: str
    stems_tested: list[str]
    sweep_params: dict[str, list]
    fixed_params: dict
    permutation_count: int
    generated_at: str
    results: list[PermutationResult]  # sorted by quality_score desc

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "audio_file": self.audio_file,
            "algorithm": self.algorithm,
            "plugin_key": self.plugin_key,
            "stems_tested": self.stems_tested,
            "sweep_params": self.sweep_params,
            "fixed_params": self.fixed_params,
            "permutation_count": self.permutation_count,
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SweepReport":
        return cls(
            schema_version=d["schema_version"],
            audio_file=d["audio_file"],
            algorithm=d["algorithm"],
            plugin_key=d.get("plugin_key", ""),
            stems_tested=d.get("stems_tested", []),
            sweep_params=d.get("sweep_params", {}),
            fixed_params=d.get("fixed_params", {}),
            permutation_count=d["permutation_count"],
            generated_at=d["generated_at"],
            results=[PermutationResult.from_dict(r) for r in d.get("results", [])],
        )

    def write(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def read(cls, path: str) -> "SweepReport":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


# ---------------------------------------------------------------------------
# SavedConfig
# ---------------------------------------------------------------------------

@dataclass
class SavedConfig:
    """A named, saved configuration extracted from a sweep report result."""

    name: str
    algorithm: str
    stem: str
    parameters: dict
    source_sweep: str
    created_at: str

    def save(self, config_dir: Path | str | None = None) -> Path:
        """Write this config as <config_dir>/<name>.json, creating the dir if needed."""
        if config_dir is None:
            config_dir = Path.home() / ".xlight" / "sweep_configs"
        config_dir = Path(config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        out = config_dir / f"{self.name}.json"
        out.write_text(json.dumps({
            "name": self.name,
            "algorithm": self.algorithm,
            "stem": self.stem,
            "parameters": self.parameters,
            "source_sweep": self.source_sweep,
            "created_at": self.created_at,
        }, indent=2), encoding="utf-8")
        return out

    @classmethod
    def load(cls, name: str, config_dir: Path | str | None = None) -> "SavedConfig":
        """Load a saved config by name from config_dir."""
        if config_dir is None:
            config_dir = Path.home() / ".xlight" / "sweep_configs"
        path = Path(config_dir) / f"{name}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            name=data["name"],
            algorithm=data["algorithm"],
            stem=data["stem"],
            parameters=data["parameters"],
            source_sweep=data.get("source_sweep", ""),
            created_at=data.get("created_at", ""),
        )

    @classmethod
    def from_report(cls, report: "SweepReport", rank: int, name: str) -> "SavedConfig":
        """Extract a SavedConfig from a SweepReport by rank (1-based)."""
        matches = [r for r in report.results if r.rank == rank]
        if not matches:
            raise ValueError(f"No result with rank={rank} in report (max rank={len(report.results)})")
        result = matches[0]
        return cls(
            name=name,
            algorithm=report.algorithm,
            stem=result.stem,
            parameters=result.parameters,
            source_sweep=report.audio_file,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# SweepRunner
# ---------------------------------------------------------------------------

class SweepRunner:
    """
    Runs all permutations of a SweepConfig against a single audio file.

    Usage:
        runner = SweepRunner(build_algorithm_registry())
        report = runner.run("song.mp3", config, stems)
    """

    def __init__(self, algorithm_registry: dict[str, type]) -> None:
        self._registry = algorithm_registry

    def run(
        self,
        audio_path: str,
        config: SweepConfig,
        stems=None,
        progress_callback=None,
    ) -> SweepReport:
        """
        Load audio once, iterate all permutations, score each, return ranked report.

        stems: optional StemSet (from StemSeparator); when None full_mix is used
               for all permutations.
        progress_callback: optional callable(index, total, stem, params, mark_count, score)
        """
        audio, sr, meta = load(audio_path)

        algo_cls = self._registry.get(config.algorithm)
        if algo_cls is None:
            raise ValueError(
                f"Algorithm '{config.algorithm}' not found in registry. "
                f"Available: {sorted(self._registry)}"
            )

        default_stem = algo_cls.preferred_stem if hasattr(algo_cls, "preferred_stem") else "full_mix"
        perms = list(config.permutations(default_stem=default_stem))
        total = len(perms)
        raw_results: list[PermutationResult] = []

        for idx, (stem, params) in enumerate(perms):
            algo_audio = _select_audio(stem, audio, sr, stems)

            # Instantiate algorithm with overridden parameters
            algo = algo_cls()
            algo.parameters = dict(params)

            try:
                track = algo.run(algo_audio, sr)
            except Exception as exc:
                print(
                    f"WARNING: sweep permutation failed (stem={stem}, params={params}): {exc}",
                    file=__import__("sys").stderr,
                )
                track = None

            if track is None:
                from src.analyzer.result import TimingTrack as _TT
                track = _TT(
                    name=config.algorithm,
                    algorithm_name=config.algorithm,
                    element_type="beat",
                    marks=[],
                    quality_score=0.0,
                )

            qs = score_track(track)
            track.quality_score = qs

            result = PermutationResult(
                rank=0,  # assigned after sorting
                stem=stem,
                parameters=params,
                quality_score=qs,
                mark_count=track.mark_count,
                avg_interval_ms=track.avg_interval_ms,
                track=track,
            )
            raw_results.append(result)

            if progress_callback:
                progress_callback(idx + 1, total, stem, params, track.mark_count, qs)

        # Sort descending by quality score, assign ranks
        raw_results.sort(key=lambda r: r.quality_score, reverse=True)
        for rank_idx, r in enumerate(raw_results, start=1):
            r.rank = rank_idx

        if raw_results and all(r.mark_count == 0 for r in raw_results):
            import sys as _sys
            print(
                "WARNING: all sweep permutations returned zero marks. "
                "Check audio file, stem selection, and plugin parameters.",
                file=_sys.stderr,
            )

        stems_tested = list(dict.fromkeys(r.stem for r in raw_results))

        return SweepReport(
            schema_version="1.0",
            audio_file=str(Path(audio_path).resolve()),
            algorithm=config.algorithm,
            plugin_key=getattr(algo_cls, "plugin_key", "") or "",
            stems_tested=stems_tested,
            sweep_params=config.sweep_params,
            fixed_params=config.fixed_params,
            permutation_count=total,
            generated_at=datetime.now(timezone.utc).isoformat(),
            results=raw_results,
        )


# ---------------------------------------------------------------------------
# Algorithm registry
# ---------------------------------------------------------------------------

def build_algorithm_registry() -> dict[str, type]:
    """Return a dict mapping algorithm name → class for all Vamp algorithms."""
    registry: dict[str, type] = {}
    try:
        from src.analyzer.algorithms.vamp_beats import (
            QMBeatAlgorithm, QMBarAlgorithm, BeatRootAlgorithm,
        )
        from src.analyzer.algorithms.vamp_onsets import (
            QMOnsetComplexAlgorithm, QMOnsetHFCAlgorithm, QMOnsetPhaseAlgorithm,
        )
        from src.analyzer.algorithms.vamp_structure import (
            QMSegmenterAlgorithm, QMTempoAlgorithm,
        )
        from src.analyzer.algorithms.vamp_pitch import (
            PYINNotesAlgorithm, PYINPitchChangesAlgorithm,
        )
        from src.analyzer.algorithms.vamp_harmony import (
            ChordinoAlgorithm, NNLSChromaAlgorithm,
        )
        for cls in (
            QMBeatAlgorithm, QMBarAlgorithm, BeatRootAlgorithm,
            QMOnsetComplexAlgorithm, QMOnsetHFCAlgorithm, QMOnsetPhaseAlgorithm,
            QMSegmenterAlgorithm, QMTempoAlgorithm,
            PYINNotesAlgorithm, PYINPitchChangesAlgorithm,
            ChordinoAlgorithm, NNLSChromaAlgorithm,
        ):
            registry[cls.name] = cls
    except ImportError:
        pass
    return registry


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _select_audio(
    stem: str,
    full_mix: np.ndarray,
    full_mix_sr: int,
    stems=None,
) -> np.ndarray:
    """Return the audio array for the requested stem, falling back to full_mix."""
    if stems is None or stem == "full_mix":
        return full_mix
    arr = stems.get(stem)
    if arr is None:
        return full_mix
    stem_sr = stems.sample_rate
    if stem_sr != full_mix_sr:
        import librosa as _lr
        arr = _lr.resample(arr, orig_sr=stem_sr, target_sr=full_mix_sr)
    return arr
