"""Data conditioning: downsample, smooth, normalize feature curves for xLights export."""
from __future__ import annotations

import numpy as np

from src.analyzer.result import ConditionedCurve


def downsample(
    values: np.ndarray,
    source_sr: int,
    source_hop: int,
    target_fps: int,
) -> np.ndarray:
    """Resample a feature array from audio frame rate to target_fps using interpolation."""
    n_in = len(values)
    duration_s = n_in * source_hop / source_sr
    n_out = max(1, round(duration_s * target_fps))

    x_in = np.linspace(0.0, duration_s, n_in)
    x_out = np.linspace(0.0, duration_s, n_out)
    return np.interp(x_out, x_in, values)


def smooth(
    values: np.ndarray,
    window_length: int = 5,
    polyorder: int = 2,
    peak_restore_ratio: float = 0.9,
) -> np.ndarray:
    """Zero-phase Savitzky-Golay smoothing with peak reinsertion."""
    from scipy.signal import savgol_filter, find_peaks

    n = len(values)
    if n < window_length:
        return values.copy()

    # Zero-phase SG filter
    smoothed = savgol_filter(values, window_length=window_length, polyorder=polyorder)

    # Peak reinsertion: restore peaks to at least peak_restore_ratio of original
    peaks, _ = find_peaks(values)
    for p in peaks:
        if values[p] * peak_restore_ratio > smoothed[p]:
            smoothed[p] = values[p] * peak_restore_ratio

    return smoothed


def normalize(values: np.ndarray) -> tuple[list[int], bool]:
    """
    Scale values to 0-100 integer range.

    Returns (normalized_ints, is_flat) where is_flat=True when the dynamic
    range is negligible (< 1% of peak).
    """
    vmin = float(np.min(values))
    vmax = float(np.max(values))
    dynamic_range = vmax - vmin

    peak = max(abs(vmax), abs(vmin), 1e-9)
    is_flat = dynamic_range < 0.01 * peak

    if is_flat or dynamic_range < 1e-9:
        out = [50] * len(values) if is_flat else [0] * len(values)
        return out, True

    scaled = (values - vmin) / dynamic_range * 100.0
    out = [int(round(float(np.clip(v, 0.0, 100.0)))) for v in scaled]
    return out, False


def condition_curve(
    raw: np.ndarray,
    source_sr: int,
    source_hop: int,
    target_fps: int,
    name: str,
    stem: str,
    feature: str,
) -> ConditionedCurve:
    """Downsample → smooth → normalize a raw feature array into a ConditionedCurve."""
    resampled = downsample(raw, source_sr, source_hop, target_fps)
    smoothed = smooth(resampled)
    values, is_flat = normalize(smoothed)

    return ConditionedCurve(
        name=name,
        stem=stem,
        feature=feature,
        fps=target_fps,
        values=values,
        is_flat=is_flat,
    )
