# Quality Scoring

[< Back to Index](README.md) | See also: [Algorithm Reference](algorithms.md) · [Pipeline](pipeline.md)

Every timing track produced by an algorithm is scored on a 0.0–1.0 scale. Scoring determines which algorithm "wins" for each hierarchy level, which tracks get exported, and which results appear at the top of sweep reports.

---

## Five Scoring Criteria

Each track is evaluated on five independent criteria:

### 1. Density (weight: 0.25)

**What:** How many marks per second does the track produce?

**Formula:** `mark_count / (duration_ms / 1000.0)`

**Why it matters:** Too few marks means the algorithm missed events. Too many means it's noisy or detecting non-musical artifacts.

```
Too sparse (0.1/sec):     |              |              |
Ideal (2.0/sec):          |    |    |    |    |    |    |
Too dense (50/sec):       ||||||||||||||||||||||||||||||||
```

### 2. Regularity (weight: 0.25)

**What:** How consistent are the intervals between marks?

**Formula:** `1.0 - (std(intervals) / mean(intervals))`

This is `1 - coefficient of variation`. A perfectly regular track (metronome) scores 1.0. A highly irregular track scores near 0.

**Why it matters:** Beat and bar tracks should be regular. Onset tracks should be less regular (they follow musical events, not a metronome). The target range is different per category.

```
High regularity (0.95):   |    |    |    |    |    |    |
Low regularity (0.30):    | |      |  ||    |        | |
```

### 3. Mark Count (weight: 0.15)

**What:** Absolute number of marks.

**Why it matters:** A 3.5-minute pop song should have ~200–400 beats. If a beat tracker produces 50 or 2000, something is wrong.

### 4. Coverage (weight: 0.15)

**What:** What fraction of the song duration is spanned by marks?

**Formula:** `(last_mark_time - first_mark_time) / duration_ms`

**Why it matters:** Tracks that only cover the first 30 seconds or miss the intro/outro are incomplete. Good tracks span >80% of the song.

```
Low coverage (0.40):      |||||||||.............................
High coverage (0.98):     |||||||||||||||||||||||||||||||||||||.
```

### 5. Min Gap Compliance (weight: 0.20)

**What:** What fraction of mark intervals are at least 25ms?

**Formula:** `count(intervals >= 25ms) / count(intervals)`

**Why it matters:** Marks closer than ~25ms are indistinguishable to human perception and to light controllers. They indicate duplicate detection, polyphonic overlap, or noise. This criterion penalizes tracks with many near-zero-gap marks.

---

## Category-Specific Ranges

Different types of tracks have very different expected characteristics. A beat track should be regular; an onset track should be irregular. The scorer uses category-specific target ranges:

### Beats (beat trackers)

```
Criterion        Target Range      Rationale
───────────────  ────────────────  ─────────────────────────────────
Density          1.0 – 4.0 /sec   60–240 BPM range
Regularity       0.6 – 1.0        Beats should be metrically regular
Mark Count       100 – 800        ~3.5 min × 2 beats/sec = ~400
Coverage         0.8 – 1.0        Should span nearly the whole song
Min Gap          ≥ 25ms           No near-duplicates
```

### Bars (downbeat trackers)

```
Criterion        Target Range      Rationale
───────────────  ────────────────  ─────────────────────────────────
Density          0.2 – 1.0 /sec   One bar every 1–5 seconds
Regularity       0.6 – 1.0        Bars should be regular
Mark Count       20 – 200         ~3.5 min ÷ 4 beats/bar ≈ 50
Coverage         0.7 – 1.0        May miss intro/outro
Min Gap          ≥ 25ms           No near-duplicates
```

### Onsets (onset detectors)

```
Criterion        Target Range      Rationale
───────────────  ────────────────  ─────────────────────────────────
Density          1.0 – 8.0 /sec   Higher density — many events
Regularity       0.0 – 0.6        Onsets are musically IRREGULAR
Mark Count       100 – 2000       Wide range depending on genre
Coverage         0.7 – 1.0        Should cover most of the song
Min Gap          ≥ 25ms           No near-duplicates
```

**Key difference:** Onsets are expected to be irregular (regularity 0.0–0.6), while beats are expected to be regular (0.6–1.0). A beat track that scores high on regularity is doing well; an onset track that scores high on regularity might be detecting only drum hits and missing everything else.

