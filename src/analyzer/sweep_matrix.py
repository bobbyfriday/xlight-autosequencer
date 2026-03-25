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
