# Research: Intelligent Stem Analysis and Automated Light Sequencing Pipeline

**Feature**: 012-intelligent-stem-sweep
**Date**: 2026-03-23

## Research Topics

### R1: xLights Value Curve (.xvc) File Format

**Decision**: Use xLights Custom value curve type with segmented export for per-frame resolution.

**Findings from xLights source code (ValueCurve.cpp)**:

The `.xvc` file is a single XML element with all data encoded in a pipe-delimited `data` attribute:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<valuecurve
  data="Active=TRUE|Id=my_curve|Type=Custom|Min=0.00|Max=100.00|Values=0.00:0.50;0.01:0.75;1.00:0.25|"
  SourceVersion="2024.01"
/>
```

**Key format details**:
- **Data encoding**: Pipe-delimited `key=value` pairs in the `data` attribute
- **Custom points**: `Values=x1:y1;x2:y2;...` — semicolon-separated `x:y` pairs
- **X range**: 0.00 to 1.00 (normalized time — 0% to 100% of effect duration)
- **Y range**: 0.00 to 1.00 (normalized value — maps to Min..Max via linear interpolation)
- **Interpolation**: Linear between adjacent points; "wrapped" points jump directly
- **Min/Max**: Define the output parameter range. For 0-100 brightness: `Min=0.00|Max=100.00`
- **Precision**: Values formatted with 2 decimal places (`fmt2f()`). X values snap to `VC_X_POINTS = 200` discrete positions.

**Critical constraint — X-axis resolution**:
With 2-decimal formatting, only 101 unique X positions (0.00 through 1.00 in 0.01 steps) are representable. Even with internal 200-point snapping, a 3-minute song at 20 FPS has 3600 frames — far exceeding the ~100-200 unique X positions available.

**Resolution strategy**: Export value curves as **per-effect segments** rather than full-song monoliths. xLights applies value curves per-effect, so each effect (e.g., a 10-second section) maps the full 0.00-1.00 X range to its own duration. A 10-second effect at 20 FPS = 200 frames, which fits within the 200-position limit. The export pipeline will:
1. Use song structure segments (verse, chorus, etc.) as natural effect boundaries
2. Generate one `.xvc` file per segment per feature curve
3. Also generate a full-song "macro" `.xvc` with reduced resolution (~100 points, one per 1% of duration) for master dimmer use

**Alternatives considered**:
- Single full-song `.xvc` with all 3600 points: Rejected because X-axis quantization would collapse most points onto the same position
- Timing Track Toggle value curve type: Only supports on/off states, no continuous values
- Music value curve type: Derives from the audio waveform directly, not from our processed features

**Rationale**: Per-segment export matches how xLights users actually apply value curves (per effect), provides full frame resolution within each segment, and aligns with the existing song structure analysis output.

---

### R2: xLights Timing Track (.xtiming) Format for Beats/Onsets

**Decision**: Extend the existing `XTimingWriter` to support discrete event timing tracks (not just phonemes).

**Findings**:
The `.xtiming` format is already implemented in the codebase (`src/analyzer/xtiming.py`). The format uses:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<timings>
    <timing name="TrackName" SourceVersion="2024.01">
        <EffectLayer>
            <Effect label="beat" starttime="1000" endtime="1050" />
            <Effect label="beat" starttime="1500" endtime="1550" />
        </EffectLayer>
    </timing>
</timings>
```

For discrete events (beats, onsets), each Effect has a short duration (e.g., 50ms = one frame). Multiple timing tracks can be exported in a single file using separate `<timing>` elements, or as individual files.

**What needs extending**: The current writer only handles PhonemeResult (lyrics/words/phonemes). New code needs to accept TimingTrack objects and export their marks as Effect elements with appropriate labels.

**Alternatives considered**:
- Export beats as JSON only: Rejected — xLights can't import JSON timing data
- Export as MIDI: Rejected — xLights timing import supports `.xtiming` natively, MIDI would require conversion

---

### R3: Leader/Dominant Stem Election

**Decision**: Frame-by-frame RMS energy comparison with 250ms hold and energy-delta bypass.

