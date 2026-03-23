"""
Shared pytest fixtures. Synthetic audio files are generated once per test session
and cached in tests/fixtures/. No real audio files are committed to the repo.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest
import scipy.io.wavfile as wavfile

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SR = 22050  # sample rate used for all fixtures


def _make_beat_fixture(path: Path) -> None:
    """120 BPM kick drum pattern — clear quarter-note beat every 500 ms."""
    duration_s = 10
    bpm = 120.0
    beat_interval_s = 60.0 / bpm  # 0.5 s

    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    audio = np.zeros_like(t)

    beat_times = np.arange(0, duration_s, beat_interval_s)
    for bt in beat_times:
        start = int(bt * SR)
        # Exponentially decaying sine at 150 Hz — kick-drum approximation
        decay_len = int(0.08 * SR)  # 80 ms decay
        if start + decay_len > len(audio):
            decay_len = len(audio) - start
        end = start + decay_len
        kick_t = np.linspace(0, decay_len / SR, decay_len, endpoint=False)
        kick = np.sin(2 * np.pi * 150 * kick_t) * np.exp(-40 * kick_t)
        audio[start:end] += kick

    # Normalise to int16 range
    audio = audio / (np.max(np.abs(audio)) + 1e-9)
    audio_int16 = (audio * 32767).astype(np.int16)
    wavfile.write(str(path), SR, audio_int16)


def _make_ambient_fixture(path: Path) -> None:
    """Smooth sine wave with slow amplitude modulation — no transients, no beat."""
    duration_s = 10
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    # 220 Hz carrier, amplitude modulated at 0.1 Hz (very slow)
    audio = np.sin(2 * np.pi * 220 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t))
    audio = audio / (np.max(np.abs(audio)) + 1e-9)
    audio_int16 = (audio * 32767).astype(np.int16)
    wavfile.write(str(path), SR, audio_int16)


def _make_drums_melody_fixture(wav_path: Path, gt_path: Path) -> None:
    """Drum hits on beats 1+3 (0.0s, 0.5s, 1.0s, 1.5s…) + 4-note melody."""
    duration_s = 10
    bpm = 120.0
    beat_s = 60.0 / bpm  # 0.5 s

    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    audio = np.zeros_like(t)

    # Drum hits on beats 1 and 3 of each bar (every beat in a 2-beat pattern)
    drum_times = np.arange(0, duration_s, beat_s)
    for bt in drum_times:
        start = int(bt * SR)
        decay_len = min(int(0.08 * SR), len(audio) - start)
        if decay_len <= 0:
            continue
        kick_t = np.linspace(0, decay_len / SR, decay_len, endpoint=False)
        kick = np.sin(2 * np.pi * 150 * kick_t) * np.exp(-40 * kick_t)
        audio[start : start + decay_len] += 0.8 * kick

    # 4-note melody cycling: C4(261Hz), E4(329Hz), G4(392Hz), B4(493Hz)
    melody_notes = [261.63, 329.63, 392.00, 493.88]
    note_duration_s = 0.4
    melody_times: list[float] = []
    note_idx = 0
    mt = 0.05  # slight offset from beat
    while mt + note_duration_s <= duration_s:
        freq = melody_notes[note_idx % len(melody_notes)]
        start = int(mt * SR)
        end = min(start + int(note_duration_s * SR), len(audio))
        note_t = np.linspace(0, (end - start) / SR, end - start, endpoint=False)
        note = np.sin(2 * np.pi * freq * note_t) * np.exp(-3 * note_t)
        audio[start:end] += 0.4 * note
        melody_times.append(round(mt * 1000))  # ms
        mt += note_duration_s + 0.1  # 100 ms gap between notes
        note_idx += 1

    audio = audio / (np.max(np.abs(audio)) + 1e-9)
    audio_int16 = (audio * 32767).astype(np.int16)
    wavfile.write(str(wav_path), SR, audio_int16)

    ground_truth = {
        "drum_hit_times_ms": [round(bt * 1000) for bt in drum_times.tolist()],
        "melody_note_onset_times_ms": melody_times,
        "bpm": bpm,
        "sample_rate": SR,
        "duration_ms": duration_s * 1000,
    }
    gt_path.write_text(json.dumps(ground_truth, indent=2))


def _make_mixed_fixture(path: Path) -> None:
    """Mixed signal: kick drums + bass tone + melody — suitable for stem routing tests."""
    duration_s = 10
    bpm = 120.0
    beat_s = 60.0 / bpm

    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    audio = np.zeros_like(t)

    # Kick drum on every beat
    for bt in np.arange(0, duration_s, beat_s):
        start = int(bt * SR)
        decay_len = min(int(0.08 * SR), len(audio) - start)
        if decay_len <= 0:
            continue
        kick_t = np.linspace(0, decay_len / SR, decay_len, endpoint=False)
        audio[start:start + decay_len] += 0.7 * np.sin(2 * np.pi * 150 * kick_t) * np.exp(-40 * kick_t)

    # Bass tone at 80 Hz
    audio += 0.3 * np.sin(2 * np.pi * 80 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t))

    # Melody: cycling notes
    for i, freq in enumerate([261.63, 329.63, 392.00, 493.88] * 5):
        start = int((i * 0.5 + 0.05) * SR)
        end = min(start + int(0.4 * SR), len(audio))
        if start >= len(audio):
            break
        note_t = np.linspace(0, (end - start) / SR, end - start, endpoint=False)
        audio[start:end] += 0.25 * np.sin(2 * np.pi * freq * note_t) * np.exp(-3 * note_t)

    audio = audio / (np.max(np.abs(audio)) + 1e-9)
    wavfile.write(str(path), SR, (audio * 32767).astype(np.int16))


@pytest.fixture(scope="session", autouse=True)
def audio_fixtures() -> dict[str, Path]:
    """Generate synthetic audio fixtures once per test session."""
    FIXTURES_DIR.mkdir(exist_ok=True)

    beat_path = FIXTURES_DIR / "beat_120bpm_10s.wav"
    ambient_path = FIXTURES_DIR / "ambient_10s.wav"
    drums_melody_path = FIXTURES_DIR / "drums_melody_10s.wav"
    gt_path = FIXTURES_DIR / "drums_melody_10s_ground_truth.json"
    mixed_path = FIXTURES_DIR / "10s_mixed.wav"

    if not beat_path.exists():
        _make_beat_fixture(beat_path)
    if not ambient_path.exists():
        _make_ambient_fixture(ambient_path)
    if not drums_melody_path.exists():
        _make_drums_melody_fixture(drums_melody_path, gt_path)
    if not mixed_path.exists():
        _make_mixed_fixture(mixed_path)

    return {
        "beat": beat_path,
        "ambient": ambient_path,
        "drums_melody": drums_melody_path,
        "ground_truth": gt_path,
        "mixed": mixed_path,
    }


@pytest.fixture(scope="session")
def beat_fixture_path(audio_fixtures: dict[str, Path]) -> Path:
    return audio_fixtures["beat"]


@pytest.fixture(scope="session")
def ambient_fixture_path(audio_fixtures: dict[str, Path]) -> Path:
    return audio_fixtures["ambient"]


@pytest.fixture(scope="session")
def drums_melody_fixture_path(audio_fixtures: dict[str, Path]) -> Path:
    return audio_fixtures["drums_melody"]


@pytest.fixture(scope="session")
def ground_truth(audio_fixtures: dict[str, Path]) -> dict:
    return json.loads(audio_fixtures["ground_truth"].read_text())


@pytest.fixture(scope="session")
def mixed_fixture_path(audio_fixtures: dict[str, Path]) -> Path:
    return audio_fixtures["mixed"]


def vamp_plugin_available(plugin_key: str) -> bool:
    """Return True if a Vamp plugin is installed and loadable."""
    try:
        import vamp
        plugins = vamp.list_plugins()
        # plugin_key format: "pack:plugin" — check prefix
        base_key = ":".join(plugin_key.split(":")[:2])
        return any(p.startswith(base_key) for p in plugins)
    except Exception:
        return False
