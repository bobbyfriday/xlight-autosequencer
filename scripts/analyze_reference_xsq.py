#!/usr/bin/env python3
"""Analyze a hand-sequenced xLights .xsq file to extract sequencing patterns.

Extracts the "vocabulary and grammar" of how a skilled sequencer works:
effect choices, timing patterns, layering, palette usage, model coverage, etc.

Usage:
    python scripts/analyze_reference_xsq.py path/to/file.xsq
"""

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Known xLights effects (for anti-pattern detection)
# ---------------------------------------------------------------------------
KNOWN_XLIGHTS_EFFECTS = {
    "Bars", "Butterfly", "Candle", "Chase", "Circle", "Color Wash",
    "Curtain", "DMX", "Faces", "Fan", "Fill", "Fire", "Fireworks",
    "Galaxy", "Garlands", "Glediator", "Kaleidoscope", "Life", "Lightning",
    "Lines", "Liquid", "Marquee", "Meteors", "Morph", "Music", "Off",
    "On", "Pictures", "Pinwheel", "Plasma", "Ripple", "Servo", "Shader",
    "Shape", "Shimmer", "Shockwave", "Single Strand", "Snowflakes",
    "Snowstorm", "Spirals", "Spirograph", "State", "Strobe", "Tendril",
    "Tree", "Twinkle", "Video", "VU Meter", "Warp", "Wave",
}


@dataclass
class EffectPlacement:
    """A single effect placement on a model layer."""
    model: str
    layer_index: int
    name: str
    start_ms: int
    end_ms: int
    palette_idx: int
    ref: int  # index into EffectDB

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def duration_s(self) -> float:
        return self.duration_ms / 1000.0


@dataclass
class TimingMark:
    """A timing mark from a timing track."""
    track_name: str
    label: str
    start_ms: int
    end_ms: int


@dataclass
class XSQData:
    """All parsed data from an XSQ file."""
    filename: str = ""
    song_duration_ms: int = 0
    palettes: list[str] = field(default_factory=list)
    effect_db: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    timing_tracks: list[str] = field(default_factory=list)
    effects: list[EffectPlacement] = field(default_factory=list)
    timing_marks: list[TimingMark] = field(default_factory=list)
    model_layer_counts: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_xsq(path: str) -> XSQData:
    tree = ET.parse(path)
    root = tree.getroot()
    data = XSQData(filename=Path(path).name)

    # Metadata
    head = root.find("head")
    if head is not None:
        for tag in ("song", "artist", "album", "sequenceDuration", "sequenceTiming"):
            el = head.find(tag)
            if el is not None and el.text:
                data.metadata[tag] = el.text
        dur = head.find("sequenceDuration")
        if dur is not None and dur.text:
            data.song_duration_ms = int(float(dur.text) * 1000)

    # Color Palettes
    cp = root.find("ColorPalettes")
    if cp is not None:
        for p in cp.findall("ColorPalette"):
            data.palettes.append(p.text or "")

    # EffectDB
    edb = root.find("EffectDB")
    if edb is not None:
        for e in edb.findall("Effect"):
            data.effect_db.append(e.text or "")

    # DisplayElements
    de = root.find("DisplayElements")
    if de is not None:
        for el in de.findall("Element"):
            etype = el.get("type", "")
            name = el.get("name", "")
            if etype == "model":
                data.models.append(name)
            elif etype == "timing":
                data.timing_tracks.append(name)

    # ElementEffects
    ee = root.find("ElementEffects")
    if ee is not None:
        for elem in ee.findall("Element"):
            etype = elem.get("type", "")
            name = elem.get("name", "")

            if etype == "timing":
                for layer in elem.findall("EffectLayer"):
                    for eff in layer.findall("Effect"):
                        label = eff.get("label", "")
                        st = int(eff.get("startTime", "0"))
                        et = int(eff.get("endTime", "0"))
                        data.timing_marks.append(TimingMark(name, label, st, et))
            elif etype == "model":
                layers = elem.findall("EffectLayer")
                data.model_layer_counts[name] = len(layers)
                for li, layer in enumerate(layers):
                    for eff in layer.findall("Effect"):
                        eff_name = eff.get("name")
                        if eff_name is None:
                            continue  # timing-style labels, skip
                        st = int(eff.get("startTime", "0"))
                        et = int(eff.get("endTime", "0"))
                        pal = int(eff.get("palette", "0"))
                        ref = int(eff.get("ref", "0"))
                        data.effects.append(EffectPlacement(
                            model=name, layer_index=li, name=eff_name,
                            start_ms=st, end_ms=et, palette_idx=pal, ref=ref,
                        ))

    return data


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def parse_palette_params(palette_str: str) -> dict[str, str]:
    """Parse a comma-separated palette string into key=value dict."""
    params = {}
    # Palettes can contain commas inside Active=TRUE|...| values, so we
    # split carefully: split on comma only when followed by C_
    parts = re.split(r",(?=C_)", palette_str)
    for part in parts:
        if "=" in part:
            key, _, val = part.partition("=")
            params[key] = val
    return params


