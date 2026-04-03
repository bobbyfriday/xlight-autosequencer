"""Baseline comparison — save, load, and compare validation baselines.

A baseline captures scorer results for a set of test scenarios. Future runs
compare against the baseline to detect regressions (score drops beyond a
configurable tolerance).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.validation.report import ValidationReport
from src.validation.scorers import ScorerResult

logger = logging.getLogger(__name__)


@dataclass
class BaselineEntry:
    """Baseline scores for a single test scenario."""

    scenario_name: str
    scores: dict[str, float]  # scorer_name -> score (0-100)
    overall: float = 0.0


@dataclass
class Baseline:
    """Collection of baseline entries for regression comparison."""

    version: str
    entries: list[BaselineEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "entries": [
                {
                    "scenario_name": e.scenario_name,
                    "scores": e.scores,
                    "overall": e.overall,
                }
                for e in self.entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Baseline:
        entries = [
            BaselineEntry(
                scenario_name=e["scenario_name"],
                scores=e["scores"],
                overall=e["overall"],
            )
            for e in data["entries"]
        ]
        return cls(version=data["version"], entries=entries)


@dataclass
class RegressionResult:
    """Result of comparing a report against a baseline entry."""

    scenario_name: str
    passed: bool
    regressions: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    details: dict[str, dict[str, float]] = field(default_factory=dict)


def save_baseline(baseline: Baseline, path: Path) -> None:
    """Write a baseline to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline.to_dict(), indent=2))
    logger.info("Saved baseline (%d entries) to %s", len(baseline.entries), path)


def load_baseline(path: Path) -> Baseline:
    """Load a baseline from JSON."""
    data = json.loads(path.read_text())
    return Baseline.from_dict(data)


def create_baseline_entry(
    scenario_name: str,
    report: ValidationReport,
) -> BaselineEntry:
    """Create a baseline entry from a validation report."""
    scores = {r.name: r.score for r in report.scorer_results}
    return BaselineEntry(
        scenario_name=scenario_name,
        scores=scores,
        overall=report.overall_score,
    )


def compare_against_baseline(
    report: ValidationReport,
    baseline_entry: BaselineEntry,
    tolerance_pct: float = 5.0,
) -> RegressionResult:
    """Compare a validation report against a baseline entry.

    A regression is detected when any scorer's score drops by more than
    tolerance_pct percentage points below the baseline.

    Args:
        report: Current validation report.
        baseline_entry: Baseline to compare against.
        tolerance_pct: Maximum allowed score drop (percentage points).

    Returns:
        RegressionResult with pass/fail and per-scorer deltas.
    """
    regressions: list[str] = []
    improvements: list[str] = []
    details: dict[str, dict[str, float]] = {}

    for scorer_result in report.scorer_results:
        name = scorer_result.name
        current = scorer_result.score
        baseline_score = baseline_entry.scores.get(name)

        if baseline_score is None:
            # New scorer not in baseline — skip comparison
            continue

        delta = current - baseline_score
        details[name] = {
            "current": current,
            "baseline": baseline_score,
            "delta": round(delta, 1),
        }

        if delta < -tolerance_pct:
            regressions.append(
                f"{name}: {current:.1f} (was {baseline_score:.1f}, "
                f"dropped {abs(delta):.1f}pts, tolerance={tolerance_pct})"
            )
        elif delta > tolerance_pct:
            improvements.append(
                f"{name}: {current:.1f} (was {baseline_score:.1f}, "
                f"improved {delta:.1f}pts)"
            )

    return RegressionResult(
        scenario_name=baseline_entry.scenario_name,
        passed=len(regressions) == 0,
        regressions=regressions,
        improvements=improvements,
        details=details,
    )


def compare_report_to_baseline_file(
    report: ValidationReport,
    scenario_name: str,
    baseline_path: Path,
    tolerance_pct: float = 5.0,
) -> RegressionResult:
    """Load a baseline file and compare a report against the named scenario."""
    baseline = load_baseline(baseline_path)
    entry = None
    for e in baseline.entries:
        if e.scenario_name == scenario_name:
            entry = e
            break

    if entry is None:
        return RegressionResult(
            scenario_name=scenario_name,
            passed=True,
            improvements=[f"New scenario '{scenario_name}' — no baseline to compare"],
        )

    return compare_against_baseline(report, entry, tolerance_pct)
