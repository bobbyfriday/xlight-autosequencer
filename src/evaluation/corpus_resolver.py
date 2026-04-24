"""Corpus resolver for the acceptance gate.

Combines the default CC0 corpus (tests/fixtures/cc0_music/) with an optional
local augmentation at ~/.xlight/eval_corpus.json, so developers can test against
their own music library without committing anything.

The CC0 corpus is hash-verified (see download_fixtures.py); local entries are
trusted — they reference files the user chose to include.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "fixtures"
    / "cc0_music"
    / "manifest.json"
)
LOCAL_MANIFEST = Path.home() / ".xlight" / "eval_corpus.json"


@dataclass(frozen=True)
class CorpusEntry:
    slug: str
    path: Path
    genre: str | None
    tempo_bpm: float | None
    expected_section_count: int | None
    source: str  # "cc0" | "local"


def load_default_corpus(manifest_path: Path = DEFAULT_MANIFEST) -> list[CorpusEntry]:
    """Load the 4 CC0 tracks from the committed manifest."""
    data = json.loads(manifest_path.read_text())
    corpus_dir = manifest_path.parent
    entries: list[CorpusEntry] = []
    for t in data["tracks"]:
        entries.append(
            CorpusEntry(
                slug=t["slug"],
                path=corpus_dir / t["filename"],
                genre=t.get("genre"),
                tempo_bpm=t.get("tempo_bpm"),
                expected_section_count=t.get("expected_section_count"),
                source="cc0",
            )
        )
    return entries


def load_local_corpus(manifest_path: Path = LOCAL_MANIFEST) -> list[CorpusEntry]:
    """Load optional local entries from ~/.xlight/eval_corpus.json.

    Returns [] if the file does not exist. Malformed files raise ValueError
    with a clear message rather than crashing mid-run.
    """
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Local corpus manifest at {manifest_path} is not valid JSON: {exc}"
        ) from exc

    raw_entries = data.get("entries", [])
    if not isinstance(raw_entries, list):
        raise ValueError(
            f"Local corpus manifest at {manifest_path} must have an 'entries' list; "
            f"got {type(raw_entries).__name__}."
        )

    entries: list[CorpusEntry] = []
    for idx, e in enumerate(raw_entries):
        path_str = e.get("path")
        slug = e.get("slug")
        if not path_str or not slug:
            raise ValueError(
                f"Local corpus entry #{idx} missing required 'path' or 'slug'. "
                f"Got keys: {sorted(e.keys())}"
            )
        path = Path(path_str).expanduser()
        if not path.is_absolute():
            raise ValueError(
                f"Local corpus entry '{slug}' has non-absolute path: {path_str}. "
                "Local corpus paths must be absolute so the gate runs identically "
                "regardless of CWD."
            )
        if not path.exists():
            raise ValueError(f"Local corpus entry '{slug}' points at missing file: {path}")
        entries.append(
            CorpusEntry(
                slug=slug,
                path=path,
                genre=e.get("genre"),
                tempo_bpm=e.get("tempo_bpm"),
                expected_section_count=e.get("expected_section_count"),
                source="local",
            )
        )
    return entries


def resolve_corpus(
    *,
    quick: bool = False,
    fixture_slug: str | None = None,
) -> list[CorpusEntry]:
    """Build the active corpus for a gate run.

    Default: CC0 corpus + any local entries.
    Quick mode: a single CC0 track (manifest's quick_mode_default_slug, falling
      back to maple_leaf_rag).
    fixture_slug: restrict to a single entry by slug (matches across both sources).
    """
    cc0 = load_default_corpus()
    local = load_local_corpus()
    combined = cc0 + local

    if fixture_slug:
        matched = [e for e in combined if e.slug == fixture_slug]
        if not matched:
            raise ValueError(
                f"No corpus entry with slug '{fixture_slug}'. "
                f"Available: {sorted(e.slug for e in combined)}"
            )
        return matched

    if quick:
        manifest = json.loads(DEFAULT_MANIFEST.read_text())
        quick_slug = manifest.get("quick_mode_default_slug", "maple_leaf_rag")
        return [e for e in cc0 if e.slug == quick_slug] or cc0[:1]

    return combined
