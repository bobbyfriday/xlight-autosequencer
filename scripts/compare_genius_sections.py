#!/usr/bin/env python3
"""Compare our segment classifier output with Genius lyric sections.

Usage:
    python scripts/compare_genius_sections.py songs/14_-_Ghostbusters/14_-_Ghostbusters.mp3

Requires GENIUS_API_TOKEN in .env or environment.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analyzer.genius_segments import (
    fetch_genius_lyrics,
    parse_sections,
    read_id3_tags,
    sanitize_title,
    strip_boilerplate,
)


def _fmt(ms: int) -> str:
    m = ms // 60_000
    s = (ms % 60_000) / 1000
    return f"{m:02d}:{s:05.2f}"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/compare_genius_sections.py <mp3_path>")
        sys.exit(1)

    mp3_path = Path(sys.argv[1]).resolve()
    token = os.environ.get("GENIUS_API_TOKEN", "")
    if not token:
        print("ERROR: GENIUS_API_TOKEN not set. Add it to .env or export it.")
        sys.exit(1)

    # ── Load our story sections ──────────────────────────────────────────────
    story_path = mp3_path.parent / (mp3_path.stem + "_story.json")
    if not story_path.exists():
        # Try one level up
        story_path = mp3_path.parent.parent / (mp3_path.stem + "_story.json")
    if not story_path.exists():
        print(f"ERROR: Story JSON not found at {story_path}")
        print("Run the analysis first via the upload UI or CLI.")
        sys.exit(1)

    story = json.loads(story_path.read_text(encoding="utf-8"))
    our_sections = story.get("sections", [])
    duration_ms = int(story["song"]["duration_seconds"] * 1000)

    # ── Fetch Genius lyrics ──────────────────────────────────────────────────
    try:
        artist, title = read_id3_tags(str(mp3_path))
    except ValueError:
        title = mp3_path.stem.replace("_", " ").replace("-", " ").strip()
        # Remove leading track numbers like "14 "
        import re
        title = re.sub(r"^\d+\s*[-.]?\s*", "", title).strip()
        artist = ""

    search_title = sanitize_title(title)
    print(f"Song: {title} by {artist}")
    print(f"Search: '{search_title}' / '{artist}'")
    print()

    match = fetch_genius_lyrics(search_title, artist, token)
    if match is None:
        print("ERROR: No match found on Genius.")
        sys.exit(1)

    print(f"Genius match: '{match.title}' by {match.artist}")
    print()

    clean_lyrics = strip_boilerplate(match.raw_lyrics)
    genius_sections = parse_sections(clean_lyrics)

    # ── Print Genius sections ────────────────────────────────────────────────
    print("=" * 70)
    print("GENIUS SECTIONS (lyric-based, no timing)")
    print("=" * 70)
    for i, seg in enumerate(genius_sections, 1):
        lines = seg.text.count("\n") + 1 if seg.text else 0
        preview = seg.text[:80].replace("\n", " / ") if seg.text else "(empty)"
        occ = f" #{seg.occurrence_index + 1}" if seg.occurrence_index > 0 else ""
        print(f"  {i:2d}. [{seg.label}{occ}]  ({lines} lines)")
        print(f"      {preview}")
    print()

    # ── Print our sections ───────────────────────────────────────────────────
    print("=" * 70)
    print("OUR SECTIONS (classifier output)")
    print("=" * 70)
    for s in our_sections:
        c = s.get("character", {})
        energy = c.get("energy_score", "?")
        print(f"  {s['id']}  {s['role']:16s}  {s['start_fmt']} → {s['end_fmt']}  "
              f"({s['duration']:.1f}s)  energy={energy}")
    print()

    # ── Comparison ───────────────────────────────────────────────────────────
    print("=" * 70)
    print("COMPARISON: Genius → Ours")
    print("=" * 70)

    # Normalise Genius labels to our role vocabulary
    def _normalize_genius_label(label: str) -> str:
        label_lower = label.lower().strip()
        # Strip artist/feature annotations like "Chorus: Ray Parker Jr."
        if ":" in label_lower:
            label_lower = label_lower.split(":")[0].strip()
        # Strip parenthetical
        label_lower = label_lower.split("(")[0].strip()

        mapping = {
            "intro": "intro",
            "verse": "verse",
            "chorus": "chorus",
            "hook": "chorus",
            "refrain": "chorus",
            "pre-chorus": "pre_chorus",
            "pre chorus": "pre_chorus",
            "post-chorus": "post_chorus",
            "post chorus": "post_chorus",
            "bridge": "bridge",
            "outro": "outro",
            "interlude": "interlude",
            "instrumental": "instrumental_break",
            "guitar solo": "instrumental_break",
            "solo": "instrumental_break",
            "sax solo": "instrumental_break",
            "break": "instrumental_break",
            "rap": "verse",  # Genius often labels rap sections separately
        }

        # Try exact match first
        if label_lower in mapping:
            return mapping[label_lower]

        # Try prefix match (e.g. "verse 1" → "verse")
        for key, role in mapping.items():
            if label_lower.startswith(key):
                return role

        return label_lower  # Return as-is if unknown

    genius_roles = [_normalize_genius_label(s.label) for s in genius_sections]
    our_roles = [s["role"] for s in our_sections]

    # Count by role
    from collections import Counter
    genius_counts = Counter(genius_roles)
    our_counts = Counter(our_roles)

    all_roles = sorted(set(list(genius_counts.keys()) + list(our_counts.keys())))

    print(f"\n  {'Role':<20s} {'Genius':>8s} {'Ours':>8s} {'Delta':>8s}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*8}")
    for role in all_roles:
        g = genius_counts.get(role, 0)
        o = our_counts.get(role, 0)
        delta = o - g
        marker = ""
        if delta > 0:
            marker = f"+{delta}"
        elif delta < 0:
            marker = str(delta)
        else:
            marker = "="
        print(f"  {role:<20s} {g:>8d} {o:>8d} {marker:>8s}")

    # ── Sequence comparison ──────────────────────────────────────────────────
    print(f"\n  Genius sequence ({len(genius_roles)} sections):")
    print(f"    {' → '.join(genius_roles)}")
    print(f"\n  Our sequence ({len(our_roles)} sections):")
    print(f"    {' → '.join(our_roles)}")

    # ── Gap analysis ─────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("GAP ANALYSIS")
    print("=" * 70)

    gaps = []

    # 1. Missing roles
    genius_role_set = set(genius_roles)
    our_role_set = set(our_roles)
    missing = genius_role_set - our_role_set
    extra = our_role_set - genius_role_set
    if missing:
        gaps.append(f"Roles in Genius but missing from ours: {', '.join(sorted(missing))}")
    if extra:
        gaps.append(f"Roles in ours but not in Genius: {', '.join(sorted(extra))}")

    # 2. Count mismatches
    for role in all_roles:
        g = genius_counts.get(role, 0)
        o = our_counts.get(role, 0)
        if g != o:
            gaps.append(f"{role}: Genius has {g}, we have {o} (delta {o-g:+d})")

    # 3. Sequence order issues
    if len(genius_roles) > 0 and len(our_roles) > 0:
        # Check if first/last roles match
        if genius_roles[0] != our_roles[0]:
            gaps.append(f"First section mismatch: Genius='{genius_roles[0]}', Ours='{our_roles[0]}'")
        if genius_roles[-1] != our_roles[-1]:
            gaps.append(f"Last section mismatch: Genius='{genius_roles[-1]}', Ours='{our_roles[-1]}'")

    if not gaps:
        print("  No significant gaps detected!")
    else:
        for i, gap in enumerate(gaps, 1):
            print(f"  {i}. {gap}")

    print()


if __name__ == "__main__":
    main()
