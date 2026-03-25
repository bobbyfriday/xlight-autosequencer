# Musical Analysis Design Document

**Created**: 2026-03-24
**Status**: Working design — captures research, findings, and decisions from analysis sessions
**Songs tested**: Highway to Hell (AC/DC), Ghostbusters (Ray Parker Jr), You're A Mean One Mr. Grinch (Sabrina Carpenter/Lindsey Stirling)

---

## 1. Analysis Hierarchy for xLights

The fundamental insight: not all analysis serves the same purpose. Beats, structure, energy, and harmony each drive different lighting decisions. Treating them as a flat list of "timing tracks ranked by score" misses the point.

### Level 0: Special Moments (the "wow" triggers)

**Purpose**: Detect the moments in a song where something genuinely different happens — the moments a human listener would notice and respond to. These trigger one-shot or transition effects that make the light show feel alive rather than mechanical.

**What qualifies as a "special moment":**

| Moment Type | Detection Method | Validated? | Notes |
|-------------|-----------------|------------|-------|
| Energy impacts | RMS energy change >1.8x or <0.55x in 1-second windows | ✅ All 3 songs | Highway: 25, Ghostbusters: 41, Grinch: 43. Universal. |
| Gaps/silence | Near-silence (RMS < 0.01) for >300ms | ⚠️ Genre-dependent | Highway: 3 (intro stops), Ghostbusters: 2 (bookends), Grinch: **0**. Modern pop has no silence. |
| Novelty peaks | Chroma-based self-similarity deviation, top 90th percentile | ✅ All 3 songs | Relative ranking within a song works; absolute thresholds don't generalize. |
| Texture changes | Count of active stems crossing a threshold | ✅ Highway only (needs stems) | Going from 2→4 stems = build-up, 4→1 = breakdown. Concept is universal but requires stem separation. |
| Stem solos | One stem's energy >3x average of others | ✅ Highway only (needs stems) | Guitar solo detection worked perfectly. |

**Cross-song validation results:**
- Energy impacts: **universal** — works across all genres
- Gaps: **useful when present** but can't depend on them existing
- Novelty: **works but needs relative thresholds** (top N% within the song, not absolute values)
- Texture/stem changes: **needs stems** — can't run on full mix alone

### Level 1: Structure (scene boundaries)

**Purpose**: Divide the song into sections so you can assign different lighting scenes, color palettes, and effect groups to each section.

**Key finding**: Neither Segmentino nor QM Segmenter alone produces optimal boundaries. An ensemble approach where 2+ independent sources agree produces the most accurate boundaries.