def extract_hex_colors(palette_str: str) -> list[str]:
    """Extract all #RRGGBB hex colors from a palette string."""
    return [c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}", palette_str)]


def detect_effect_type_from_db(db_entry: str) -> str:
    """Infer the effect type from an EffectDB parameter string."""
    # Look for E_*_EffectName_ prefixed params
    m = re.search(r"E_\w+?_([\w]+?)_", db_entry)
    if m:
        return m.group(1)
    return "Unknown"


def bucket_duration(dur_s: float) -> str:
    """Bucket a duration into a human-readable range."""
    if dur_s < 0.25:
        return "<0.25s"
    elif dur_s < 0.5:
        return "0.25-0.5s"
    elif dur_s < 1.0:
        return "0.5-1s"
    elif dur_s < 2.0:
        return "1-2s"
    elif dur_s < 4.0:
        return "2-4s"
    elif dur_s < 8.0:
        return "4-8s"
    elif dur_s < 16.0:
        return "8-16s"
    elif dur_s < 30.0:
        return "16-30s"
    elif dur_s < 60.0:
        return "30-60s"
    else:
        return "60s+"


DURATION_BUCKET_ORDER = [
    "<0.25s", "0.25-0.5s", "0.5-1s", "1-2s", "2-4s", "4-8s",
    "8-16s", "16-30s", "30-60s", "60s+",
]


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def report_header(data: XSQData) -> str:
    lines = []
    lines.append("=" * 78)
    lines.append(f"  XSQ REFERENCE ANALYSIS: {data.filename}")
    lines.append("=" * 78)
    lines.append("")
    for k, v in data.metadata.items():
        lines.append(f"  {k:25s} {v}")
    dur_s = data.song_duration_ms / 1000.0
    lines.append(f"  {'duration':25s} {dur_s:.1f}s ({dur_s/60:.1f} min)")
    lines.append(f"  {'total models':25s} {len(data.models)}")
    lines.append(f"  {'timing tracks':25s} {len(data.timing_tracks)}")
    lines.append(f"  {'total effect placements':25s} {len(data.effects)}")
    lines.append(f"  {'unique palettes':25s} {len(data.palettes)}")
    lines.append(f"  {'effect DB entries':25s} {len(data.effect_db)}")
    lines.append("")
    return "\n".join(lines)


