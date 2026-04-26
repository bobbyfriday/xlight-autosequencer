"""Import-time audio validation.

Rejects malformed, empty, silent, or out-of-range audio at the
``POST /api/v1/import`` boundary so the analyzer never runs on garbage.

The historical failure mode this exists to prevent: a one-frame MP3
(``libmpg123: Cannot read next header, a one-frame stream? Duh...``)
slipped through import, the analyzer wasted CPU on it, and the user
saw an opaque "review timeline button not visible" downstream.
Catching it here produces a structured 400 with a useful error code.

Thresholds are deliberately loose — they catch obvious junk without
rejecting unusual-but-legitimate uploads:

* ``MIN_DURATION_S = 5.0`` — a real song is at minimum tens of seconds.
  5 s catches one-frame MP3s, screen-test artifacts, and misclicks on
  system sounds, while still accepting short jingles.
* ``MAX_DURATION_S = 1800`` (30 min) — a soft ceiling. Albums, podcasts,
  and DJ sets are out of scope; a single track for an xLights sequence
  fits well under this.
* ``MIN_SAMPLE_RATE_HZ = 8_000`` — telephony-codec floor. Anything
  below is voice-codec audio, not music.
* ``MAX_SAMPLE_RATE_HZ = 96_000`` — high-quality-audio ceiling. Above
  this is almost certainly mis-decoded multi-channel studio output.
* ``MIN_RMS_5S = 1e-4`` — librosa returns float32 in ``[-1, 1]``.
  Pure silence is 0; ambient noise floor is ~1e-3. 1e-4 catches
  all-zero / DC-offset / broken-decode cases without rejecting quiet
  fade-in intros.
"""
from __future__ import annotations

import numpy as np

from src.analyzer.audio import load as _load_audio


MIN_DURATION_S = 5.0
MAX_DURATION_S = 1_800.0  # 30 minutes
MIN_SAMPLE_RATE_HZ = 8_000
MAX_SAMPLE_RATE_HZ = 96_000
MIN_RMS_5S = 1e-4


class AudioValidationError(Exception):
    """Raised when an uploaded audio file fails import validation.

    ``code`` is a stable machine-readable identifier surfaced as
    ``error.code`` in the JSON response; ``message`` is human-readable.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_audio(path: str) -> None:
    """Validate an audio file at ``path``.

    Raises :class:`AudioValidationError` on any failure. Returns
    ``None`` on success.
    """
    try:
        audio, sample_rate, meta = _load_audio(path)
    except Exception as exc:
        # ``audio.load`` already wraps decode failures in ValueError,
        # but other I/O exceptions can leak through. Surface all of
        # them as a single decode-failure code.
        raise AudioValidationError(
            "invalid_audio_decode",
            f"Could not decode audio file: {exc}",
        ) from exc

    duration_s = meta.duration_ms / 1000.0
    if duration_s < MIN_DURATION_S:
        raise AudioValidationError(
            "audio_too_short",
            f"Audio is too short ({duration_s:.2f}s). "
            f"Minimum supported length is {MIN_DURATION_S:g}s.",
        )
    if duration_s > MAX_DURATION_S:
        raise AudioValidationError(
            "audio_too_long",
            f"Audio is too long ({duration_s:.0f}s). "
            f"Maximum supported length is {MAX_DURATION_S:.0f}s "
            f"({int(MAX_DURATION_S // 60)} minutes).",
        )

    if sample_rate < MIN_SAMPLE_RATE_HZ or sample_rate > MAX_SAMPLE_RATE_HZ:
        raise AudioValidationError(
            "audio_sample_rate_invalid",
            f"Audio sample rate {sample_rate} Hz is outside the "
            f"supported range "
            f"[{MIN_SAMPLE_RATE_HZ}, {MAX_SAMPLE_RATE_HZ}] Hz.",
        )

    # RMS over the first 5 seconds — short enough that quiet fade-ins
    # don't drag the average down, long enough to be representative.
    head_samples = int(MIN_DURATION_S * sample_rate)
    head = audio[:head_samples]
    if head.size == 0:
        # Should not happen given the duration check above, but guard
        # against zero-sample arrays so np.mean doesn't warn.
        rms = 0.0
    else:
        rms = float(np.sqrt(np.mean(np.square(head, dtype=np.float64))))
    if rms < MIN_RMS_5S:
        raise AudioValidationError(
            "audio_silent",
            "Audio is silent or near-silent in the first "
            f"{MIN_DURATION_S:g}s (RMS {rms:.2e}). "
            "Verify the upload is correct.",
        )
