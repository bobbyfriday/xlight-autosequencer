"""Acceptance-gate orchestrator.

Runs three suites against a corpus and aggregates results into a single
exit-code + JSON report:

1. Analyzer suite  — AnalyzerBaseline check for every fixture.
2. Generator suite — existing quality calibration check (delegated).
3. UI suite        — pytest -m ui (spawns Flask + Vite via conftest fixtures).

Exit codes (highest-priority wins):
    8 — infrastructure failure (missing Playwright without --skip-ui,
         corpus download failed, unexpected exception)
    4 — no baseline for one or more required suites
    6 — at least one suite detected a regression
    0 — all suites pass
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.evaluation import analyzer_baseline
from src.evaluation.analyzer_baseline import (
    AnalyzerBaseline,
    BaselineMissingError,
    FixtureSnapshot,
    Violation,
)
from src.evaluation.corpus_resolver import CorpusEntry, resolve_corpus

EXIT_PASS = 0
EXIT_NO_BASELINE = 4
EXIT_REGRESSION = 6
EXIT_INFRA = 8

REPORTS_DIR = Path("tests/golden/reports")


@dataclass
class GateOptions:
    quick: bool = False
    skip_ui: bool = False
    fixture_slug: Optional[str] = None
    report_path: Optional[Path] = None
    analyzer_baseline_path: Path = analyzer_baseline.DEFAULT_BASELINE_PATH


@dataclass
class SuiteResult:
    name: str
    status: str  # "pass" | "fail" | "skip" | "no-baseline" | "infra-error"
    fixtures_checked: int = 0
    violations: list[dict] = field(default_factory=list)
    message: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "fixtures_checked": self.fixtures_checked,
            "violations": list(self.violations),
            "message": self.message,
            "duration_seconds": round(self.duration_seconds, 3),
        }


@dataclass
class GateReport:
    started_at: str
    duration_seconds: float
    exit_code: int
    corpus: list[str]
    suites: dict[str, SuiteResult] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "started_at": self.started_at,
            "duration_seconds": round(self.duration_seconds, 3),
            "exit_code": self.exit_code,
            "corpus": list(self.corpus),
            "suites": {name: r.to_dict() for name, r in self.suites.items()},
        }


# ---------- Analyzer suite ----------

def _snapshot_fixture_live(entry: CorpusEntry) -> FixtureSnapshot:
    """Run the full analyzer pipeline on one fixture; return its snapshot.

    Imported lazily so unit tests of the orchestrator don't pay the
    analyzer import cost unless they exercise this path.
    """
    from src.analyzer.runner import AnalysisRunner, default_algorithms
    from src.evaluation.analyzer_baseline import TrackSnapshot

    runner = AnalysisRunner(algorithms=default_algorithms())
    result = runner.run(str(entry.path))
    algorithms = {
        t.algorithm_name: TrackSnapshot.from_track(t) for t in result.timing_tracks
    }
    return FixtureSnapshot(fixture_slug=entry.slug, algorithms=algorithms)


def run_analyzer_suite(
    corpus: list[CorpusEntry],
    baseline_path: Path,
    *,
    snapshot_fn=None,
) -> SuiteResult:
    # Resolve snapshot function at call time so tests can patch the module-level
    # `_snapshot_fixture_live` and have the patch take effect.
    if snapshot_fn is None:
        snapshot_fn = _snapshot_fixture_live
    start = time.monotonic()
    try:
        baseline = analyzer_baseline.load(baseline_path)
    except BaselineMissingError as exc:
        return SuiteResult(
            "analyzer",
            status="no-baseline",
            message=str(exc),
            duration_seconds=time.monotonic() - start,
        )

    violations: list[Violation] = []
    for entry in corpus:
        if entry.source == "local":
            # Local corpus entries aren't in the CC0 baseline — skip silently.
            # They still run through the generator suite for benchmark value.
            continue
        current = snapshot_fn(entry)
        violations.extend(analyzer_baseline.check_fixture(baseline, entry.slug, current))

    return SuiteResult(
        "analyzer",
        status="fail" if violations else "pass",
        fixtures_checked=sum(1 for e in corpus if e.source != "local"),
        violations=[
            {
                "fixture_slug": v.fixture_slug,
                "algorithm_name": v.algorithm_name,
                "kind": v.kind,
                "detail": v.detail,
            }
            for v in violations
        ],
        duration_seconds=time.monotonic() - start,
    )


# ---------- Generator suite (delegates to existing check logic) ----------

def run_generator_suite(corpus: list[CorpusEntry]) -> SuiteResult:
    """Wrap `xlight-evaluate check` with the acceptance-gate corpus.

    The existing generator baseline treats the corpus as a filesystem directory
    with MP3s. We materialize a view to the CC0 directory (already the default)
    and shell out to the check logic.
    """
    start = time.monotonic()
    # Generator baseline comparison requires a fully generated .xsq per fixture,
    # which requires the generator pipeline. Delegate to `xlight-evaluate check`
    # as a subprocess so the gate preserves the existing exit-code contract
    # rather than re-implementing it.
    cmd = ["xlight-evaluate", "check"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return SuiteResult(
            "generator", status="infra-error",
            message=f"xlight-evaluate check failed to run: {exc}",
            duration_seconds=time.monotonic() - start,
        )

    duration = time.monotonic() - start

    if proc.returncode == 0:
        return SuiteResult(
            "generator", status="pass",
            fixtures_checked=len([e for e in corpus if e.source == "cc0"]),
            duration_seconds=duration,
        )
    if proc.returncode == 4:
        return SuiteResult(
            "generator", status="no-baseline",
            message=(proc.stdout + proc.stderr).strip()[:500],
            duration_seconds=duration,
        )
    if proc.returncode == 6:
        return SuiteResult(
            "generator", status="fail",
            message=(proc.stdout + proc.stderr).strip()[:500],
            duration_seconds=duration,
        )
    return SuiteResult(
        "generator", status="infra-error",
        message=f"unexpected exit code {proc.returncode}: {(proc.stdout + proc.stderr)[:300]}",
        duration_seconds=duration,
    )


# ---------- UI suite ----------

def _playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


def run_ui_suite(skip: bool = False, quick: bool = False) -> SuiteResult:
    """Run the UI flow suite.

    - skip=True: do nothing; report `skip`. Used for --skip-ui or offline runs.
    - quick=True: run only the content flow (-m 'ui and content') — one
      upload + real analysis + manifest assertions, ~90s.
    - default: run all UI flows (-m ui) — smoke flows + content flow, ~2-3 min.
    """
    start = time.monotonic()
    if skip:
        return SuiteResult("ui", status="skip", message="--skip-ui passed")

    if not _playwright_available():
        return SuiteResult(
            "ui", status="infra-error",
            message="playwright not installed; pass --skip-ui to run without the UI suite",
            duration_seconds=time.monotonic() - start,
        )

    marker = "ui and content" if quick else "ui"
    # Auto-capture artifacts on failure for post-hoc debugging:
    #   --screenshot=only-on-failure       → PNG of final state
    #   --video=retain-on-failure          → WebM of full run
    #   --tracing=retain-on-failure        → Playwright trace.zip (timeline replay)
    # Lands under test-results/<test-id>/. View traces with `playwright show-trace`.
    cmd = [
        "pytest", "-m", marker, "--tb=short", "-v",
        "--screenshot=only-on-failure",
        "--video=retain-on-failure",
        "--tracing=retain-on-failure",
        "--full-page-screenshot",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return SuiteResult(
            "ui", status="infra-error",
            message=f"pytest -m ui failed to run: {exc}",
            duration_seconds=time.monotonic() - start,
        )

    duration = time.monotonic() - start
    if proc.returncode == 0:
        return SuiteResult("ui", status="pass", duration_seconds=duration)
    if proc.returncode == 5:
        return SuiteResult(
            "ui", status="skip",
            message="no UI tests collected (expected in environments without UI flows)",
            duration_seconds=duration,
        )
    return SuiteResult(
        "ui", status="fail",
        message=(proc.stdout + proc.stderr).strip()[-2000:],
        duration_seconds=duration,
    )


# ---------- Top-level orchestrator ----------

def _aggregate_exit_code(suites: dict[str, SuiteResult]) -> int:
    statuses = [s.status for s in suites.values()]
    if "infra-error" in statuses:
        return EXIT_INFRA
    if "no-baseline" in statuses:
        return EXIT_NO_BASELINE
    if "fail" in statuses:
        return EXIT_REGRESSION
    return EXIT_PASS


def run_gate(options: GateOptions) -> GateReport:
    start_wall = time.monotonic()
    started_iso = datetime.now(timezone.utc).isoformat()

    # Resolve corpus up front — a corpus-resolution error is infra.
    try:
        corpus = resolve_corpus(
            quick=options.quick,
            fixture_slug=options.fixture_slug,
        )
    except (FileNotFoundError, ValueError) as exc:
        report = GateReport(
            started_at=started_iso,
            duration_seconds=time.monotonic() - start_wall,
            exit_code=EXIT_INFRA,
            corpus=[],
            suites={
                "corpus": SuiteResult(
                    "corpus", status="infra-error", message=str(exc)
                )
            },
        )
        _write_report(report, options.report_path)
        return report

    suites: dict[str, SuiteResult] = {}

    # Analyzer suite (skipped entirely when quick mode tests only a single
    # fixture? No — quick mode still exercises the analyzer; it just uses
    # one fixture to save time.)
    suites["analyzer"] = run_analyzer_suite(corpus, options.analyzer_baseline_path)

    # Generator suite
    suites["generator"] = run_generator_suite(corpus)

    # UI suite — --quick runs only the content flow (smoke + assertions on
    # one fixture); full mode runs all flows.
    suites["ui"] = run_ui_suite(skip=options.skip_ui, quick=options.quick)

    exit_code = _aggregate_exit_code(suites)
    report = GateReport(
        started_at=started_iso,
        duration_seconds=time.monotonic() - start_wall,
        exit_code=exit_code,
        corpus=[e.slug for e in corpus],
        suites=suites,
    )
    _write_report(report, options.report_path)
    return report


def _write_report(report: GateReport, explicit_path: Optional[Path]) -> Path:
    if explicit_path is not None:
        path = explicit_path
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = report.started_at.replace(":", "-").replace("+00-00", "Z").replace(".", "-")
        path = REPORTS_DIR / f"gate-{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    return path


def format_summary(report: GateReport) -> str:
    """Human-readable summary table for stdout."""
    lines = [
        f"Acceptance gate — {report.started_at}",
        f"Corpus: {', '.join(report.corpus) or '(empty)'}",
        f"Duration: {report.duration_seconds:.1f}s",
        "",
        f"{'SUITE':<12} {'STATUS':<14} {'CHECKED':<8} {'DURATION':<10}",
        "-" * 50,
    ]
    for name, suite in report.suites.items():
        lines.append(
            f"{name:<12} {suite.status.upper():<14} "
            f"{suite.fixtures_checked:<8} {suite.duration_seconds:>7.1f}s"
        )
        if suite.message:
            lines.append(f"    → {suite.message}")
        for v in suite.violations[:5]:
            lines.append(
                f"    × {v['fixture_slug']}/{v['algorithm_name']} ({v['kind']}): {v['detail']}"
            )
        if len(suite.violations) > 5:
            lines.append(f"    … and {len(suite.violations) - 5} more")

    lines.append("")
    verdict = {
        EXIT_PASS: "PASS — all suites passed",
        EXIT_REGRESSION: "FAIL — regression detected",
        EXIT_NO_BASELINE: "NO-BASELINE — run snapshot first",
        EXIT_INFRA: "INFRA — setup problem, re-run",
    }.get(report.exit_code, f"UNKNOWN ({report.exit_code})")
    lines.append(f"Verdict: {verdict} (exit {report.exit_code})")
    return "\n".join(lines)