See [Section 5: Ensemble Segmentation](#5-ensemble-segmentation) for full details.

**Segmentino repeat labels (A, B, N1, N2, etc.) are the most valuable structural feature** — they tell you which sections are musically identical and can share the same lighting design. This is more useful than knowing the section's name.

### Level 2: Bars & Phrases (pattern organization)

**Purpose**: The organizational grid for repeating patterns. A 4-beat chase pattern needs bar boundaries to reset correctly. A build effect needs phrase boundaries (every 4 bars).

| Detection | Algorithms | Typical Frequency | Validated? |
|-----------|-----------|-------------------|------------|
| Bar boundaries (downbeats) | qm_bars, librosa_bars, madmom_downbeats | ~0.5/s at 120 BPM | ✅ All beat trackers agree |
| Phrase boundaries | Not currently detected | ~0.125/s (every 4 bars) | ❌ Gap — could derive from bars + energy |

**Bars are correctly detected** at ~0.5/s (every 2 seconds at 120 BPM). All bar-detection algorithms agree on this frequency, confirming the detection is reliable.

**Phrases are missing** — groups of 4 or 8 bars that form musical phrases. Could be derived from bar marks + energy contour (a phrase often starts with a dynamic change).

### Level 3: Beats (pulse)

**Purpose**: The heartbeat. Flash timing, chase step, on-beat sync.

| Detection | Typical Frequency | Notes |
|-----------|-------------------|-------|
| Beat positions | ~2/s at 120 BPM | All beat trackers agree. Pick ONE best tracker per song. |

**Key insight**: You want ONE best beat track, not all of them. The sweep's job at this level is to find which algorithm + stem combo gives the most accurate beats for THIS song.

### Level 4: Instrument Events (per-stem accents)

**Purpose**: Individual musical events that trigger one-shot effects — a snare hit, a guitar strum, a vocal entry.

**Critical finding: different algorithms produce different densities, and you need the RIGHT density for each use case.**

| Use Case | Ideal Frequency | Best Algorithm + Stem | Notes |
|----------|----------------|----------------------|-------|
| Drum hits (all) | 2-4/s | aubio_onset on drums (2.3/s), percussion_onsets on drums (1.7/s) | ✅ Correct density |
| Guitar strums | 1-3/s | qm_onsets_phase on guitar (2.7/s) | ✅ But qm_onsets_hfc on guitar = 3.4/s (borderline) |
| Bass notes | 1.5-2.5/s | qm_onsets_phase on bass (2.2/s) | ✅ Correct |
| Vocal entries | 0.3-1/s | aubio_onset on vocals (0.5/s) | ✅ Correct — one per phrase |
| Chord changes | 0.3-1/s | chordino_chords on guitar (0.7/s) | ✅ Correct |

**Algorithms that produce TOO MANY events for lighting:**
- librosa_onsets on guitar: 8/s (every pick of every strum — too granular)
- qm_onsets_complex on bass: 7.5/s (too dense)
- librosa_onsets on full_mix: 6/s (too dense)

**Fix**: Sweep onset sensitivity parameter at multiple levels to find the right density for each stem.

### Level 5: Energy Curves (continuous automation)

**Purpose**: Drive xLights effect properties (brightness, size, speed, position) continuously over time. These are NOT timing events — they're value curves (`.xvc` files).

| Algorithm | Output | xLights Use |
|-----------|--------|------------|
| bbc_energy (per stem) | 0-100 value curve | Per-prop brightness — drum lights follow drum energy |
| bbc_spectral_flux | 0-100 value curve | Effect intensity — more spectral change = more visual complexity |
| amplitude_follower (per stem) | 0-100 value curve | Smooth brightness following (like a VU meter) |

**xLights value curve format**: `.xvc` files store percentage values (0-100) applied to any effect property. Users import them and assign to brightness, position, rotation, etc. Our 0-100 normalized output maps directly.

### Level 6: Harmonic Color (tonal mapping)

**Purpose**: Drive color selection based on harmonic content.

| Detection | Algorithm | Frequency | Use |
|-----------|-----------|-----------|-----|
| Chord changes | chordino_chords on guitar/piano | 0.7/s | Color change on each chord |
| Key changes | qm_key on full_mix | 0.2/s (structural) | Color palette shift |

---

## 2. Algorithms We're Using Wrong

### BBC Rhythm — Misclassified as Timing Marks

**What we did**: Treated 5168 items as timing marks (onset events).
**What it actually is**: A continuous rhythm strength curve at 172 values/second (every 5.8ms). Each item has a single float value measuring "how rhythmic is this moment."
**Fix**: Reclassify as a value curve. It measures rhythm intensity over time — could drive effect speed or pattern complexity.

### NNLS Chroma — Misclassified as Timing Marks

**What we did**: Treated 646 items as timing marks.
**What it actually is**: A 12-bin chroma matrix — 12 values per frame representing energy in each pitch class (C, C#, D, D#... B).
**Fix**: Either use as 12 value curves (one per pitch class for color mapping) or don't use directly — Chordino already processes it internally for chord detection.

### Onset Detectors at Default Sensitivity

**Problem**: Running onset detectors at default sensitivity produces the right density for some stems but too many events for others.
**Example**: `librosa_onsets` on drums = 2/s (correct for beats), but on guitar = 8/s (every pick, too dense for lighting).
**Fix**: Sweep the sensitivity parameter at multiple levels per stem:
- For drum hits: sensitivity 25-40
- For guitar strums: sensitivity 10-20
- For vocal entries: sensitivity 5-15
- The `minioi` (minimum inter-onset interval) parameter can also cap density (e.g., 200ms = max 5/s)

---

## 3. Stem Affinity — Universal vs Song-Specific

### Always True (physics of the instrument):
- **Beat trackers always work best on drums** — drums have the sharpest transients at beat positions
- **Chord detection always works best on guitar/piano** — they carry the harmonic content
- **Percussion onset detection always works best on drums** — purpose-built for broadband percussive events

### Song-Specific (depends on arrangement):
- **Bass onset detection**: Rhythmic in funk, sustained in ambient — onset count varies wildly
- **Guitar as beat source**: Works for rhythmic strumming (AC/DC), fails for legato playing (jazz ballad)
- **Energy curves**: Dynamic songs produce useful curves; wall-of-sound tracks produce flat curves
- **Vocal onset frequency**: Frequent in rap, sparse in opera

### Implication for the Sweep:
The affinity table gives good defaults. The sweep's real value is discovering **exceptions** — when a non-default stem gives better results for this particular song. That's why we sweep all applicable stems, not just the top 1.

---

## 4. The "Does the Name Matter?" Question

### Answer: No.

What matters for lighting is measurable properties, not section names:

| Property | How to detect | What it drives |
|----------|--------------|----------------|
| **Repeats?** | Segmentino labels (A=A=A) | Reuse the same lighting design |
| **Vocals active?** | Vocal stem energy > threshold | Spotlight on/off, lyric effects |
| **How many stems?** | Count stems above threshold | Effect complexity (1=simple, 4=full) |
| **Energy level?** | RMS relative to song median | Overall brightness/intensity |
| **Getting louder/quieter?** | Energy delta from previous section | Build-up or wind-down effects |
| **Something unique?** | Repeat count = 1 | Special one-time effects |

Calling it "Chorus" is shorthand for "repeating, vocals active, all stems playing, high energy." The measurable properties ARE the lighting decisions.

### When Genius labels ARE useful:
- Building a template library ("my standard Chorus lighting")
- Human readability in the UI
- Identifying instrumental sections (Guitar Solo, Interlude) that have no lyrics

---

## 5. Ensemble Segmentation

### The Problem with Single-Source Segmentation

| Segmenter | Strengths | Weaknesses |
|-----------|-----------|------------|
| **Segmentino** | Identifies repeating sections (A=A=A), good high-level structure | Too coarse — merged Highway intro+verse into 54s block. Missed guitar solo boundary. |
| **QM Segmenter (default)** | More granular boundaries (18 sections) | Too many sections, some very short (4-5s). Labels don't indicate repetition well. |
| **QM Segmenter (tuned)** | nSegmentTypes and neighbourhoodLimit are tunable | Requires parameter tuning per song. |
| **Genius** | Human-labeled section names, semantic meaning | No audio-derived timing. Requires API. Not all songs available. |

### QM Segmenter Parameters

Discovered through sweep:

| Parameter | What it controls | Useful range |
|-----------|-----------------|-------------|
| `nSegmentTypes` | How many distinct section types to detect | 3-5 (fewer = cleaner structure) |
| `neighbourhoodLimit` | Minimum segment duration | 6-12 (8 gives ~10s minimum, 6 catches solos) |
| `featureType` | Which audio feature drives segmentation | 1 or 2 (3 works too, 4-5 produce nothing) |

**Best tuned config for Highway to Hell**: nSegmentTypes=3, neighbourhoodLimit=8, featureType=1 → 8 segments with clean A/B/C labels.

### The Ensemble Approach

Run three segmenters independently, then find **consensus boundaries** where 2+ sources agree within 3 seconds:

1. **Segmentino** — for repeat structure (A=A=A)
2. **QM Segmenter tuned** (nSegmentTypes=3, neighbourhoodLimit=8) — clean boundaries
3. **QM Segmenter granular** (nSegmentTypes=5, neighbourhoodLimit=6) — catches details like solos
4. **Genius labels** (when available) — semantic names

**Validation on Highway to Hell**: The ensemble produced 12 consensus boundaries. Every real section boundary was found, including the guitar solo at 2:16 which Segmentino alone missed.

### Cross-Song Segmentation Results

| Song | Segmentino | QM (default) | Genius | Notes |
|------|-----------|-------------|--------|-------|
| Highway to Hell | 9 sections, 2 labels (A, N) | 18 sections | 8 sections | Segmentino merges intro+verse; QM too granular |
| Ghostbusters | 16 sections, 3 labels (A, B, N) | — | 12 sections | More complex structure; Segmentino handles well |
| Mr. Grinch | 9 sections, 3 labels (A, B, N) | — | 4 sections (verses only) | Genius misses instrumental interludes |

**Key observation**: Segmentino's repeat labels (A appears 5x in Highway, 6x in Ghostbusters, 4x in Grinch) are the most actionable feature across all songs. They tell you exactly what to reuse.

---

## 6. What Generalizes Across Songs

Tested on Highway to Hell (hard rock), Ghostbusters (80s funk/pop), Mr. Grinch (modern pop):

### Universal ✅
- **Energy impacts** (sudden loudness changes) — all 3 songs had 25-43 impacts
- **Beat/bar detection** — consistent ~2/s beats, ~0.5/s bars across all tempos
- **Segmentino repeat labels** — meaningful repeating structure in all 3 songs
- **Onset detection on drums** — correct density (1.7-2.3/s) for drum hits

### Genre-Dependent ⚠️
- **Gaps/silence** — Highway: 3, Ghostbusters: 2, Grinch: 0. Modern production eliminates silence.
- **Novelty peaks** — works but absolute thresholds vary. Use top N% within each song.
- **Energy dynamic range** — all 3 were "moderate" (0.40-0.48). A classical piece would be much higher; EDM might be lower.

### Needs Stems (can't verify on full mix alone) 🔬
- **Texture changes** (stem count) — tested only on Highway. Concept is universal but requires stem separation.
- **Stem dominance** — tested only on Highway. Per-stem energy analysis needs isolated stems.

### Not Yet Tested ❌
- Songs with no clear beat (ambient, classical)
- Songs with heavy compression (modern EDM where energy is nearly flat)
- Songs with extreme dynamic range (orchestral)

---

## 7. Recommended Architecture Changes

### Short-term (implement next):
1. **Fix bbc_rhythm and nnls_chroma** — reclassify as value curves, not timing marks
2. **Add sensitivity sweeping** for onset detectors — sweep at multiple sensitivities per stem
3. **Build ensemble segmenter** — combine Segmentino + tuned QM Segmenter + Genius
4. **Categorize sweep results by purpose** in the UI — not one flat list

### Medium-term:
5. **Add phrase detection** — derive from bar marks + energy contour
6. **Add texture analysis** — count active stems per section (requires stems)
7. **Section classification by measurable properties** — not names, but energy/vocal/stem-count

### Long-term:
8. **Auto-generate lighting roadmap** — for each section, recommend: intensity level, which stems to follow, which effects to use, what repeats
9. **Template matching** — "this section has similar properties to a Chorus template" for users who want named presets

---

## 8. xLights Value Curve (.xvc) Format

From the xLights documentation:

- Value curves modify how effect attributes change over time
- Applied to **any effect property**: brightness, speed, size, color mix, position, rotation
- Range: **0-100** (percentage)
- Types: flat, ramp, sawtooth, or **custom** (arbitrary points — what we produce)
- Stored as `.xvc` files in the show's `valuecurves/` folder
- Users import them and assign to effect properties via a dialog

Our `bbc_energy` output (0-100 normalized values per frame) maps directly to the custom value curve type. One energy curve per stem = one brightness automation per light group.

---

## 9. Open Questions

1. **Should we sweep QM Segmenter parameters per song, or use fixed "good defaults"?** The parameter sweep showed that nSegmentTypes=3, neighbourhoodLimit=8 works well for Highway, but might not be optimal for all songs. Could auto-detect optimal params by comparing segmenter output to energy dynamics.

2. **How do we handle songs where Genius isn't available?** The ensemble still works with just Segmentino + QM Segmenter. Genius adds names but isn't required for the measurable-property approach.

3. **What's the right sensitivity for onset detection per use case?** We identified target frequency ranges (drum hits: 2-4/s, guitar strums: 1-3/s) but haven't systematically swept sensitivity to find which values produce those ranges.

4. **How do we validate on non-rock genres?** Need to test ambient, classical, EDM, hip-hop to confirm the hierarchy generalizes. The three songs tested so far are all structured Western pop/rock.
