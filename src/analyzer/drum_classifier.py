"""Drum hit classifier: label each drum onset as kick, snare, or hihat.

Uses frequency-band energy ratios computed on a short window of the drum
stem at each onset.  No ML model required — three spectral bands are
sufficient to separate the three primary drum types reliably:

  kick   — dominated by sub/low energy  (20–200 Hz)
  hihat  — dominated by high energy     (8 000+ Hz)
  snare  — everything in between (midrange body + transient crack)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from src.analyzer.result import TimingTrack

# Frequency boundaries (Hz)
_KICK_MAX = 200
_HIHAT_MIN = 8_000

# Window around onset to analyse (ms)
_WINDOW_MS = 60


def classify_drum_events(
    track: "TimingTrack",
    drum_audio: np.ndarray,
    sample_rate: int,
) -> None:
    """Mutate each mark's label in-place with 'kick', 'snare', or 'hihat'.

    Args:
        track:       Drum TimingTrack whose marks will be labelled.
        drum_audio:  Mono float32 array of the separated drum stem.
        sample_rate: Sample rate of drum_audio.
    """
    if not track or not track.marks or drum_audio is None:
        return

    # Ensure mono
    if drum_audio.ndim == 2:
        drum_audio = drum_audio.mean(axis=1)

    n_fft = 1024
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
    kick_mask  = freqs < _KICK_MAX
    hihat_mask = freqs >= _HIHAT_MIN

    window_samples = max(n_fft, int(_WINDOW_MS * sample_rate / 1000))
    n = len(drum_audio)

    mid_mask = ~kick_mask & ~hihat_mask

    for mark in track.marks:
        center = int(mark.time_ms * sample_rate / 1000)
        segment = drum_audio[center: min(n, center + window_samples)]

        if len(segment) < n_fft:
            segment = np.pad(segment, (0, n_fft - len(segment)))

        spectrum = np.abs(np.fft.rfft(segment[:n_fft]))

        low_e  = float(spectrum[kick_mask].mean())
        mid_e  = float(spectrum[mid_mask].mean())
        high_e = float(spectrum[hihat_mask].mean())
        total  = low_e + mid_e + high_e + 1e-10

        low_ratio  = low_e  / total
        high_ratio = high_e / total

        if low_ratio > 0.60:
            mark.label = "kick"
        elif high_ratio > 0.20:
            mark.label = "hihat"
        else:
            mark.label = "snare"
