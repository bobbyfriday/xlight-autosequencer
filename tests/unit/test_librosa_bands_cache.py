"""Regression test for the STFT cache key in librosa_bands.

Background
==========

PR #102 fixed a latent bug in `src/analyzer/algorithms/librosa_bands.py`:
the module-level `_stft_cache` was keyed by `(id(audio), sample_rate)`.
CPython readily reuses freed memory addresses for new objects, so when the
analyzer ran multiple fixtures back-to-back in a single process (the
acceptance gate, the snapshot regenerator, the cross-song tuner), a second
fixture's audio array could collide with a stale cache entry from the first
fixture and read back the wrong STFT. Symptom: 3-6× drift in
bass/mid/treble event counts between consecutive snapshot runs.

The fix was to key the cache by a cheap content fingerprint
(length, sample_rate, ndim, three sampled amplitude values).

These tests lock in that behaviour:

* `test_distinct_arrays_with_recycled_id_do_not_collide` simulates the
  id-collision scenario by creating two arrays with different content,
  freeing the first, and verifying the cache returns content-correct data
  for the second even when CPython happens to reuse the address.
* `test_fingerprint_distinguishes_distinct_audio` exercises
  `_audio_fingerprint` directly with arrays that are the same length and
  sample rate but have different content.
* `test_fingerprint_stable_for_equal_content` verifies the fingerprint is
  reproducible: a second array with the same shape and content produces the
  same key, so a cache hit on equal content is correct.
"""
from __future__ import annotations

import gc

import numpy as np

from src.analyzer.algorithms import librosa_bands as lb


def _silence_arr(n: int, sr: int = 22050) -> np.ndarray:
    return np.zeros(n, dtype=np.float32)


def _tone_arr(n: int, freq: float, sr: int = 22050) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / sr
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _clear_cache() -> None:
    lb._stft_cache.clear()


def test_fingerprint_distinguishes_distinct_audio() -> None:
    """Two arrays of equal shape but distinct content produce distinct keys."""
    sr = 22050
    a = _silence_arr(sr * 2, sr)
    b = _tone_arr(sr * 2, 220.0, sr)
    key_a = lb._audio_fingerprint(a, sr)
    key_b = lb._audio_fingerprint(b, sr)
    assert key_a != key_b


def test_fingerprint_stable_for_equal_content() -> None:
    """Two arrays with identical content produce the same key (cache-hit case)."""
    sr = 22050
    a = _tone_arr(sr, 440.0, sr)
    b = _tone_arr(sr, 440.0, sr)
    assert a is not b  # distinct objects
    assert lb._audio_fingerprint(a, sr) == lb._audio_fingerprint(b, sr)


def test_fingerprint_distinguishes_sample_rate() -> None:
    """Same buffer at different sample rates is not cache-equivalent."""
    a = _tone_arr(22050, 440.0, 22050)
    assert lb._audio_fingerprint(a, 22050) != lb._audio_fingerprint(a, 44100)


def test_distinct_arrays_with_recycled_id_do_not_collide() -> None:
    """Simulate the PR #102 bug: two distinct arrays whose Python `id()`s
    happen to collide must not return stale cached STFT data.

    We exercise the cache with one array, drop our only reference to it so
    CPython is free to recycle its address, then call the cache again with a
    differently-shaped/content array. With the previous `id()`-based key
    this could have returned the first array's STFT (wrong shape/freqs);
    with the content fingerprint it correctly recomputes.
    """
    _clear_cache()
    sr = 22050

    # First array: 1.0 s of silence at sr=22050.
    arr1 = _silence_arr(sr, sr)
    stft1, freqs1 = lb._get_stft_and_freqs(arr1, sr)
    n_frames_1 = stft1.shape[1]
    arr1_id = id(arr1)

    # Drop the reference and force GC. CPython is free to reuse the address.
    del arr1
    gc.collect()

    # Second array: 2.0 s of tone at sr=22050. Different length → different
    # number of STFT frames. If the cache wrongly returned the first entry
    # the frame count would still be n_frames_1.
    arr2 = _tone_arr(sr * 2, 440.0, sr)
    stft2, freqs2 = lb._get_stft_and_freqs(arr2, sr)

    # Whether or not arr2 happens to be at the recycled address, the cache
    # must serve content-correct data for the new array.
    assert stft2.shape[1] != n_frames_1, (
        "STFT frame count matches the previous (different-length) array — "
        "cache returned stale data."
    )
    # freqs depends only on (n_fft, sr), so it's the same — that is correct
    # and not affected by the bug. Sanity-check the shape.
    assert freqs1.shape == freqs2.shape

    # Document (without asserting) whether id() recycled. The test is
    # meaningful regardless because the fingerprint key is content-based.
    _ = (arr1_id, id(arr2))


def test_cache_hit_on_same_array_returns_same_object() -> None:
    """A second call with the same array returns the cached STFT identically."""
    _clear_cache()
    sr = 22050
    arr = _tone_arr(sr, 440.0, sr)
    stft1, freqs1 = lb._get_stft_and_freqs(arr, sr)
    stft2, freqs2 = lb._get_stft_and_freqs(arr, sr)
    # Cached return is the same numpy object (cache hit, not recompute).
    assert stft1 is stft2
    assert freqs1 is freqs2


def test_cache_evicts_previous_entry() -> None:
    """The cache keeps at most one entry to bound memory."""
    _clear_cache()
    sr = 22050
    a = _silence_arr(sr, sr)
    b = _tone_arr(sr * 2, 440.0, sr)
    lb._get_stft_and_freqs(a, sr)
    assert len(lb._stft_cache) == 1
    lb._get_stft_and_freqs(b, sr)
    # Cache holds only the most recent key.
    assert len(lb._stft_cache) == 1
    assert lb._audio_fingerprint(b, sr) in lb._stft_cache