**Algorithm**:
1. Compute per-frame RMS energy for each selected stem using `librosa.feature.rms()` with `frame_length=2048, hop_length=1024` (~23ms at 44.1kHz)
2. At each frame, find the stem with the highest RMS. If it exceeds the current leader by a configurable `delta_threshold` (default: 6 dB), assign immediately (bypass hold). Otherwise, a candidate must maintain higher energy for `hold_frames` (250ms / hop_time ≈ 11 frames) before becoming the new leader.
3. Quantize the final leader track to the export frame rate (20 FPS) by majority vote within each 50ms window.

**Parameters**:
- `hop_length`: 1024 samples (~23ms at 44.1kHz) for responsive tracking
- `hold_ms`: 250ms (spec FR-013) — prevents flickering
- `delta_db`: 6 dB — energy difference that bypasses hold (sudden solo/drop)
- Uses RMS energy rather than spectral flux because RMS is more robust to stem separation artifacts and directly comparable across stems

**Rationale**: RMS is simple, well-understood, and directly measures energy. Spectral flux would add sensitivity to timbral changes but also to separation artifacts. The hold mechanism with delta bypass balances stability against responsiveness.

**Alternatives considered**:
- Spectral flux + RMS combination: More complex, marginal benefit for stem-separated audio where artifacts cause spurious flux changes
- Machine learning classifier: Overkill for energy-based leader detection; no training data available

---

### R4: Kick-Bass Rhythmic Tightness

**Decision**: Onset-peak timing comparison using `librosa.onset.onset_detect()` on each stem, with windowed cross-correlation.

**Algorithm**:
1. Detect onsets in the drums stem and bass stem independently using `librosa.onset.onset_detect()`
2. For each analysis window (e.g., 4 bars based on estimated tempo):
   - Extract onset times for both stems within the window
   - For each drum onset, find the nearest bass onset
   - Compute the mean absolute timing difference (in ms)
   - Tightness score = `max(0, 1 - mean_diff / max_diff)` where `max_diff` = half a beat period
3. High tightness (> 0.7): flag as "unison flash" candidate
4. Low tightness (< 0.3): flag as "independent movement" candidate

**Parameters**:
- Window size: 4 bars (derived from estimated tempo and time signature)
- `max_diff`: Half a beat period (e.g., 250ms at 120 BPM)
- Onset detection uses energy peaks, not raw waveforms, per FR-014

**Rationale**: Comparing onset peak timing rather than raw waveform cross-correlation is specified in FR-014 to be resilient to stem separation artifacts. Onset detection on separated stems is more reliable than waveform correlation because it focuses on the rhythmic events rather than the spectral content.

**Alternatives considered**:
- Raw waveform cross-correlation: Sensitive to stem bleed and separation artifacts
- Beat-synchronous correlation: Would miss sub-beat interactions (e.g., syncopation)

---

### R5: Visual Sidechaining

**Decision**: Multiplicative gain envelope applied at drum onset positions on the vocal brightness curve.

**Algorithm**:
1. Detect drum onsets using `librosa.onset.onset_detect()` on the drums stem
2. For each onset, generate an envelope: instant attack (1 frame), exponential release over `release_frames` (default: 4 frames = 200ms at 20 FPS)
3. Envelope shape: `gain(t) = 1 - depth * exp(-t / tau)` where `depth` = 0.4 (40% reduction), `tau` = 2 frames
4. Multiply the vocal feature curve by the gain envelope
5. Simultaneously, boost a secondary dimension (e.g., saturation value) by `boost = depth * (1 - gain)` to create the "pumping" contrast per FR-016

**Parameters**:
- `depth`: 0.4 (40% momentary reduction in brightness)
- `release_frames`: 4 frames (200ms at 20 FPS) — natural pumping feel
- `boost_factor`: 0.3 (30% boost on secondary dimension during dip)
- Attack: instant (1 frame)

**Rationale**: Multiplicative envelope is the standard approach for sidechain pumping in audio production. The dual-dimension approach (dip brightness + boost saturation) creates visual contrast rather than just dimming, per FR-016. The release time of 200ms at 20 FPS provides a visible but not overwhelming pumping effect.

**Alternatives considered**:
- Subtractive envelope: Less natural than multiplicative; can create negative values
- Fixed-shape template: Less responsive to actual onset timing and spacing

---

### R6: Call-and-Response / Stem Handoff Detection

**Decision**: Energy envelope gap analysis with overlap tolerance.

