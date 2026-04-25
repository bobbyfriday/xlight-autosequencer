"""Section-fidelity scoring — pure module shared by the manual script and the
acceptance gate's fourth suite.

The score is the per-section integer ``agreement_score`` that the story
builder writes into ``_story.json`` (one per section). This module only
aggregates and shapes those numbers; it does not recompute them. The
math therefore stays byte-compatible with PR #84's
``scripts/library_fidelity.py`` output, which is one of the
non-regression contracts of this change (per
``openspec/changes/agreement-score-operationalization/spec.md``).

The module is imported by:

- ``scripts/library_fidelity.py`` — manual diagnostic script, kept as a
  thin CLI wrapper over the helpers below.
- ``src/evaluation/acceptance_gate.py`` — fourth suite
  (``section_fidelity``) that compares the corpus's library-mean against
  ``tests/golden/section_fidelity/baseline.json`` and contributes to the
  gate's exit-code aggregation.

Keep it pure-functional. Module-level state would carry across test
runs (cerebrum DNR 2026-04-25 "module-level dicts accumulate").
"""
from __future__ import annotations

import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# Story-loading + per-song summary (extracted from scripts/library_fidelity.py)
# ---------------------------------------------------------------------------

def load_stories(songs_dir: Path) -> list[tuple[str, dict]]:
    """Find every ``*_story.json`` under *songs_dir* and return ``[(name, story)]``.

    Stories under a ``stems/`` directory are skipped (those are demucs
    outputs, not full-song stories).

    Unparseable JSON is logged to stderr and skipped — the manual script
    has done that since PR #84 and we preserve the contract.
    """
    out: list[tuple[str, dict]] = []
    for story_path in sorted(songs_dir.rglob("*_story.json")):
        if "stems" in story_path.parts:
            continue
        try:
            story = json.loads(story_path.read_text())
        except Exception as exc:
            print(f"  skipping {story_path} ({exc})", file=sys.stderr)
            continue
        song_name = story_path.stem.removesuffix("_story")
        out.append((song_name, story))
    return out


def summarize_song(name: str, story: dict) -> dict:
    """Per-song summary mirroring PR #84's library_fidelity.py output.

    The keys/values here drive both the manual script's printed table
    and the gate's per-fixture breakdown. Adding fields is fine; renaming
    or removing them breaks the script's stdout contract.
    """
    sections = story.get("sections") or []
    scores = [int(s.get("agreement_score", 0)) for s in sections]
    src = story.get("global", {}).get("section_source", "?")
    n_zero = sum(1 for s in scores if s == 0)
    n_strong = sum(1 for s in scores if s >= 3)
    zero_roles = [sections[i].get("role") for i, s in enumerate(scores) if s == 0]
    return {
        "name": name,
        "source": src,
        "n_sections": len(scores),
        "mean_score": statistics.mean(scores) if scores else 0.0,
        "median_score": statistics.median(scores) if scores else 0.0,
        "n_zero": n_zero,
        "n_strong": n_strong,
        "zero_roles": zero_roles,
    }


def print_report(per_song: list[dict]) -> None:
    """Stdout report — preserves PR #84's column order and totals lines.

    The exact format is part of the spec
    ("Script's stdout format is unchanged from PR #84").
    """
    if not per_song:
        print("No stories found.")
        return

    all_zero_sections = 0
    all_sections = 0
    for row in per_song:
        all_sections += row["n_sections"]
        all_zero_sections += row["n_zero"]

    print(f"{'song':<50} {'source':<10} {'n':<3} {'mean':<6} {'zeros':<6} {'strong':<7} {'zero_roles'}")
    print("-" * 120)
    for row in sorted(per_song, key=lambda r: -r["mean_score"]):
        zr = ",".join(row["zero_roles"][:4]) if row["zero_roles"] else ""
        if len(row["zero_roles"]) > 4:
            zr += f",…(+{len(row['zero_roles']) - 4})"
        print(
            f"{row['name']:<50} {row['source']:<10} "
            f"{row['n_sections']:<3} {row['mean_score']:<6.2f} "
            f"{row['n_zero']:<6} {row['n_strong']:<7} {zr}"
        )

    # Aggregate
    print()
    print(f"Library totals:")
    print(f"  Songs: {len(per_song)}")
    print(f"  Sections: {all_sections}")
    if all_sections:
        print(f"  Sections with score 0: {all_zero_sections} ({100*all_zero_sections/all_sections:.1f}%)")
    means = [r["mean_score"] for r in per_song]
    if means:
        print(f"  Per-song mean score — library mean:   {statistics.mean(means):.3f}")
        print(f"  Per-song mean score — library median: {statistics.median(means):.3f}")


# ---------------------------------------------------------------------------
# Aggregates consumed by the gate suite
# ---------------------------------------------------------------------------