def report_vocabulary(data: XSQData) -> str:
    lines = []
    lines.append("-" * 78)
    lines.append("  1. VOCABULARY -- What effects are used")
    lines.append("-" * 78)

    # Effect counts
    effect_counts = Counter(e.name for e in data.effects)
    lines.append("")
    lines.append("  Effect usage (total placements):")
    for name, count in effect_counts.most_common():
        pct = count / len(data.effects) * 100
        bar = "#" * max(1, int(pct / 2))
        lines.append(f"    {name:25s} {count:5d}  ({pct:5.1f}%)  {bar}")

    # Working set
    lines.append("")
    total = len(data.effects)
    cumulative = 0
    core_effects = []
    for name, count in effect_counts.most_common():
        cumulative += count
        core_effects.append(name)
        if cumulative / total >= 0.90:
            break
    lines.append(f"  Core working set (90% of placements): {', '.join(core_effects)}")
    rare = [n for n, c in effect_counts.items() if c <= 3]
    if rare:
        lines.append(f"  Rarely used (<=3 placements): {', '.join(sorted(rare))}")

    # Effects per model
    lines.append("")
    lines.append("  Effects used per model (top 15 models by placement count):")
    model_effects = defaultdict(Counter)
    for e in data.effects:
        model_effects[e.model][e.name] += 1
    model_totals = {m: sum(c.values()) for m, c in model_effects.items()}
    for model, _ in sorted(model_totals.items(), key=lambda x: -x[1])[:15]:
        fx_list = ", ".join(
            f"{n}({c})" for n, c in model_effects[model].most_common(5)
        )
        lines.append(f"    {model:35s} [{model_totals[model]:3d}] {fx_list}")

    # Customized parameters per effect type
    lines.append("")
    lines.append("  Effect parameter customizations (from EffectDB):")
    effect_type_params: dict[str, list[dict[str, str]]] = defaultdict(list)
    for entry in data.effect_db:
        etype = detect_effect_type_from_db(entry)
        params = {}
        for part in entry.split(","):
            if "=" in part:
                k, _, v = part.partition("=")
                params[k] = v
        effect_type_params[etype].append(params)

    for etype, param_list in sorted(effect_type_params.items()):
        lines.append(f"    {etype} ({len(param_list)} variants):")
        # Find params that vary across variants
        all_keys: set[str] = set()
        for p in param_list:
            all_keys.update(p.keys())
        varying = {}
        for key in sorted(all_keys):
            vals = set(p.get(key, "") for p in param_list)
            if len(vals) > 1:
                varying[key] = vals
        if varying:
            for key, vals in list(varying.items())[:5]:
                short_key = key.split("_", 2)[-1] if "_" in key else key
                sample = sorted(vals)[:4]
                lines.append(f"      varies: {short_key} = {', '.join(sample)}")
        else:
            lines.append("      (all identical)")

    lines.append("")
    return "\n".join(lines)


