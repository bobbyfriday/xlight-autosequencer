"""Song structure analysis using librosa segmentation + lyric-enhanced clustering."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.analyzer.phonemes import PhonemeResult

# Words ignored when comparing lyric content between segments.
_STOPWORDS = {
    "THE", "A", "AN", "I", "YOU", "ME", "MY", "YOUR", "WE", "OUR", "THEY",
    "AND", "OR", "BUT", "TO", "OF", "IN", "IS", "IT", "ON", "AT", "BE",
    "OH", "YEAH", "HEY", "NA", "LA", "OOH", "AH", "UM", "UH",
}


@dataclass
class StructureSegment:
    """A single labeled section of a song (intro, verse, chorus, etc.)."""

    label: str       # e.g. "intro", "verse", "chorus", "bridge", "outro"
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        self.start_ms = int(self.start_ms)
        self.end_ms = int(self.end_ms)

    def to_dict(self) -> dict:
        return {"label": self.label, "start_ms": self.start_ms, "end_ms": self.end_ms}

    @classmethod
    def from_dict(cls, d: dict) -> "StructureSegment":
        return cls(label=d["label"], start_ms=d["start_ms"], end_ms=d["end_ms"])


@dataclass
class SongStructure:
    """Complete structural segmentation result for one audio file."""

    segments: list[StructureSegment] = field(default_factory=list)
    source: str = "librosa"

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "segments": [s.to_dict() for s in self.segments],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SongStructure":
        return cls(
            segments=[StructureSegment.from_dict(s) for s in d.get("segments", [])],
            source=d.get("source", "librosa"),
        )


# ── Lyric helpers ──────────────────────────────────────────────────────────────

def _words_in_range(words, start_ms: int, end_ms: int):
    """Return WordMarks whose midpoint falls inside [start_ms, end_ms)."""
    return [w for w in words if start_ms <= (w.start_ms + w.end_ms) // 2 < end_ms]


def _vocal_coverage(words, start_ms: int, end_ms: int) -> float:
    """Fraction of [start_ms, end_ms) covered by word spans."""
    span = end_ms - start_ms
    if span <= 0:
        return 0.0
    covered = sum(
        min(w.end_ms, end_ms) - max(w.start_ms, start_ms)
        for w in words
        if w.start_ms < end_ms and w.end_ms > start_ms
    )
    return min(1.0, covered / span)


def _content_words(words, start_ms: int, end_ms: int) -> set[str]:
    """Non-stopword labels for words whose midpoint is in the segment."""
    return {
        w.label for w in _words_in_range(words, start_ms, end_ms)
        if w.label not in _STOPWORDS
    }


def _lyric_pause_boundaries_ms(words, min_gap_ms: int = 4000) -> list[int]:
    """
    Return a list of millisecond timestamps at the midpoint of every silence
    gap longer than min_gap_ms between consecutive words.
    """
    boundaries = []
    for i in range(1, len(words)):
        gap = words[i].start_ms - words[i - 1].end_ms
        if gap >= min_gap_ms:
            boundaries.append((words[i - 1].end_ms + words[i].start_ms) // 2)
    return boundaries


# ── Label assignment ───────────────────────────────────────────────────────────

def _assign_labels(
    cluster_labels: "np.ndarray",
    seg_energy: "np.ndarray",
    vocal_coverage: list[float],
    seg_start_ms: list[int],
    seg_end_ms: list[int],
    duration_ms: int,
) -> list[str]:
    """
    Map integer cluster IDs to semantic names.

    Priority order:
      1. Non-vocal segments (coverage < 15 %) → position-based instrumental name.
      2. Among vocal clusters: most-repeated + highest-energy → "chorus".
      3. Second most-repeated vocal cluster → "verse".
      4. Remaining vocal clusters → "bridge", "break", …
      5. Intro / outro overrides for first / last segment if they look like
         standalone non-repeating sections near song edges.
    """
    import numpy as np

    n = len(cluster_labels)
    names = [""] * n

    # ── Step 1: Mark non-vocal segments directly ──────────────────────────────
    is_vocal = [cov >= 0.15 for cov in vocal_coverage]

    for i in range(n):
        if not is_vocal[i]:
            rel_start = seg_start_ms[i] / duration_ms
            rel_end = seg_end_ms[i] / duration_ms
            if rel_start < 0.15:
                names[i] = "intro"
            elif rel_end > 0.85:
                names[i] = "outro"
            else:
                names[i] = "break"

    # ── Step 2: Cluster stats for vocal segments ──────────────────────────────
    vocal_indices = [i for i in range(n) if is_vocal[i]]
    if not vocal_indices:
        return names

    unique_clusters = list({int(cluster_labels[i]) for i in vocal_indices})
    freq: dict[int, int] = {}
    avg_energy: dict[int, float] = {}
    for c in unique_clusters:
        members = [i for i in vocal_indices if cluster_labels[i] == c]
        freq[c] = len(members)
        avg_energy[c] = float(seg_energy[members].mean())

    # Sort: most frequent first, break ties by energy
    ranked = sorted(unique_clusters, key=lambda c: (freq[c], avg_energy[c]), reverse=True)

    pool = ["chorus", "verse", "bridge", "break", "inst", "solo"]
    cluster_name: dict[int, str] = {c: pool[min(i, len(pool) - 1)] for i, c in enumerate(ranked)}

    for i in vocal_indices:
        names[i] = cluster_name[int(cluster_labels[i])]

    # ── Step 3: Intro/outro overrides for edge vocal segments ─────────────────
    # If the first segment is in a cluster that only appears once and is near
    # the start, call it "intro" regardless of vocal content.
    first_c = int(cluster_labels[0])
    last_c = int(cluster_labels[n - 1])

    if freq.get(first_c, 0) == 1 and seg_end_ms[0] / duration_ms < 0.2:
        names[0] = "intro"
    if last_c != first_c and freq.get(last_c, 0) == 1 and seg_start_ms[n - 1] / duration_ms > 0.8:
        names[n - 1] = "outro"

    return names


# ── Main analyzer ──────────────────────────────────────────────────────────────

class StructureAnalyzer:
    """
    Detect song structure using librosa segmentation with optional lyric
    enhancement from phoneme analysis output.

    Algorithm
    ---------
    1. Beat-synchronise MFCC + chroma features.
    2. Audio boundaries via agglomerative clustering on beat-synced features.
    3. If lyrics are available:
       a. Add silence-gap boundaries (gaps > 4 s in word track) as candidates.
       b. Snap audio boundaries to nearby lyric boundaries (within 2 s).
       c. Build a per-segment bag-of-words vector from content words; append
          to audio features before clustering so segments with the same lyrics
          naturally group together.
    4. Cluster segments on combined features → semantic labels via position,
       energy, repetition, and vocal coverage.
    """

    def analyze(
        self,
        audio_path: str,
        phoneme_result: Optional["PhonemeResult"] = None,
    ) -> SongStructure:
        """
        Analyze song structure from an audio file.

        Parameters
        ----------
        audio_path:
            Path to the audio file.
        phoneme_result:
            Optional PhonemeResult from prior phoneme analysis.  When present,
            word timings are used to improve boundary detection and labeling.

        Returns a SongStructure; segments list is empty if analysis fails.
        """
        import numpy as np
        import librosa
        from sklearn.cluster import AgglomerativeClustering

        hop_length = 512

        y, sr = librosa.load(audio_path, mono=True)
        duration = float(librosa.get_duration(y=y, sr=sr))
        duration_ms = int(duration * 1000)

        # ── Beat tracking ─────────────────────────────────────────────────────
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
        beat_frames = librosa.util.fix_frames(
            beat_frames, x_max=y.shape[-1] // hop_length
        )
        n_beats = len(beat_frames)
        if n_beats < 8:
            return SongStructure(segments=[])

        # ── Beat-synced features ──────────────────────────────────────────────
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, hop_length=hop_length)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)

        mfcc_sync = librosa.util.sync(mfcc, beat_frames, aggregate=np.median)
        chroma_sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
        rms_sync = librosa.util.sync(rms, beat_frames, aggregate=np.median)

        audio_features = np.vstack([
            librosa.util.normalize(mfcc_sync, axis=1),
            librosa.util.normalize(chroma_sync, axis=1),
        ])  # shape: (32, n_beats)

        # ── Helper: beat index → time in seconds ─────────────────────────────
        def beat_to_sec(idx: int) -> float:
            frame = beat_frames[min(int(idx), n_beats - 1)]
            return float(librosa.frames_to_time(frame, sr=sr, hop_length=hop_length))

        def sec_to_beat(t_sec: float) -> int:
            frame = int(librosa.time_to_frames(t_sec, sr=sr, hop_length=hop_length))
            return int(np.argmin(np.abs(beat_frames - frame)))

        # ── Audio boundary detection ──────────────────────────────────────────
        n_segs = max(4, min(12, int(duration / 25)))
        audio_bound_beats = librosa.segment.agglomerative(audio_features, n_segs)
        # These are indices into the beat-synced feature columns.

        # ── Lyric boundary enhancement ────────────────────────────────────────
        words = []
        if phoneme_result is not None:
            words = phoneme_result.word_track.marks

        if words:
            # Convert lyric pause midpoints to beat indices
            lyric_boundary_ms = _lyric_pause_boundaries_ms(words, min_gap_ms=4000)
            lyric_bound_beats = [sec_to_beat(t / 1000.0) for t in lyric_boundary_ms]

            # Snap audio boundaries to nearby lyric boundaries (within 2 s = ~2*fps beats)
            snap_window = sec_to_beat(2.0) - sec_to_beat(0.0)
            snap_window = max(snap_window, 4)

            snapped = set()
            used_lyric = set()
            for ab in audio_bound_beats:
                best_lb = None
                best_dist = snap_window + 1
                for lb in lyric_bound_beats:
                    d = abs(int(ab) - int(lb))
                    if d < best_dist:
                        best_dist = d
                        best_lb = lb
                if best_lb is not None and best_dist <= snap_window:
                    snapped.add(int(best_lb))
                    used_lyric.add(int(best_lb))
                else:
                    snapped.add(int(ab))

            # Add lyric boundaries that were far from any audio boundary
            for lb in lyric_bound_beats:
                if lb not in used_lyric:
                    snapped.add(int(lb))

            bound_beats = np.array(sorted(snapped))
        else:
            bound_beats = audio_bound_beats

        # Build full boundary array (including start=0 and end=n_beats)
        bounds = np.concatenate([[0], bound_beats, [n_beats]])
        bounds = np.clip(bounds, 0, n_beats).astype(int)
        bounds = np.unique(bounds)  # deduplicate and sort

        # ── Per-segment audio features + lyric features ───────────────────────
        seg_start_sec: list[float] = []
        seg_end_sec: list[float] = []
        seg_audio_feats: list[np.ndarray] = []
        seg_energy: list[float] = []
        seg_vocal_cov: list[float] = []

        for i in range(len(bounds) - 1):
            s, e = int(bounds[i]), int(bounds[i + 1])
            e = max(e, s + 1)
            t_start = beat_to_sec(s)
            t_end = beat_to_sec(min(e, n_beats - 1))
            seg_start_sec.append(t_start)
            seg_end_sec.append(t_end)
            feat = audio_features[:, s:e].mean(axis=1)
            seg_audio_feats.append(feat)
            seg_energy.append(float(rms_sync[0, s:e].mean()))
            seg_vocal_cov.append(
                _vocal_coverage(words, int(t_start * 1000), int(t_end * 1000))
                if words else 0.0
            )

        n_actual = len(seg_audio_feats)
        seg_audio_arr = np.array(seg_audio_feats)       # (n, 32)
        seg_energy_arr = np.array(seg_energy)            # (n,)
        seg_start_ms = [int(t * 1000) for t in seg_start_sec]
        seg_end_ms = [int(t * 1000) for t in seg_end_sec]

        # ── Build lyric bag-of-words features ─────────────────────────────────
        if words:
            # Vocabulary: all content words appearing in the song
            vocab = sorted({
                w.label for w in words if w.label not in _STOPWORDS
            })
            vocab_idx = {w: i for i, w in enumerate(vocab)}
            V = len(vocab)

            seg_bow = np.zeros((n_actual, V), dtype=float)
            for i in range(n_actual):
                for w in _words_in_range(words, seg_start_ms[i], seg_end_ms[i]):
                    if w.label in vocab_idx:
                        seg_bow[i, vocab_idx[w.label]] += 1
                # L1-normalise per segment
                total = seg_bow[i].sum()
                if total > 0:
                    seg_bow[i] /= total

            # Weight: lyric features scaled so they have comparable influence
            # to audio features — scale by sqrt(audio_dim / lyric_dim)
            lyric_weight = (seg_audio_arr.shape[1] / max(V, 1)) ** 0.5
            combined_features = np.hstack([seg_audio_arr, seg_bow * lyric_weight])
        else:
            combined_features = seg_audio_arr

        # ── Cluster segments ──────────────────────────────────────────────────
        n_clusters = min(n_actual, max(2, int(n_actual * 0.6)))
        cluster_labels = AgglomerativeClustering(
            n_clusters=n_clusters, linkage="ward"
        ).fit_predict(combined_features)

        # ── Semantic label assignment ─────────────────────────────────────────
        names = _assign_labels(
            cluster_labels=cluster_labels,
            seg_energy=seg_energy_arr,
            vocal_coverage=seg_vocal_cov,
            seg_start_ms=seg_start_ms,
            seg_end_ms=seg_end_ms,
            duration_ms=duration_ms,
        )

        segments = [
            StructureSegment(
                label=names[i],
                start_ms=seg_start_ms[i],
                end_ms=min(seg_end_ms[i], duration_ms),
            )
            for i in range(n_actual)
        ]

        return SongStructure(segments=segments, source="librosa")