### Segments (structure detectors)

```
Criterion        Target Range      Rationale
───────────────  ────────────────  ─────────────────────────────────
Density          0.01 – 0.1 /sec  Very sparse — 5–15 per song
Regularity       0.0 – 0.5        Sections aren't equally sized
Mark Count       4 – 30           Most songs have 5–15 sections
Coverage         0.5 – 1.0        First/last section may be partial
Min Gap          ≥ 25ms           Sections are always far apart
```

### Notes (pitch/melody)

```
Criterion        Target Range
───────────────  ────────────────
Density          0.5 – 3.0 /sec
Regularity       0.2 – 0.8
Mark Count       50 – 500
Coverage         0.5 – 1.0
Min Gap          ≥ 25ms
```

### Harmonics (chord/chroma)

```
Criterion        Target Range
───────────────  ────────────────
Density          0.5 – 2.0 /sec
Regularity       0.3 – 0.9
Mark Count       30 – 300
Coverage         0.6 – 1.0
Min Gap          ≥ 25ms
```

---

## Scoring Formula

For each criterion, the raw value is scored against its target range:

```python
def score_in_range(value, target_min, target_max):
    if target_min <= value <= target_max:
        return 1.0                              # Perfect — in range
    if value < target_min:
        return max(0, value / target_min)       # Linear ramp up to min
    # value > target_max
    return max(0, 1 - (value - target_max) / target_max)  # Linear ramp down
```

Visualization:

```
Score
1.0 ┤          ┌──────────────────┐
    │         ╱                    ╲
    │        ╱                      ╲
    │       ╱                        ╲
0.0 ┤──────╱                          ╲──────
    └──────┴────────────────────────────┴──────
           target_min          target_max
```

The overall quality_score is the weighted average:

```
quality_score = 0.25 × density_score
             + 0.25 × regularity_score
             + 0.15 × mark_count_score
             + 0.15 × coverage_score
             + 0.20 × min_gap_score
```

---

## Score Breakdown

Each track gets a detailed `ScoreBreakdown` object:

```json
{
  "track_name": "madmom_beats",
  "algorithm_name": "madmom_beats",
  "category": "beats",
  "overall_score": 0.96,
  "criteria": [
    {"name": "density", "raw_value": 1.97, "score": 1.0, "weight": 0.25,
     "target_range": [1.0, 4.0]},
    {"name": "regularity", "raw_value": 0.92, "score": 1.0, "weight": 0.25,
     "target_range": [0.6, 1.0]},
    {"name": "mark_count", "raw_value": 412, "score": 1.0, "weight": 0.15,
     "target_range": [100, 800]},
    {"name": "coverage", "raw_value": 0.99, "score": 1.0, "weight": 0.15,
     "target_range": [0.8, 1.0]},
    {"name": "min_gap", "raw_value": 0.82, "score": 0.82, "weight": 0.20,
     "target_range": "≥ 25ms"}
  ]
}
```

View breakdowns via CLI: `xlight-analyze summary analysis.json --breakdown`

---

## Duplicate Detection

When multiple algorithms produce nearly identical timing data, the scorer marks duplicates:

- **Comparison:** Sort marks by time, compare pairwise within a 100ms window
- **Threshold:** If >80% of marks align within 100ms, the lower-scoring track is marked `skipped_as_duplicate`
- **Effect:** Duplicates are excluded from hierarchy selection but kept in the full analysis JSON

---

## Custom Scoring Profiles

Scoring ranges can be overridden via TOML config:

```toml
[categories.beats]
density_min = 1.5
density_max = 3.5
regularity_min = 0.7
regularity_max = 1.0
mark_count_min = 150
mark_count_max = 600

[weights]
density = 0.30
regularity = 0.30
mark_count = 0.10
coverage = 0.10
min_gap = 0.20
```

Profiles are managed via:
```bash
xlight-analyze scoring save my-profile --from config.toml
xlight-analyze scoring list
xlight-analyze scoring show my-profile
xlight-analyze scoring defaults
```

---

## Related Docs

- [Algorithm Reference](algorithms.md) — What each algorithm produces
- [Hierarchy Levels](hierarchy.md) — How scores select the best algorithm per level
- [Sweep System](sweep-system.md) — Scoring drives sweep result ranking