def report_grammar(data: XSQData) -> str:
    lines = []
    lines.append("-" * 78)
    lines.append("  2. GRAMMAR -- How effects are structured")
    lines.append("-" * 78)

    # Duration distribution
    lines.append("")
    lines.append("  Duration distribution (all effects):")
    dur_buckets: dict[str, Counter] = defaultdict(Counter)
    overall_buckets: Counter = Counter()
    for e in data.effects:
        b = bucket_duration(e.duration_s)
        dur_buckets[e.name][b] += 1
        overall_buckets[b] += 1

    lines.append("    Overall:")
    for b in DURATION_BUCKET_ORDER:
        count = overall_buckets.get(b, 0)
        if count:
            bar = "#" * max(1, int(count / max(overall_buckets.values()) * 40))
            lines.append(f"      {b:12s} {count:5d}  {bar}")

    lines.append("")
    lines.append("    Per effect type (top 8):")
    effect_counts = Counter(e.name for e in data.effects)
    for ename, _ in effect_counts.most_common(8):
        buckets = dur_buckets[ename]
        dominant = buckets.most_common(1)[0] if buckets else ("?", 0)
        total = sum(buckets.values())
        summary = ", ".join(
            f"{b}:{c}" for b in DURATION_BUCKET_ORDER
            if (c := buckets.get(b, 0)) > 0
        )
        lines.append(f"      {ename:25s} (n={total:4d}) {summary}")

    # Layering patterns
    lines.append("")
    lines.append("  Layering patterns:")
    layer_counts = Counter(data.model_layer_counts.values())
    for lc, num_models in sorted(layer_counts.items()):
        lines.append(f"    {lc} layer(s): {num_models} model(s)")

    multi_layer_models = [m for m, c in data.model_layer_counts.items() if c > 1]
    if multi_layer_models:
        lines.append("")
        lines.append("  Models with multiple layers:")
        for m in multi_layer_models:
            lc = data.model_layer_counts[m]
            # Check simultaneous layering
            model_effs = [e for e in data.effects if e.model == m]
            by_layer = defaultdict(list)
            for e in model_effs:
                by_layer[e.layer_index].append(e)
            # Count time periods where multiple layers have effects
            simultaneous = 0
            if len(by_layer) > 1:
                layer_keys = sorted(by_layer.keys())
                for e0 in by_layer[layer_keys[0]]:
                    for e1 in by_layer[layer_keys[1]]:
                        if e0.start_ms < e1.end_ms and e1.start_ms < e0.end_ms:
                            simultaneous += 1
                            break
            lines.append(
                f"    {m:35s} {lc} layers, ~{simultaneous} overlapping segments on L0"
            )

    # Density over time
    lines.append("")
    lines.append("  Density over time (active models per 10s window):")
    window_ms = 10000
    total_windows = (data.song_duration_ms + window_ms - 1) // window_ms
    window_counts = []
    for wi in range(total_windows):
        w_start = wi * window_ms
        w_end = w_start + window_ms
        active = set()
        for e in data.effects:
            if e.start_ms < w_end and e.end_ms > w_start:
                active.add(e.model)
        window_counts.append((w_start / 1000.0, len(active)))

    max_active = max(c for _, c in window_counts) if window_counts else 1
    # Show a condensed sparkline-style view
    lines.append(f"    (max active models in any window: {max_active})")
    lines.append("")
    # Show every 3rd window to keep it readable
    for i, (t, c) in enumerate(window_counts):
        bar = "#" * max(0, int(c / max(max_active, 1) * 40))
        lines.append(f"    {t:6.0f}s  {c:3d} models  {bar}")

    # Gap analysis
    lines.append("")
    lines.append("  Gap analysis (models with gaps > 1s in their timeline):")
    model_effs_sorted: dict[str, list[EffectPlacement]] = defaultdict(list)
    for e in data.effects:
        model_effs_sorted[e.model].append(e)

    gap_summary = []
    for model, effs in model_effs_sorted.items():
        effs_sorted = sorted(effs, key=lambda x: x.start_ms)
        gaps = []
        # Gap from start
        if effs_sorted and effs_sorted[0].start_ms > 1000:
            gaps.append((0, effs_sorted[0].start_ms))
        for i in range(len(effs_sorted) - 1):
            gap_start = effs_sorted[i].end_ms
            gap_end = effs_sorted[i + 1].start_ms
            if gap_end - gap_start > 1000:
                gaps.append((gap_start, gap_end))
        # Gap at end
        if effs_sorted and data.song_duration_ms - effs_sorted[-1].end_ms > 1000:
            gaps.append((effs_sorted[-1].end_ms, data.song_duration_ms))
        if gaps:
            total_gap = sum(e - s for s, e in gaps)
            gap_summary.append((model, len(gaps), total_gap))

    gap_summary.sort(key=lambda x: -x[2])
    for model, n_gaps, total_gap_ms in gap_summary[:15]:
        pct = total_gap_ms / data.song_duration_ms * 100
        lines.append(
            f"    {model:35s} {n_gaps:3d} gaps, "
            f"{total_gap_ms/1000:.1f}s total ({pct:.0f}% of song)"
        )

    # Repetition analysis
    lines.append("")
    lines.append("  Consecutive repetition (same effect+palette on same model):")
    repeat_counts: Counter = Counter()
    for model, effs in model_effs_sorted.items():
        effs_by_layer: dict[int, list[EffectPlacement]] = defaultdict(list)
        for e in effs:
            effs_by_layer[e.layer_index].append(e)
        for li, layer_effs in effs_by_layer.items():
            layer_effs.sort(key=lambda x: x.start_ms)
            streak = 1
            for i in range(1, len(layer_effs)):
                prev, cur = layer_effs[i - 1], layer_effs[i]
                if prev.name == cur.name and prev.palette_idx == cur.palette_idx:
                    streak += 1
                else:
                    if streak > 1:
                        repeat_counts[
                            f"{prev.name} (pal {prev.palette_idx}) on {model} L{li}"
                        ] += streak
                    streak = 1
            if streak > 1:
                prev = layer_effs[-1]
                repeat_counts[
                    f"{prev.name} (pal {prev.palette_idx}) on {model} L{li}"
                ] += streak

    if repeat_counts:
        lines.append("    Top consecutive runs (effect+palette repeated N times):")
        for desc, count in repeat_counts.most_common(15):
            lines.append(f"      {count:4d}x  {desc}")
    else:
        lines.append("    No consecutive repetitions found.")

    lines.append("")
    return "\n".join(lines)


