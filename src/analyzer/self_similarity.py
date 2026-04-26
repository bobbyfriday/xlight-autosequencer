"""Self-similarity matrix (SSM) — repetition-group detection for the analyzer.

Productionized from ``scripts/self_similarity_prototype.py``. The analyzer
calls :func:`compute_repetition_groups` during the structural pass; the
output is attached to ``HierarchyResult.repetition_groups``. The story
builder reads it as a *Chorus validator* — never as a source of truth
for section roles (per design D1 in
``openspec/changes/agreement-score-operationalization/design.md``).

Pipeline
--------
1. Beat-synchronous chroma + MFCC features (chroma for harmony, MFCC for
   timbre — the same pair the prototype used and that ``librosa.segment``
   examples document).
2. k-NN affinity recurrence matrix (`librosa.segment.recurrence_matrix`),
   diagonal-enhanced (`librosa.segment.path_enhance`).
3. **Auto-threshold** = 90th percentile of off-diagonal similarity values,
   per design D4. The percentile lives in ``_DEFAULT_PERCENTILE`` —
   private and not user-configurable through the public analyzer API
   (per spec scenario "Public analyzer API does not expose the
   threshold").
4. Time-lag stripe detection: contiguous runs of values ≥ threshold
   along each diagonal lag, deduped by overlap.
5. Repetition groups: occurrences linked by stripes are merged with
   union-find; groups with ≥ 2 members are returned.

Failure modes
-------------
- SSM produces zero groups (no diagonals exceed the auto-threshold,
  e.g. on songs with no clear repeats): return ``[]``. The story-builder
  validator treats every Chorus as supported in this case, so a
  zero-group song is inert — never harms.
- SSM unavailable / errors (missing librosa, audio decode failure,
  internal exception): the orchestrator catches at the call site and
  records ``repetition_groups=None`` plus a warning; this module
  raises rather than swallowing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from src.analyzer.result import RepetitionGroup


# Auto-threshold: top-X% of off-diagonal recurrence values. 90th
# percentile is the librosa.segment example default; see Q2 in
# design.md. If under-fires on Chorus validation we revisit.
_DEFAULT_PERCENTILE: float = 90.0

# Minimum stripe length (in beats) to count as a repetition. The
# prototype used 12; we keep the same default.
_MIN_LEN_BEATS: int = 12

# Minimum gap between two repetitions (in beats) so a stripe slightly
# off the main diagonal isn't mistaken for a self-match.
_MIN_GAP_BEATS: int = 16

# Feature extraction defaults (match prototype).
_FEATURE_HOP_LENGTH: int = 2048
_FEATURE_SR: int = 22050
_MFCC_DIM: int = 13


def _compute_features(
    audio: np.ndarray, sr: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (feature_matrix [F, T_beats], beat_times_s).

    ``F`` = 12 chroma + 13 MFCC = 25 dims.
    """
    import librosa

    _, beats = librosa.beat.beat_track(y=audio, sr=sr, hop_length=_FEATURE_HOP_LENGTH)
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=_FEATURE_HOP_LENGTH)

    chroma = librosa.feature.chroma_cqt(y=audio, sr=sr, hop_length=_FEATURE_HOP_LENGTH)
    chroma_sync = librosa.util.sync(chroma, beats, aggregate=np.median)

    mfcc = librosa.feature.mfcc(y=audio, sr=sr, hop_length=_FEATURE_HOP_LENGTH, n_mfcc=_MFCC_DIM)
    mfcc_sync = librosa.util.sync(mfcc, beats, aggregate=np.mean)

    features = np.vstack([chroma_sync, mfcc_sync])
    return features, beat_times


