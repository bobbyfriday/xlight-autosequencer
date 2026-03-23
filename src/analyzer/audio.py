"""T013: MP3/WAV loader — returns mono float32 array + AudioFile metadata."""
from __future__ import annotations

import os
from dataclasses import dataclass

import librosa
import numpy as np


@dataclass
class AudioFile:
    """Metadata for a loaded audio file."""

    path: str
    filename: str
    duration_ms: int
    sample_rate: int
    channels: int


def load(path: str) -> tuple[np.ndarray, int, AudioFile]:
    """
    Load an audio file and return (audio_array, sample_rate, metadata).

    audio_array is mono float32, normalised to [-1, 1].
    Raises ValueError on missing or corrupt files.
    """
    if not os.path.exists(path):
        raise ValueError(f"Audio file not found: {path!r}")

    try:
        audio, sr = librosa.load(path, sr=None, mono=True, dtype=np.float32)
    except Exception as exc:
        raise ValueError(f"Could not load audio file {path!r}: {exc}") from exc

    duration_ms = int(len(audio) / sr * 1000)
    filename = os.path.basename(path)

    meta = AudioFile(
        path=os.path.abspath(path),
        filename=filename,
        duration_ms=duration_ms,
        sample_rate=int(sr),
        channels=1,  # librosa always returns mono
    )
    return audio, int(sr), meta