def report_palettes(data: XSQData) -> str:
    lines = []
    lines.append("-" * 78)
    lines.append("  3. PALETTE PATTERNS")
    lines.append("-" * 78)

    lines.append("")
    lines.append(f"  Total unique palettes: {len(data.palettes)}")

    # Colors per palette
    colors_per_palette = []
    music_sparkles_count = 0
    all_hex: Counter = Counter()

    for i, pal in enumerate(data.palettes):
        params = parse_palette_params(pal)

        # Count enabled colors (Palette1 is always active, others need checkbox)
        active = 1  # Palette1 always active
        for j in range(2, 9):
            if params.get(f"C_CHECKBOX_Palette{j}") == "1":
                active += 1
        colors_per_palette.append(active)

        if params.get("C_CHECKBOX_MusicSparkles") == "1":
            music_sparkles_count += 1

        for color in extract_hex_colors(pal):
            all_hex[color] += 1

    # Distribution of active colors
    color_dist = Counter(colors_per_palette)
    lines.append("")
    lines.append("  Active colors per palette:")
    for n, count in sorted(color_dist.items()):
        lines.append(f"    {n} active colors: {count} palettes")

    avg_colors = sum(colors_per_palette) / max(len(colors_per_palette), 1)
    lines.append(f"    Average: {avg_colors:.1f} active colors per palette")

    # Music Sparkles
    lines.append("")
    lines.append(
        f"  MusicSparkles enabled: {music_sparkles_count}/{len(data.palettes)} "
        f"palettes ({music_sparkles_count/max(len(data.palettes),1)*100:.0f}%)"
    )

    # Most common hex colors
    lines.append("")
    lines.append("  Most common hex colors (across all palette slots):")
    for color, count in all_hex.most_common(15):
        lines.append(f"    {color}  {count:4d} occurrences")

    # Palette usage by model — how many distinct palettes per model?
    lines.append("")
    lines.append("  Palette variety per model:")
    model_palettes: dict[str, set[int]] = defaultdict(set)
    for e in data.effects:
        model_palettes[e.model].add(e.palette_idx)

    pal_variety = [(m, len(pals)) for m, pals in model_palettes.items()]
    pal_variety.sort(key=lambda x: -x[1])
    for model, n_pals in pal_variety[:15]:
        lines.append(f"    {model:35s} uses {n_pals:3d} distinct palette(s)")

    # Value curves in palettes
    vc_count = sum(1 for p in data.palettes if "Active=TRUE" in p)
    if vc_count:
        lines.append("")
        lines.append(
            f"  Palettes with color value curves (Active=TRUE): {vc_count}"
        )

    # SparkleFrequency overrides
    sparkle_freq = [
        p for p in data.palettes if "C_SLIDER_SparkleFrequency" in p
    ]
    if sparkle_freq:
        lines.append(f"  Palettes with custom SparkleFrequency: {len(sparkle_freq)}")

    lines.append("")
    return "\n".join(lines)


