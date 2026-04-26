"""Unit tests for the import-time audio validator."""
from __future__ import annotations

import io
import math
import struct
import wave
from pathlib import Path

import pytest

from src.review.api.v1._audio_validation import (
    AudioValidationError,
    MAX_DURATION_S,
    MAX_SAMPLE_RATE_HZ,
    MIN_DURATION_S,
    MIN_RMS_5S,
    MIN_SAMPLE_RATE_HZ,
    validate_audio,
)


def _write_wav(
    path: Path,
    duration_secs: float = 6.0,
    sample_rate: int = 44100,
    amplitude: int = 8000,
    freq_hz: float = 440.0,
) -> Path:
    n_samples = int(duration_secs * sample_rate)
    if amplitude == 0:
        samples = [0] * n_samples
    else:
        samples = [
            int(amplitude * math.sin(2 * math.pi * freq_hz * i / sample_rate))
            for i in range(n_samples)
        ]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return path


def test_valid_audio_passes(tmp_path):
    p = _write_wav(tmp_path / "ok.wav", duration_secs=6.0)
    # No exception means success.
    validate_audio(str(p))


def test_too_short_rejected(tmp_path):
    p = _write_wav(tmp_path / "short.wav", duration_secs=2.0)
    with pytest.raises(AudioValidationError) as exc:
        validate_audio(str(p))
    assert exc.value.code == "audio_too_short"


def test_too_long_rejected(tmp_path, monkeypatch):
    # Avoid actually generating 30 minutes of WAV — patch the
    # threshold low enough that a 6-second clip exceeds it.
    monkeypatch.setattr(
        "src.review.api.v1._audio_validation.MAX_DURATION_S",
        1.0,
    )
    p = _write_wav(tmp_path / "long.wav", duration_secs=6.0)
    with pytest.raises(AudioValidationError) as exc:
        validate_audio(str(p))
    assert exc.value.code == "audio_too_long"


def test_low_sample_rate_rejected(tmp_path):
    # 4000 Hz is below the 8 kHz floor.
    p = _write_wav(tmp_path / "low_sr.wav", duration_secs=6.0, sample_rate=4000)
    with pytest.raises(AudioValidationError) as exc:
        validate_audio(str(p))
    assert exc.value.code == "audio_sample_rate_invalid"


def test_silent_audio_rejected(tmp_path):
    p = _write_wav(tmp_path / "silent.wav", duration_secs=6.0, amplitude=0)
    with pytest.raises(AudioValidationError) as exc:
        validate_audio(str(p))
    assert exc.value.code == "audio_silent"


def test_malformed_file_rejected(tmp_path):
    # Random bytes with a .mp3 extension — the decoder cannot read this.
    p = tmp_path / "junk.mp3"
    p.write_bytes(b"\xff\xfb" + b"\x00" * 32)
    with pytest.raises(AudioValidationError) as exc:
        validate_audio(str(p))
    # Either decode fails outright or the partial result trips a
    # downstream check (too short / silent). All are valid rejections.
    assert exc.value.code in {
        "invalid_audio_decode",
        "audio_too_short",
        "audio_silent",
    }


def test_thresholds_documented():
    # Sanity: thresholds match what the docstring promises so a future
    # refactor can't silently change them.
    assert MIN_DURATION_S == 5.0
    assert MAX_DURATION_S == 1_800.0
    assert MIN_SAMPLE_RATE_HZ == 8_000
    assert MAX_SAMPLE_RATE_HZ == 96_000
    assert MIN_RMS_5S == 1e-4
