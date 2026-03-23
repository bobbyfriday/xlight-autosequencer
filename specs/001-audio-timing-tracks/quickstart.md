# Quickstart: Audio Analysis and Timing Track Generation

**Branch**: `001-audio-timing-tracks` | **Date**: 2026-03-22

Use this guide to validate a working implementation end-to-end.

---

## Prerequisites

```bash
# Install system dependency (macOS)
brew install ffmpeg

# Install Python dependencies
pip install librosa madmom click pytest

# Confirm install
python -c "import librosa, madmom, click; print('OK')"
```

---

## Step 1: Run Analysis on an MP3

```bash
xlight-analyze analyze /path/to/song.mp3
```

Expected output:
- Progress lines for each of 9 algorithms
- Summary table with track names, mark counts, and average intervals
- A file `song_analysis.json` written next to the MP3

---

## Step 2: Review the Summary

```bash
xlight-analyze summary song_analysis.json
```

Look for:
- `** HIGH DENSITY` flags on tracks like `onsets` or `treble`
- Compare `beats` vs `beats_rnn` mark counts and intervals — they should be similar
  for a steady 4/4 song
- Identify 3–5 tracks that look useful for the song

---

## Step 3: Export Selected Tracks

```bash
xlight-analyze export song_analysis.json --select beats,drums,bass
```

Expected output:
- Confirmation of 3 tracks exported
- A file `song_selected.json` with only those tracks

---

## Step 4: Verify Determinism

```bash
xlight-analyze analyze /path/to/song.mp3 --output run1.json
xlight-analyze analyze /path/to/song.mp3 --output run2.json
diff run1.json run2.json
# Should produce no output (files are identical)
```

---

## Step 5: Run the Test Suite

```bash
pytest tests/ -v
```

All tests should pass. Integration test `test_full_pipeline.py` validates the
end-to-end path from fixture MP3 → JSON output with expected beat timestamps.

---

## Validation Checklist

- [ ] `song_analysis.json` contains 9 timing tracks
- [ ] Beat track timestamps align visually with the song's audible beat
- [ ] `onsets` track has significantly more marks than `beats` (confirms noise filtering need)
- [ ] Two runs of the same file produce identical JSON
- [ ] `export` produces a JSON file with only the selected tracks
- [ ] `pytest` passes all tests