def report_timing(data: XSQData) -> str:
    lines = []
    lines.append("-" * 78)
    lines.append("  4. TIMING PATTERNS")
    lines.append("-" * 78)

    # Timing tracks
    lines.append("")
    lines.append("  Timing tracks:")
    tracks = defaultdict(list)
    for tm in data.timing_marks:
        tracks[tm.track_name].append(tm)

    for track_name, marks in tracks.items():
        lines.append(f"    {track_name}: {len(marks)} marks")
        if len(marks) <= 20:
            for m in marks:
                dur = (m.end_ms - m.start_ms) / 1000
                lines.append(
                    f"      {m.start_ms/1000:7.1f}s - {m.end_ms/1000:7.1f}s "
                    f"({dur:.1f}s) \"{m.label}\""
                )
        else:
            # Show summary
            labels = Counter(m.label for m in marks)
            lines.append(f"      Sample labels: {', '.join(list(labels.keys())[:10])}")
            durations = [(m.end_ms - m.start_ms) / 1000 for m in marks]
            avg_dur = sum(durations) / len(durations)
            lines.append(
                f"      Duration range: {min(durations):.2f}s - {max(durations):.2f}s "
                f"(avg {avg_dur:.2f}s)"
            )

    # Correlation: effect boundaries vs timing marks
    lines.append("")
    lines.append("  Effect boundary alignment with timing marks:")

    # Collect all timing mark start times
    beat_marks = []
    section_marks = []
    for tm in data.timing_marks:
        if "beat" in tm.track_name.lower() or "count" in tm.track_name.lower():
            beat_marks.append(tm.start_ms)
        if "break" in tm.track_name.lower() or "section" in tm.track_name.lower():
            section_marks.append(tm.start_ms)

    all_timing_starts = sorted(set(tm.start_ms for tm in data.timing_marks))

    if all_timing_starts:
        # For each effect start, find the nearest timing mark
        snap_thresholds = [25, 50, 100, 250, 500]
        effect_starts = [e.start_ms for e in data.effects]
        effect_ends = [e.end_ms for e in data.effects]
        all_boundaries = effect_starts + effect_ends

        for threshold in snap_thresholds:
            aligned = 0
            for boundary in all_boundaries:
                # Binary search would be better but this is fine for analysis
                for tm_t in all_timing_starts:
                    if abs(boundary - tm_t) <= threshold:
                        aligned += 1
                        break
            pct = aligned / max(len(all_boundaries), 1) * 100
            lines.append(
                f"    Within {threshold:4d}ms of any timing mark: "
                f"{aligned}/{len(all_boundaries)} ({pct:.1f}%)"
            )

        if beat_marks:
            lines.append("")
            lines.append("  Effect start alignment with beat marks specifically:")
            beat_set = sorted(set(beat_marks))
            for threshold in [25, 50, 100, 250]:
                aligned = 0
                for st in effect_starts:
                    for bt in beat_set:
                        if abs(st - bt) <= threshold:
                            aligned += 1
                            break
                pct = aligned / max(len(effect_starts), 1) * 100
                lines.append(
                    f"    Within {threshold:4d}ms of a beat: "
                    f"{aligned}/{len(effect_starts)} ({pct:.1f}%)"
                )

    lines.append("")
    return "\n".join(lines)


def report_model_coverage(data: XSQData) -> str:
    lines = []
    lines.append("-" * 78)
    lines.append("  5. MODEL COVERAGE")
    lines.append("-" * 78)

    lines.append("")
    dur_ms = data.song_duration_ms

    model_active: dict[str, int] = {}
    model_effs: dict[str, list[EffectPlacement]] = defaultdict(list)
    for e in data.effects:
        model_effs[e.model].append(e)

    for model in data.models:
        effs = sorted(model_effs.get(model, []), key=lambda x: x.start_ms)
        if not effs:
            model_active[model] = 0
            continue
        # Merge overlapping intervals across all layers
        intervals = [(e.start_ms, e.end_ms) for e in effs]
        intervals.sort()
        merged = [intervals[0]]
        for s, e in intervals[1:]:
            if s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        total = sum(e - s for s, e in merged)
        model_active[model] = total

    # Sort by coverage
    coverage = [
        (m, model_active.get(m, 0), model_active.get(m, 0) / max(dur_ms, 1) * 100)
        for m in data.models
    ]
    coverage.sort(key=lambda x: -x[2])

    lines.append(f"  {'Model':35s} {'Active':>8s} {'Coverage':>8s} {'Effects':>8s}")
    lines.append(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*8}")
    for model, active_ms, pct in coverage:
        n_effs = len(model_effs.get(model, []))
        lines.append(
            f"  {model:35s} {active_ms/1000:7.1f}s {pct:7.1f}% {n_effs:8d}"
        )

    # Categorize
    always_on = [m for m, _, p in coverage if p >= 90]
    sparse = [m for m, _, p in coverage if 0 < p < 30]
    empty = [m for m, _, p in coverage if p == 0]

    lines.append("")
    if always_on:
        lines.append(f"  'Always on' (>=90% coverage): {', '.join(always_on)}")
    if sparse:
        lines.append(f"  'Sparse' (<30% coverage): {', '.join(sparse)}")
    if empty:
        lines.append(f"  'Empty' (no effects): {', '.join(empty)}")

    lines.append("")
    return "\n".join(lines)


