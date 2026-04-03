"""Validation report — runs all scorers and produces a structured summary."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.analyzer.result import HierarchyResult
from src.generator.models import SequencePlan
from src.validation.scorers import ALL_SCORERS, ScorerResult, run_all_scorers

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Complete validation report for a generated sequence."""

    song_title: str
    song_artist: str
    duration_ms: int
    num_sections: int
    total_effects: int
    scorer_results: list[ScorerResult]
    overall_score: float = 0.0

    def __post_init__(self) -> None:
        if self.scorer_results:
            self.overall_score = round(
                sum(r.score for r in self.scorer_results) / len(self.scorer_results),
                1,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "song_title": self.song_title,
            "song_artist": self.song_artist,
            "duration_ms": self.duration_ms,
            "num_sections": self.num_sections,
            "total_effects": self.total_effects,
            "overall_score": self.overall_score,
            "scorers": {
                r.name: {"score": r.score, "details": r.details}
                for r in self.scorer_results
            },
        }

    def summary_table(self) -> str:
        """Format a human-readable summary table."""
        lines = [
            f"Validation Report: {self.song_title} by {self.song_artist}",
            f"Duration: {self.duration_ms / 1000:.1f}s | "
            f"Sections: {self.num_sections} | "
            f"Effects: {self.total_effects}",
            "-" * 50,
            f"{'Scorer':<25} {'Score':>6}",
            "-" * 50,
        ]
        for r in self.scorer_results:
            lines.append(f"{r.name:<25} {r.score:>5.1f}%")
        lines.append("-" * 50)
        lines.append(f"{'OVERALL':<25} {self.overall_score:>5.1f}%")
        return "\n".join(lines)


def generate_report(
    plan: SequencePlan,
    hierarchy: HierarchyResult,
) -> ValidationReport:
    """Run all scorers and produce a ValidationReport."""
    total_effects = sum(
        len(placements)
        for assignment in plan.sections
        for placements in assignment.group_effects.values()
    )

    results = run_all_scorers(plan, hierarchy)

    return ValidationReport(
        song_title=plan.song_profile.title,
        song_artist=plan.song_profile.artist,
        duration_ms=hierarchy.duration_ms,
        num_sections=len(plan.sections),
        total_effects=total_effects,
        scorer_results=results,
    )


def save_report(report: ValidationReport, path: Path) -> None:
    """Write a validation report to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2))
    logger.info("Wrote validation report: %s", path)


def load_report(path: Path) -> ValidationReport:
    """Load a validation report from JSON."""
    data = json.loads(path.read_text())
    scorer_results = [
        ScorerResult(name=name, score=info["score"], details=info.get("details", {}))
        for name, info in data["scorers"].items()
    ]
    return ValidationReport(
        song_title=data["song_title"],
        song_artist=data["song_artist"],
        duration_ms=data["duration_ms"],
        num_sections=data["num_sections"],
        total_effects=data["total_effects"],
        scorer_results=scorer_results,
    )