def _compute_recurrence(features: np.ndarray) -> np.ndarray:
    """Return a diagonal-enhanced recurrence matrix [T, T]."""
    import librosa
    R = librosa.segment.recurrence_matrix(
        features,
        mode="affinity",
        sym=True,
        k=max(5, features.shape[1] // 20),
    )
    R = librosa.segment.path_enhance(R, 15)
    return R


def _auto_threshold(R: np.ndarray, percentile: float = _DEFAULT_PERCENTILE) -> float:
    """Per-song threshold — percentile of off-diagonal recurrence values.

    Per spec: "the threshold computed for A SHALL depend only on A's
    matrix values, not on B's".
    """
    n = R.shape[0]
    if n < 2:
        return 1.0
    # Use upper triangle (k=1) to skip the main diagonal which is always 1.
    iu = np.triu_indices(n, k=1)
    off_diag = R[iu]
    if off_diag.size == 0:
        return 1.0
    return float(np.percentile(off_diag, percentile))


def _detect_stripes(
    R: np.ndarray,
    threshold: float,
    min_len_beats: int = _MIN_LEN_BEATS,
    min_gap_beats: int = _MIN_GAP_BEATS,
) -> list[tuple[int, int, int, float]]:
    """Find contiguous diagonal stripes above ``threshold``.

    Returns a list of ``(lag, start_beat, length, mean_similarity)``.
    """
    n = R.shape[0]
    stripes: list[tuple[int, int, int, float]] = []
    for k in range(min_gap_beats, n - min_len_beats):
        diag = np.array([R[i, i + k] for i in range(n - k)])
        above = diag >= threshold
        i = 0
        while i < len(above):
            if not above[i]:
                i += 1
                continue
            j = i
            while j < len(above) and above[j]:
                j += 1
            if j - i >= min_len_beats:
                stripes.append((k, i, j - i, float(np.mean(diag[i:j]))))
            i = j + 1
    return stripes


def _dedupe_stripes(
    stripes: list[tuple[int, int, int, float]],
) -> list[tuple[int, int, int, float]]:
    """Drop stripes whose occurrences overlap an already-kept stripe.

    Adjacent lags can produce near-identical detections of the same
    repetition; we keep only the longest / strongest representative.
    """
    # Sort by length desc, then by mean similarity desc so the strongest
    # stripe wins ties.
    stripes_sorted = sorted(stripes, key=lambda s: (-s[2], -s[3]))
    kept: list[tuple[int, int, int, float]] = []
    for s in stripes_sorted:
        k, start, length, _mean = s
        a_region = (start, start + length)
        b_region = (start + k, start + k + length)
        overlaps = False
        for kk in kept:
            kk_k, kk_s, kk_l, _ = kk
            kk_a = (kk_s, kk_s + kk_l)
            kk_b = (kk_s + kk_k, kk_s + kk_k + kk_l)
            for r1 in (a_region, b_region):
                for r2 in (kk_a, kk_b):
                    overlap = min(r1[1], r2[1]) - max(r1[0], r2[0])
                    if overlap > 0.5 * min(r1[1] - r1[0], r2[1] - r2[0]):
                        overlaps = True
                        break
                if overlaps:
                    break
            if overlaps:
                break
        if not overlaps:
            kept.append(s)
    return kept


def _stripes_to_groups(
    stripes: list[tuple[int, int, int, float]],
    beat_times: np.ndarray,
) -> list["RepetitionGroup"]:
    """Group stripe occurrences via union-find; convert to RepetitionGroups."""
    from src.analyzer.result import RepetitionGroup

    if not stripes:
        return []

    # Each stripe gives two occurrences (a at start; b at start+lag).
    occurrences: list[tuple[int, int, float]] = []
    for k, start, length, mean in stripes:
        occurrences.append((start, start + length, mean))
        occurrences.append((start + k, start + k + length, mean))

    occurrences.sort()
    merged: list[tuple[int, int, float]] = []
    for o in occurrences:
        if merged:
            last = merged[-1]
            overlap = min(o[1], last[1]) - max(o[0], last[0])
            min_len = min(o[1] - o[0], last[1] - last[0])
            if overlap > 0.5 * min_len:
                merged[-1] = (
                    min(last[0], o[0]),
                    max(last[1], o[1]),
                    max(last[2], o[2]),
                )
                continue
        merged.append(o)

    parent = list(range(len(merged)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def find_occ_idx(start: int, end: int) -> Optional[int]:
        for idx, (s, e, _) in enumerate(merged):
            overlap = min(e, end) - max(s, start)
            min_len = min(e - s, end - start)
            if min_len > 0 and overlap > 0.5 * min_len:
                return idx
        return None

    for k, start, length, _mean in stripes:
        a_idx = find_occ_idx(start, start + length)
        b_idx = find_occ_idx(start + k, start + k + length)
        if a_idx is not None and b_idx is not None:
            ra, rb = find(a_idx), find(b_idx)
            if ra != rb:
                parent[ra] = rb

    groups_map: dict[int, list[int]] = {}
    for i in range(len(merged)):
        root = find(i)
        groups_map.setdefault(root, []).append(i)

    # Convert beat indices → milliseconds via beat_times. Round-trip via
    # the cached array keeps the conversion inside this module.
    def beat_to_ms(beat_idx: int) -> int:
        i = min(max(beat_idx, 0), len(beat_times) - 1)
        return int(round(float(beat_times[i]) * 1000))

    groups: list[RepetitionGroup] = []
    for gid, member_indices in enumerate(groups_map.values()):
        if len(member_indices) < 2:
            continue
        members_ms = sorted(
            (beat_to_ms(merged[i][0]), beat_to_ms(merged[i][1]))
            for i in member_indices
        )
        groups.append(RepetitionGroup(id=gid, members=members_ms))

    # Stable order: largest groups first, then earliest first occurrence.
    groups.sort(key=lambda g: (-len(g.members), g.members[0][0]))
    # Re-id after sorting so ids are 0..N-1 in the emitted order.
    for new_id, group in enumerate(groups):
        group.id = new_id
    return groups


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_repetition_groups(
    audio: np.ndarray,
    sr: int,
) -> list["RepetitionGroup"]:
    """Detect repetition groups via SSM.

    Returns:
        A list of ``RepetitionGroup`` instances. Empty list when no
        diagonals exceed the auto-threshold (per spec scenario "SSM
        produces zero groups → empty list").

    Raises:
        Exception: any underlying librosa / numpy failure. The
        orchestrator wraps the call so the analyzer continues with
        ``repetition_groups=None`` and a warning. Per the engineering
        principles ("Favor real solutions over hacks"), this module
        does not silently swallow errors.
    """
    if audio.size == 0:
        return []

    features, beat_times = _compute_features(audio, sr)
    if features.shape[1] < (_MIN_GAP_BEATS + _MIN_LEN_BEATS):
        # Song too short for any plausible repetition.
        return []

    R = _compute_recurrence(features)
    threshold = _auto_threshold(R)
    stripes = _detect_stripes(R, threshold)
    if not stripes:
        return []
    stripes = _dedupe_stripes(stripes)
    return _stripes_to_groups(stripes, beat_times)


def compute_repetition_groups_from_matrix(
    R: np.ndarray,
    beat_times: np.ndarray,
    *,
    percentile: float = _DEFAULT_PERCENTILE,
) -> list["RepetitionGroup"]:
    """Internal entry-point used by tests with a pre-built matrix.

    Not part of the public analyzer API — exposed only for unit testing
    so we don't have to feed real audio into the test.
    """
    threshold = _auto_threshold(R, percentile=percentile)
    stripes = _detect_stripes(R, threshold)
    if not stripes:
        return []
    stripes = _dedupe_stripes(stripes)
    return _stripes_to_groups(stripes, beat_times)