def report_antipatterns(data: XSQData) -> str:
    lines = []
    lines.append("-" * 78)
    lines.append("  6. ANTI-PATTERNS (things NOT done)")
    lines.append("-" * 78)

    # Unused effects
    used_effects = set(e.name for e in data.effects)
    unused = KNOWN_XLIGHTS_EFFECTS - used_effects
    lines.append("")
    lines.append(f"  Effects NEVER used ({len(unused)} of {len(KNOWN_XLIGHTS_EFFECTS)} known):")
    for name in sorted(unused):
        lines.append(f"    - {name}")

    # Models with no effects
    models_with_effects = set(e.model for e in data.effects)
    empty_models = [m for m in data.models if m not in models_with_effects]
    lines.append("")
    if empty_models:
        lines.append(f"  Models with NO effects ({len(empty_models)}):")
        for m in empty_models:
            lines.append(f"    - {m}")
    else:
        lines.append("  All models have at least one effect.")

    # Very short effects
    short = [e for e in data.effects if e.duration_ms < 500]
    lines.append("")
    lines.append(f"  Very short effects (<500ms): {len(short)} placements")
    if short:
        short_by_name = Counter(e.name for e in short)
        for name, count in short_by_name.most_common(10):
            durs = [e.duration_ms for e in short if e.name == name]
            avg = sum(durs) / len(durs)
            lines.append(
                f"    {name:25s} {count:4d} short placements "
                f"(avg {avg:.0f}ms, min {min(durs)}ms)"
            )
        # Where do short effects occur?
        short_models = Counter(e.model for e in short)
        lines.append("")
        lines.append("    Short effects by model:")
        for model, count in short_models.most_common(10):
            lines.append(f"      {model:35s} {count:4d}")

    # Very long effects
    long = [e for e in data.effects if e.duration_ms > 30000]
    lines.append("")
    lines.append(f"  Very long effects (>30s): {len(long)} placements")
    if long:
        for e in sorted(long, key=lambda x: -x.duration_ms)[:10]:
            lines.append(
                f"    {e.name:25s} on {e.model:25s} "
                f"{e.duration_s:.1f}s ({e.start_ms/1000:.1f}s-{e.end_ms/1000:.1f}s)"
            )

    lines.append("")
    return "\n".join(lines)


def report_summary_insights(data: XSQData) -> str:
    """High-level takeaways from the analysis."""
    lines = []
    lines.append("-" * 78)
    lines.append("  7. SUMMARY INSIGHTS")
    lines.append("-" * 78)
    lines.append("")

    effect_counts = Counter(e.name for e in data.effects)
    total = len(data.effects)

    # Effect diversity
    lines.append(f"  Unique effect types used: {len(effect_counts)}")
    top3 = effect_counts.most_common(3)
    top3_pct = sum(c for _, c in top3) / total * 100
    lines.append(
        f"  Top 3 effects account for {top3_pct:.0f}% of all placements: "
        f"{', '.join(f'{n} ({c})' for n, c in top3)}"
    )

    # Average effects per model
    models_with = set(e.model for e in data.effects)
    if models_with:
        avg_per_model = total / len(models_with)
        lines.append(f"  Average placements per active model: {avg_per_model:.1f}")

    # Duration stats
    durs = [e.duration_s for e in data.effects]
    if durs:
        durs.sort()
        median = durs[len(durs) // 2]
        lines.append(
            f"  Effect duration: min={min(durs):.2f}s, "
            f"median={median:.2f}s, max={max(durs):.2f}s"
        )

    # Palette reuse
    pal_usage = Counter(e.palette_idx for e in data.effects)
    lines.append(f"  Palettes actually referenced: {len(pal_usage)} of {len(data.palettes)}")
    top_pal = pal_usage.most_common(3)
    lines.append(
        f"  Most used palettes: "
        + ", ".join(f"#{i} ({c} uses)" for i, c in top_pal)
    )

    # Layering
    multi = sum(1 for c in data.model_layer_counts.values() if c > 1)
    lines.append(f"  Models with multi-layer effects: {multi}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path/to/file.xsq>")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    data = parse_xsq(path)

    report = []
    report.append(report_header(data))
    report.append(report_vocabulary(data))
    report.append(report_grammar(data))
    report.append(report_palettes(data))
    report.append(report_timing(data))
    report.append(report_model_coverage(data))
    report.append(report_antipatterns(data))
    report.append(report_summary_insights(data))

    print("\n".join(report))


if __name__ == "__main__":
    main()
