# Troubleshooting Guide

Common issues and how to resolve them.

## Installation Issues

### ffmpeg not found
**Symptoms:** `FileNotFoundError: ffmpeg` or `ffmpeg not found` during analysis.

**Fix:**
```bash
# macOS
brew install ffmpeg

# If installed but not on PATH (common with Homebrew on Apple Silicon):
export PATH="/opt/homebrew/bin:$PATH"

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
choco install ffmpeg
```

### Vamp plugins not loading
**Symptoms:** `INFO: vamp Python package not available` or `INFO: .venv-vamp not found — vamp/madmom algorithms skipped.`

**Causes:**
- The `.venv-vamp` virtual environment is not set up
- Vamp plugin `.dylib/.so` files are not in the expected location

**Fix:**
```bash
# Run the install script
./scripts/install.sh

# Or create the venv manually
python3.12 -m venv .venv-vamp
source .venv-vamp/bin/activate
pip install "numpy<2" vamp madmom librosa soundfile
deactivate

# Or point to an existing venv with vamp installed
export XLIGHT_VENV_VAMP=/path/to/venv/with/vamp/bin/python

# Verify Vamp plugins are installed
ls ~/Library/Audio/Plug-Ins/Vamp/  # macOS
ls /usr/lib/vamp/                   # Linux
```

### madmom import errors
**Symptoms:** `ImportError` or numpy compatibility errors with madmom.

**Cause:** madmom requires numpy < 2.0. The main environment uses numpy >= 2.0.

**Fix:** madmom runs in the `.venv-vamp` subprocess automatically. Ensure `.venv-vamp` has `numpy<2` and madmom installed:
```bash
.venv-vamp/bin/pip install "numpy<2" madmom
```

### `No module named 'demucs.api'`
**Symptoms:** Import error when running stem separation.

**Fix:** You need demucs >= 4.0.1:
```bash
pip install -U demucs
```

### `SSLCertVerificationError` during model downloads
**Symptoms:** SSL certificate errors when demucs or whisperx tries to download models.

**Fix (macOS, Python.org installer only):**
```bash
open "/Applications/Python 3.12/Install Certificates.command"
```

### whisperx / phoneme model errors
**Symptoms:** `Model not found` or SSL errors when downloading Whisper models, or alignment model failures.

**Fix:**
```bash
# Pre-download the model
python -c "from faster_whisper import WhisperModel; WhisperModel('base')"

# If alignment model fails
pip install huggingface_hub && huggingface-cli login

# If behind a proxy or firewall, download manually and set:
export HF_HOME=/path/to/huggingface/cache
```

### `TorchCodec is required` warning
**Symptoms:** Warning message about TorchCodec during analysis.

**Fix:** This warning is harmless and can be safely ignored.

---

## Analysis Issues

### Analysis seems frozen (no output)
**Symptoms:** CLI shows no progress for several minutes.

**Likely cause:** Stem separation (demucs) or Vamp algorithms running silently.

**Fix:**
- Use `--profile quick` for fast librosa-only analysis
- Set `XLIGHT_VERBOSE=1` for detailed progress output
- Stem separation can take 2-5 minutes on first run (demucs downloads a ~200 MB model, cached afterward)

### Out of memory during analysis
**Symptoms:** `MemoryError` or process killed by OS.

**Causes:**
- Large audio files (>10 minutes)
- Stem separation + all algorithms running simultaneously
- Multiple parallel analyses

**Fix:**
- Close other applications to free memory
- Use `--profile quick` (librosa-only, low memory)
- Process shorter audio files
- Ensure at least 4GB free RAM for full analysis with stems

### Poor quality scores
**Symptoms:** All tracks show low quality scores (<0.4).

**Possible causes:**
- Audio file has unusual tempo or structure
- Very short audio (<30 seconds)
- Audio is heavily compressed or low bitrate

**Fix:**
- Use a higher quality audio file (320kbps MP3 or WAV)
- Check `xlight-analyze summary <file>.json` for per-track details
- Try a custom scoring profile: `xlight-analyze scoring list`

### Cache not detected / stale results
**Symptoms:** Analysis re-runs when it shouldn't, or old results persist after changing the audio file.

**Fix:**
```bash
# Force fresh analysis
xlight-analyze analyze song.mp3 --fresh

# Check what's cached
ls -la <song_dir>/analysis/
```

---

## Web UI Issues

### Port already in use
**Symptoms:** `Address already in use` when launching `xlight-analyze review`.

**Fix:**
```bash
# Find and kill the existing process
lsof -i :5173
kill <PID>

# Then retry
xlight-analyze review
```

### Audio not playing in review UI
**Symptoms:** Timeline loads but audio won't play.

**Possible causes:**
- Audio file path has changed since analysis
- Browser blocking autoplay

**Fix:**
- Re-analyze the song to update the source_file path
- Click the Play button manually (browsers block autoplay)
- Check browser console for errors (F12)

### Upload fails silently
**Symptoms:** File selected but Analyze button stays disabled or nothing happens.

**Fix:**
- Ensure file is an MP3 (`.mp3` extension)
- Check browser console for JavaScript errors (F12)
- Try a different browser

---

## Generation / Export Issues

### xLights can't import the .xsq file
**Symptoms:** Error when opening generated sequence in xLights.

**Possible causes:**
- xLights version incompatibility
- Layout file not matching the generated sequence

**Fix:**
- Ensure you're using xLights 2024.x or later
- Verify the layout file used during generation matches your current xLights setup
- Try exporting as `.xtiming` instead (more portable format)

### Missing effects in generated sequence
**Symptoms:** Some sections have no effects or blank periods.

**Possible causes:**
- Section too short for effect placement
- Theme doesn't have effects for that section type

**Fix:**
- Check the generation preview for gaps
- Try a different theme or adjust section boundaries in Story Review

---

## Environment Issues

### devcontainer path mismatches
**Symptoms:** Analysis cache not found in devcontainer or Docker, or stem paths resolve incorrectly.

**Cause:** Paths differ between host and container.

**Fix:** The path resolution system auto-detects container environments. If issues persist:
```bash
# Check path resolution
python -c "from src.paths import PathContext; print(PathContext().info())"
```

### `.venv-vamp not found` in devcontainer
**Symptoms:** `".venv-vamp not found - cannot run demucs"` or similar errors in a container environment.

**Fix:** Run the install script inside the container:
```bash
./scripts/install.sh
```

---

## Getting More Help

- Set `XLIGHT_VERBOSE=1` for detailed error tracebacks
- Check the analysis JSON for warnings: `jq '.warnings' song_hierarchy.json`
- Run tests to verify your setup: `pytest tests/ -v`
- File issues at the project repository