**Algorithm**:
1. Compute a smoothed energy envelope for each melodic stem (vocals, guitar, piano) using RMS with a 500ms window
2. Define "active" as energy > 10% of the stem's peak energy
3. For each pair of melodic stems (A, B):
   - Find segments where A transitions from active → inactive and B transitions from inactive → active within a tolerance window
   - Tolerance: 500ms maximum gap between A's offset and B's onset (closer handoffs are higher confidence)
   - Emit a handoff event at the midpoint of the transition
4. Filter handoffs that occur within a structural boundary (from song structure analysis) for higher confidence

**Parameters**:
- Activity threshold: 10% of stem peak energy
- Max gap: 500ms between offset of stem A and onset of stem B
- Min active duration: 1 second (ignore very brief blips)

**Rationale**: Energy-based handoff detection is simple and sufficient for the use case. The 500ms gap tolerance accounts for natural pauses between phrases. Structural boundary alignment increases confidence. This approach doesn't require pitch analysis, which would be complex and unreliable on separated stems.

**Alternatives considered**:
- Pitch continuity analysis: Would detect melodic continuation more precisely but is unreliable on stem-separated audio
- Chroma-based similarity: More complex, marginal benefit for the lighting use case

---

### R7: Smoothing for Light Show Export

**Decision**: Savitzky-Golay filter with peak protection.

**Algorithm**:
1. Apply `scipy.signal.savgol_filter()` as the primary smoothing method:
   - Window length: 5 frames (250ms at 20 FPS)
   - Polynomial order: 2 (preserves peaks better than order 1, less overshoot than order 3)
2. Peak protection: Before smoothing, identify peaks that exceed `peak_threshold` (e.g., 2x the local median within a 1-second window). After smoothing, restore peak values to at least 90% of their original height.
3. The Savitzky-Golay filter is inherently zero-phase (symmetric FIR), so it introduces no lag — lights respond at the correct time.

**Parameters**:
- `window_length`: 5 frames (must be odd; 250ms at 20 FPS)
- `polyorder`: 2
- `peak_threshold`: 2.0 (times local median)
- `peak_restore_ratio`: 0.9 (restore peaks to at least 90% of original)

**Rationale**: Savitzky-Golay is zero-phase (no lag), preserves peak shapes better than moving average, and is available in scipy (no new dependency). The peak protection step ensures snare hits and drops remain visually impactful after smoothing, per FR-020.

**Alternatives considered**:
- Moving average: Introduces lag and flattens peaks; rejected per FR-020
- EMA (exponential moving average): Not zero-phase; would make lights feel sluggish
- Butterworth lowpass with filtfilt: More complex, similar results to Savitzky-Golay for this data rate

---

### R8: "Other" Stem Classification

**Decision**: Spectral heuristic based on variation and transient sharpness, per FR-018.

**Algorithm**:
1. Compute spectral centroid variance across frames
2. Compute transient sharpness: ratio of onset strength peaks to RMS energy (high = percussive, low = sustained)
3. Classification:
   - High spectral variation + low transient sharpness → pad/synth → route to spatial value curves
   - High transient sharpness → percussive element → route to timing tracks
   - Ambiguous → route to both, mark as "ambiguous" in export manifest

**Rationale**: Matches the specification in FR-018 exactly. Simple spectral features are sufficient to distinguish pads from percussive elements without a trained classifier.

---

### R9: Data Conditioning Pipeline

**Decision**: Three-stage pipeline: downsample → smooth → normalize.

**Algorithm**:
1. **Downsample**: Resample feature data from audio frame rate to target FPS (default 20 FPS / 50ms). Use `np.interp` for continuous features or nearest-frame selection for discrete features.
2. **Smooth**: Apply Savitzky-Golay filter (see R7) to continuous features only. Discrete events (beats, onsets) are not smoothed.
3. **Normalize**: Map to 0-100 integer range:
   - If the curve has meaningful dynamic range (max - min > 1% of max): linear scale `min→0, max→100`
   - If the curve is essentially flat: skip normalization expansion (FR edge case), keep at the proportional value, note in export manifest
   - Round to nearest integer; clamp to [0, 100]

**Parameters**:
- `target_fps`: 20 (configurable per FR-019)
- Frame boundaries: Round to nearest valid boundary when sample rate doesn't divide evenly (per edge case)

**Rationale**: Downsample-then-smooth is more efficient than smooth-then-downsample and produces equivalent results at these data rates. Integer 0-100 range satisfies FR-021 and maps directly to xLights value curve Y values (0.00-1.00 = 0-100%).
