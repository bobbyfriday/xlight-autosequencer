"""T011: Quality scorer for timing tracks."""
from __future__ import annotations

import numpy as np

from src.analyzer.result import TimingTrack


def score_track(track: TimingTrack) -> float:
    """
    Compute a quality score (0.0–1.0) for a timing track's lighting usefulness.

    Score = 0.6 * density_score + 0.4 * regularity_score

    density_score:
        Peaks at avg_interval in [250ms, 1000ms].
        < 100ms  → 0.0 (too dense / noisy)
        100–250  → linear 0.0–1.0
        250–1000 → 1.0
        1000–3000 → linear 1.0–0.5
        > 3000   → 0.5

    regularity_score:
        1 - (stdev(intervals) / mean(intervals)), clamped to [0, 1].
        A perfectly regular beat scores 1.0; random onsets score near 0.
    """
    if len(track.marks) < 2:
        return 0.0

    times = np.array([m.time_ms for m in track.marks], dtype=float)
    intervals = np.diff(times)
    mean_interval = float(np.mean(intervals))

    if mean_interval <= 0:
        return 0.0

    # --- density score ---
    if mean_interval < 100:
        # Too dense to be useful for lighting — return 0 regardless of regularity.
        return 0.0
    elif mean_interval < 250:
        density = (mean_interval - 100) / (250 - 100)
    elif mean_interval <= 1000:
        density = 1.0
    elif mean_interval <= 3000:
        density = 1.0 - 0.5 * (mean_interval - 1000) / (3000 - 1000)
    else:
        density = 0.5

    # --- regularity score ---
    std_interval = float(np.std(intervals))
    cv = std_interval / mean_interval  # coefficient of variation
    regularity = max(0.0, 1.0 - cv)

    score = 0.6 * density + 0.4 * regularity
    return float(np.clip(score, 0.0, 1.0))
