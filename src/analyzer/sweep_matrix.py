"""Sweep matrix: comprehensive algorithm×stem×parameter sweep engine."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Optional

from src.analyzer.stem_affinity import StemAffinity, AFFINITY_TABLE

__all__ = [
    "SweepMatrixConfig",
    "SweepMatrix",
    "Permutation",
    "PermutationResult",
    "MatrixSweepRunner",
    "auto_select_best",
]


@dataclass
class Permutation:
    """A single algorithm×stem×params combination to execute."""
    algorithm: str
    stem: str
    parameters: dict
    result_type: str  # "timing" or "value_curve"


@dataclass
class SweepMatrix:
    """The computed cross-product of algorithms × stems × parameter permutations."""
    permutations: list[Permutation]
    total_count: int
    exceeds_cap: bool = False
    cap: int = 500


@dataclass
class PermutationResult:
    """Result of executing a single permutation."""
    algorithm: str
    stem: str
    parameters: dict
    result_type: str
    quality_score: float = 0.0
    mark_count: int = 0
    sample_count: int = 0
    avg_interval_ms: int = 0
    dynamic_range: float = 0.0
    status: str = "pending"  # "success", "failed", "skipped"
    error: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "stem": self.stem,
            "parameters": self.parameters,
            "result_type": self.result_type,
            "quality_score": self.quality_score,
            "mark_count": self.mark_count,
            "sample_count": self.sample_count,
            "avg_interval_ms": self.avg_interval_ms,
            "dynamic_range": self.dynamic_range,
            "status": self.status,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class SweepMatrixConfig:
    """Configuration for a sweep matrix run."""
    algorithms: list[str] = field(default_factory=lambda: list(AFFINITY_TABLE.keys()))
    available_stems: set[str] = field(default_factory=lambda: {"full_mix"})
    param_overrides: dict[str, dict[str, list]] = field(default_factory=dict)
    max_permutations: int = 500
    sample_duration_s: float = 30.0
    sample_start_ms: Optional[int] = None
    output_dir: Optional[str] = None
    dry_run: bool = False

    def build_matrix(self) -> SweepMatrix:
        """Compute the full permutation cross-product."""
        permutations: list[Permutation] = []
        seen: set[tuple] = set()

        for algo in self.algorithms:
            stems = StemAffinity.get_stems(algo, self.available_stems)
            output_type = StemAffinity.get_output_type(algo)

            # Get parameter ranges
            param_names = StemAffinity.get_tunable_params(algo)
            overrides = self.param_overrides.get(algo, {})

            if not param_names and not overrides:
                # No tunable params — one run per stem
                param_combos = [{}]
            else:
                # Build parameter value lists
                param_values: dict[str, list] = {}
                for pname in param_names:
                    if pname in overrides:
                        param_values[pname] = overrides[pname]
                    # else: auto-derived values will be filled by the runner
                # Add any override-only params not in the affinity table
                for pname, pvals in overrides.items():
                    if pname not in param_values:
                        param_values[pname] = pvals

                if param_values:
                    keys = sorted(param_values.keys())
                    combos = list(itertools.product(*(param_values[k] for k in keys)))
                    param_combos = [dict(zip(keys, vals)) for vals in combos]
                else:
                    param_combos = [{}]

            for stem in stems:
                for params in param_combos:
                    # Deduplicate
                    key = (algo, stem, tuple(sorted(params.items())))
                    if key in seen:
                        continue
                    seen.add(key)
                    permutations.append(Permutation(
                        algorithm=algo,
                        stem=stem,
                        parameters=dict(params),
                        result_type=output_type,
                    ))

        exceeds = len(permutations) > self.max_permutations
        return SweepMatrix(
            permutations=permutations,
            total_count=len(permutations),
            exceeds_cap=exceeds,
            cap=self.max_permutations,
        )

    @classmethod
    def from_toml(
        cls,
        path: str,
        available_stems: set[str] | None = None,
    ) -> "SweepMatrixConfig":
        """Load configuration from a TOML file."""
        import tomllib
        from pathlib import Path

        with open(path, "rb") as f:
            data = tomllib.load(f)

        algorithms = data.get("algorithms", list(AFFINITY_TABLE.keys()))
        stems_list = data.get("stems")
        max_perm = data.get("max_permutations", 500)
        sample_dur = data.get("sample_duration_s", 30.0)

        # If stems specified in TOML, use those + full_mix
        if stems_list and available_stems:
            filtered = {s for s in stems_list if s in available_stems}
            filtered.add("full_mix")
        elif available_stems:
            filtered = available_stems
        else:
            filtered = {"full_mix"}

        # Parse per-algorithm param overrides
        param_overrides: dict[str, dict[str, list]] = {}
        params_section = data.get("params", {})
        for algo_name, algo_params in params_section.items():
            param_overrides[algo_name] = {
                k: list(v) if isinstance(v, (list, tuple)) else [v]
                for k, v in algo_params.items()
            }

        return cls(
            algorithms=algorithms,
            available_stems=filtered,
            param_overrides=param_overrides,
            max_permutations=max_perm,
            sample_duration_s=sample_dur,
        )


def auto_select_best(
    results: list[PermutationResult],
) -> dict[str, PermutationResult]:
    """Select the best result per algorithm (highest score, tie-break: fewer marks)."""
    best: dict[str, PermutationResult] = {}
    for r in results:
        if r.status != "success":
            continue
        current = best.get(r.algorithm)
        if current is None:
            best[r.algorithm] = r
        elif r.quality_score > current.quality_score:
            best[r.algorithm] = r
        elif (r.quality_score == current.quality_score
              and r.mark_count < current.mark_count):
            best[r.algorithm] = r
    return best


class MatrixSweepRunner:
    """Execute a sweep matrix: run every permutation, collect results, write reports.

    Usage::

        config = SweepMatrixConfig(...)
        matrix = config.build_matrix()
        runner = MatrixSweepRunner(audio_path="song.mp3", matrix=matrix)
        results = runner.run(progress_callback=my_callback)
    """

    def __init__(
        self,
        audio_path: str,
        matrix: SweepMatrix,
        output_dir: str | None = None,
        sample_start_ms: int | None = None,
        sample_end_ms: int | None = None,
    ) -> None:
        self._audio_path = audio_path
        self._matrix = matrix
        self._output_dir = output_dir
        self._sample_start_ms = sample_start_ms
        self._sample_end_ms = sample_end_ms

    def run(
        self,
        progress_callback=None,
    ) -> list[PermutationResult]:
        """Execute all permutations and return results.

        If *progress_callback* is provided, it is called with
        ``(permutation_index, total, permutation, result)`` after each run.
        """
        import json
        import time
        from pathlib import Path

        from src.analyzer.scorer import score_track
        from src.analyzer.value_curve_scorer import score_value_curve
        from src.log import get_logger

        log = get_logger("xlight.sweep_matrix")

        output_dir = Path(self._output_dir) if self._output_dir else Path(self._audio_path).parent / "analysis" / "sweep"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load audio segment
        import librosa
        import numpy as np
        y, sr = librosa.load(self._audio_path, sr=None, mono=True)

        if self._sample_start_ms is not None and self._sample_end_ms is not None:
            start_sample = int(self._sample_start_ms / 1000 * sr)
            end_sample = int(self._sample_end_ms / 1000 * sr)
            y_segment = y[start_sample:end_sample]
            log.info("Using segment %dms–%dms (%d samples)",
                     self._sample_start_ms, self._sample_end_ms, len(y_segment))
        else:
            y_segment = y
            log.info("Using full audio (%d samples)", len(y_segment))

        # Load stems if available
        stems_dir = Path(self._audio_path).parent / "stems"
        if not stems_dir.exists():
            stems_dir = Path(self._audio_path).parent / ".stems"

        total = self._matrix.total_count
        results: list[PermutationResult] = []
        # Per-algorithm result accumulator (includes full marks)
        algo_results: dict[str, list[dict]] = {}

        for idx, perm in enumerate(self._matrix.permutations):
            t0 = time.perf_counter()
            result = PermutationResult(
                algorithm=perm.algorithm,
                stem=perm.stem,
                parameters=perm.parameters,
                result_type=perm.result_type,
            )

            try:
                # Select audio for this stem
                if perm.stem == "full_mix":
                    audio = y_segment
                else:
                    stem_file = stems_dir / f"{perm.stem}.mp3"
                    if stem_file.exists():
                        stem_y, stem_sr = librosa.load(str(stem_file), sr=sr, mono=True)
                        if self._sample_start_ms is not None and self._sample_end_ms is not None:
                            start_s = int(self._sample_start_ms / 1000 * stem_sr)
                            end_s = int(self._sample_end_ms / 1000 * stem_sr)
                            audio = stem_y[start_s:end_s]
                        else:
                            audio = stem_y
                    else:
                        log.warning("Stem %s not found, skipping", perm.stem)
                        result.status = "skipped"
                        result.error = f"Stem file not found: {stem_file}"
                        results.append(result)
                        continue

                # Find and run the algorithm
                from src.analyzer.runner import default_algorithms
                algo_instance = None
                for algo in default_algorithms():
                    if algo.name == perm.algorithm:
                        algo_instance = algo
                        break

                if algo_instance is None:
                    result.status = "skipped"
                    result.error = f"Algorithm {perm.algorithm} not found"
                    results.append(result)
                    continue

                # Apply parameters
                if perm.parameters:
                    algo_instance.parameters = dict(perm.parameters)

                track = algo_instance.run(audio, sr)

                if track is not None:
                    if perm.result_type == "value_curve" and hasattr(track, "value_curve"):
                        curve = track.value_curve
                        result.quality_score = score_value_curve(curve)
                        result.sample_count = len(curve)
                        result.dynamic_range = (max(curve) - min(curve)) if curve else 0
                    else:
                        result.quality_score = score_track(track)
                        result.mark_count = track.mark_count
                        result.avg_interval_ms = track.avg_interval_ms

                    result.status = "success"

                    # Store full data for per-algorithm file
                    full_entry = result.to_dict()
                    full_entry["marks"] = [{"time_ms": m.time_ms} for m in track.marks]
                    if hasattr(track, "value_curve"):
                        full_entry["value_curve"] = track.value_curve
                    algo_results.setdefault(perm.algorithm, []).append(full_entry)
                else:
                    result.status = "failed"
                    result.error = "Algorithm returned None"

            except Exception as exc:
                result.status = "failed"
                result.error = str(exc)[:200]
                log.warning("Permutation %s/%s failed: %s", perm.algorithm, perm.stem, exc)

            result.duration_ms = int((time.perf_counter() - t0) * 1000)
            results.append(result)

            if progress_callback:
                progress_callback(idx + 1, total, perm, result)

        # Write unified report (metadata only)
        report = {
            "audio_path": str(Path(self._audio_path).resolve()),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "segment_start_ms": self._sample_start_ms,
            "segment_end_ms": self._sample_end_ms,
            "total_permutations": total,
            "completed": sum(1 for r in results if r.status == "success"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "results": [r.to_dict() for r in results],
            "best_per_algorithm": {
                algo: r.to_dict()
                for algo, r in auto_select_best(results).items()
            },
        }
        report_path = output_dir / "sweep_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        log.info("Wrote unified report: %s (%d results)", report_path, len(results))

        # Write per-algorithm files (full data)
        for algo_name, algo_entries in algo_results.items():
            algo_path = output_dir / f"sweep_{algo_name}.json"
            algo_path.write_text(json.dumps({
                "algorithm": algo_name,
                "results": algo_entries,
            }, indent=2), encoding="utf-8")

        log.info("Wrote %d per-algorithm files", len(algo_results))

        return results
