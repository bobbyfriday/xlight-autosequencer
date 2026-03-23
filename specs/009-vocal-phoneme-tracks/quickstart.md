# Quickstart: Vocal Phoneme Timing Tracks

**Branch**: `009-vocal-phoneme-tracks` | **Date**: 2026-03-22

---

## Install New Dependencies

```bash
pip install whisperx nltk
python -c "import nltk; nltk.download('cmudict')"
```

WhisperX downloads the Whisper `base` model (~140 MB) on first use, cached in `~/.cache/huggingface/`.

---

## Run Phoneme Analysis

```bash
# Audio-only (auto-transcription)
xlight-analyze analyze song.mp3 --phonemes

# With lyrics for better accuracy
xlight-analyze analyze song.mp3 --phonemes --lyrics lyrics.txt

# Note: --phonemes implies --stems (vocal stem used for phoneme analysis)
```

Output:
- `song_analysis.json` — standard analysis + `phoneme_result` section
- `song.xtiming` — xLights timing file with three layers

---

## Import into xLights

1. Open xLights
2. Go to the Timing Tracks panel
3. Right-click → Import Timing Track
4. Select `song.xtiming`
5. Three layers appear: lyrics, words, phonemes

---

## Verify Output

```bash
# View analysis summary (includes word/phoneme track info)
xlight-analyze summary song_analysis.json

# Open review UI to visualize phoneme tracks
xlight-analyze review song_analysis.json
```

---

## New Module: `src/analyzer/phonemes.py`

Key public interface:

```python
class PhonemeAnalyzer:
    def analyze(self, vocal_audio: np.ndarray, sample_rate: int,
                lyrics_path: Path | None = None) -> PhonemeResult: ...
    # Runs WhisperX transcription/alignment + cmudict phoneme decomposition

class PhonemeResult:
    lyrics_block: LyricsBlock
    word_track: WordTrack
    phoneme_track: PhonemeTrack
    language: str
    model_name: str

class XTimingWriter:
    def write(self, result: PhonemeResult, output_path: Path,
              song_name: str) -> None: ...
    # Generates .xtiming XML file
```

---

## Papagayo Mapping

Words are decomposed using the CMU Pronouncing Dictionary (ARPAbet), then mapped:

| Papagayo | ARPAbet |
|----------|---------|
| AI | AA, AE, AH, AY, AW |
| E | EH, ER, EY |
| O | AO, OW, OY, UH |
| WQ | W, UW |
| L | L |
| MBP | M, B, P |
| FV | F, V |
| etc | All others |

---

## Running Tests

```bash
pytest tests/ -v                              # all tests
pytest tests/unit/test_phonemes.py -v        # phoneme analyzer unit tests
pytest tests/unit/test_xtiming.py -v         # .xtiming writer tests
pytest tests/integration/ -v                 # end-to-end with --phonemes
```

Test fixtures: A short WAV with known lyrics (`tests/fixtures/`) is used for deterministic phoneme tests. WhisperX can be mocked for unit tests using pre-recorded transcription output.
