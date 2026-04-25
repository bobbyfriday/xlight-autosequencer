#!/usr/bin/env python3
"""Library-wide fidelity score — mean multi-source agreement across all stories.

Scans a directory of songs (each with a ``*_story.json`` next to the MP3),
collects every section's ``agreement_score``, and reports:

  - Per-song mean and distribution of agreement scores
  - Library-wide mean and percentiles
  - Sections with score 0 (no independent corroboration — worth reviewing)

Intended use: run before and after pipeline changes. A change that lifts
the library-wide mean without adding regressions is a genuine improvement;
a change that lowers it is quietly degrading quality.

Usage:
    python scripts/library_fidelity.py /path/to/songs_dir
    python scripts/library_fidelity.py /path/to/songs_dir --json /tmp/fidelity.json

The scoring math lives in ``src/evaluation/section_fidelity.py`` so the
acceptance gate's ``section_fidelity`` suite and this script consume the
exact same numbers (per the spec: "Script and gate produce identical
library-mean for the same corpus").
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.evaluation.section_fidelity import (
    load_stories,
    print_report,
    summarize_song,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("songs_dir", type=Path)
    ap.add_argument("--json", type=Path, default=None,
                    help="Also write machine-readable summary to this path")
    args = ap.parse_args()

    if not args.songs_dir.is_dir():
        print(f"Not a directory: {args.songs_dir}", file=sys.stderr)
        sys.exit(1)

    stories = load_stories(args.songs_dir)
    if not stories:
        print(f"No *_story.json files found under {args.songs_dir}")
        sys.exit(0)

    per_song = [summarize_song(name, story) for name, story in stories]
    print_report(per_song)

    if args.json:
        args.json.write_text(json.dumps(per_song, indent=2))
        print(f"\nJSON summary → {args.json}")


if __name__ == "__main__":
    main()