def compute_library_mean(stories: Iterable[tuple[str, dict]]) -> float:
    """Mean of per-song mean agreement scores across the corpus.

    Empty corpus → 0.0 (matches the manual script's behavior when no
    sections exist anywhere).
    """
    means: list[float] = []
    for _name, story in stories:
        sections = story.get("sections") or []
        if not sections:
            continue
        scores = [int(s.get("agreement_score", 0)) for s in sections]
        if not scores:
            continue
        means.append(statistics.mean(scores))
    if not means:
        return 0.0
    return statistics.mean(means)


def compute_per_fixture_breakdown(stories: Iterable[tuple[str, dict]]) -> dict[str, dict]:
    """Per-song breakdown keyed by the song name (story stem).

    Used by the gate suite to point at *which* fixture regressed.
    """
    breakdown: dict[str, dict] = {}
    for name, story in stories:
        breakdown[name] = summarize_song(name, story)
    return breakdown


# ---------------------------------------------------------------------------
# Baseline file format (the JSON snapshot consumed by the gate suite)
# ---------------------------------------------------------------------------

DEFAULT_BASELINE_PATH = Path("tests/golden/section_fidelity/baseline.json")
DEFAULT_TOLERANCE = 0.10  # library_mean must not drop more than this from baseline


@dataclass
class FidelityBaseline:
    """Snapshot of corpus-wide fidelity for regression detection.

    The baseline records the library-mean *and* per-fixture means so a
    failure can identify which fixture moved.

    ``schema_version`` is bumped only on incompatible field changes; new
    fields default to absent and are read with ``dict.get``.
    """

    schema_version: int = 1
    library_mean: float = 0.0
    library_median: float = 0.0
    n_zero_pct: float = 0.0
    per_fixture: dict[str, dict] = field(default_factory=dict)
    generated_at: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "schema_version": self.schema_version,
            "library_mean": self.library_mean,
            "library_median": self.library_median,
            "n_zero_pct": self.n_zero_pct,
            "per_fixture": self.per_fixture,
        }
        if self.generated_at is not None:
            d["generated_at"] = self.generated_at
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "FidelityBaseline":
        return cls(
            schema_version=int(d.get("schema_version", 1)),
            library_mean=float(d.get("library_mean", 0.0)),
            library_median=float(d.get("library_median", 0.0)),
            n_zero_pct=float(d.get("n_zero_pct", 0.0)),
            per_fixture=dict(d.get("per_fixture", {})),
            generated_at=d.get("generated_at"),
        )


def build_baseline(per_song: list[dict]) -> FidelityBaseline:
    """Aggregate per-song summaries into a FidelityBaseline."""
    if not per_song:
        return FidelityBaseline()
    means = [r["mean_score"] for r in per_song]
    medians = [r["median_score"] for r in per_song]
    total_sections = sum(r["n_sections"] for r in per_song)
    total_zero = sum(r["n_zero"] for r in per_song)
    n_zero_pct = (100.0 * total_zero / total_sections) if total_sections else 0.0
    per_fixture = {r["name"]: {
        "source": r["source"],
        "n_sections": r["n_sections"],
        "mean_score": r["mean_score"],
        "median_score": r["median_score"],
        "n_zero": r["n_zero"],
        "n_strong": r["n_strong"],
    } for r in per_song}
    return FidelityBaseline(
        library_mean=statistics.mean(means),
        library_median=statistics.median(medians) if medians else 0.0,
        n_zero_pct=n_zero_pct,
        per_fixture=per_fixture,
    )


def load_baseline(path: Path) -> FidelityBaseline:
    """Load a baseline JSON. Raises FileNotFoundError if missing."""
    text = path.read_text()
    return FidelityBaseline.from_dict(json.loads(text))


def save_baseline(baseline: FidelityBaseline, path: Path) -> None:
    """Persist a baseline to disk, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline.to_dict(), indent=2) + "\n")


# ---------------------------------------------------------------------------
# Corpus story loading (used by the gate suite)
# ---------------------------------------------------------------------------

def load_stories_for_corpus(corpus) -> list[tuple[str, dict]]:
    """Load ``_story.json`` for every CorpusEntry that has one.

    Fixtures without a ``_story.json`` next to their MP3 are skipped
    silently — the analyzer suite already covers "story missing" cases
    (per spec "Fixture without _story.json is skipped without failure").

    Accepts an iterable of CorpusEntry-like objects with ``slug`` and
    ``path`` attributes; ``path`` is the MP3 file path.
    """
    out: list[tuple[str, dict]] = []
    for entry in corpus:
        mp3 = Path(entry.path)
        if not mp3.exists():
            continue
        story_path = mp3.with_name(f"{mp3.stem}_story.json")
        if not story_path.exists():
            # Some fixtures may store the story under a sibling .stories dir
            # or use a different naming convention. The acceptance corpus
            # uses the next-to-MP3 layout per the orchestrator
            # (`_output_dir(audio_path) / f"{stem}_hierarchy.json"`); the
            # story builder writes to the same dir. If it's not there,
            # skip silently.
            continue
        try:
            story = json.loads(story_path.read_text())
        except Exception as exc:
            print(f"  skipping {story_path} ({exc})", file=sys.stderr)
            continue
        out.append((entry.slug, story))
    return out
