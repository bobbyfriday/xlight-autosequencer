"""Section role classifier for song story tool.

Classifies each (start_ms, end_ms) section into a named role using three
signals: segmentino repetition labels, vocal activity, and energy ranking.

Classification strategy
-----------------------
When segmentino labels are available (e.g. "A", "B", "C"):
  1. Group sections by label to find which label recurs most often.
  2. The most-repeated high-energy label → chorus.
  3. The remaining labels are ranked by energy and position.

Without labels: fall back to energy+vocals heuristics (original behaviour).
"""
from __future__ import annotations

VALID_ROLES = frozenset({
    "intro", "verse", "pre_chorus", "chorus", "post_chorus", "bridge",
    "instrumental_break", "climax", "ambient_bridge", "outro", "interlude",
})


def _avg_curve(
    curve: dict,
    start_ms: int,
    end_ms: int,
) -> float:
    """Return the average value of a energy curve dict over [start_ms, end_ms)."""
    sample_rate: float = curve.get("sample_rate") or curve.get("fps") or 10.0
    values: list[float] = curve["values"]
    n = len(values)

    start_idx = int(start_ms / 1000.0 * sample_rate)
    end_idx = int(end_ms / 1000.0 * sample_rate)
    start_idx = max(0, min(start_idx, n))
    end_idx = max(0, min(end_idx, n))

    if start_idx >= end_idx:
        return 0.0
    window = values[start_idx:end_idx]
    avg = sum(window) / len(window) if window else 0.0
    # Energy curve values are 0–100 integers; normalise to 0.0–1.0 so
    # downstream thresholds (VOCAL_THRESHOLD=0.05, chorus ≈ 0.6) work correctly.
    if avg > 1.0:
        avg /= 100.0
    return avg


def classify_section_roles(
    sections: list[tuple[int, int]],
    hierarchy: dict,
    section_labels: list[str | None] | None = None,
) -> list[dict]:
    """Classify each section into a named role.

    Args:
        sections:       List of (start_ms, end_ms) tuples.
        hierarchy:      HierarchyResult-compatible dict with energy_curves.
        section_labels: Segmentino label per merged section (e.g. "A", "B").
                        None entries mean the section spans multiple raw labels.

    Returns:
        List of dicts with 'role' (str) and 'confidence' (float) keys,
        one per input section.
    """
    if not sections:
        return []

    energy_curves: dict = hierarchy.get("energy_curves", {})
    vocals_curve: dict | None = energy_curves.get("vocals")
    full_mix_curve: dict | None = energy_curves.get("full_mix")

    n = len(sections)

    # --- Compute per-section signals ---
    vocals_avg: list[float] = []
    energy_avg: list[float] = []

    for start, end in sections:
        v = _avg_curve(vocals_curve, start, end) if vocals_curve else 0.0
        e = _avg_curve(full_mix_curve, start, end) if full_mix_curve else 0.0
        vocals_avg.append(v)
        energy_avg.append(e)

    VOCAL_THRESHOLD = 0.05
    has_any_vocal = any(v > VOCAL_THRESHOLD for v in vocals_avg)

    # --- Try label-aware classification first ---
    labels = section_labels if (section_labels and len(section_labels) == n) else None

    if labels and has_any_vocal:
        result = _classify_by_labels(
            sections, labels, vocals_avg, energy_avg, VOCAL_THRESHOLD
        )
        if result is not None:
            return result

    # --- Fallback: energy+vocal heuristics ---
    results: list[dict] = [{}] * n

    if not has_any_vocal:
        for i in range(n):
            if i == 0:
                role, conf = "intro", 0.85
            elif i == n - 1:
                role, conf = "outro", 0.85
            else:
                e = energy_avg[i]
                if e >= 0.4:
                    role, conf = "instrumental_break", 0.60
                else:
                    role, conf = "interlude", 0.55
            results[i] = {"role": role, "confidence": float(conf)}
        return results

    # Vocal song — energy percentile thresholds
    vocal_energies = [
        energy_avg[i] for i in range(n) if vocals_avg[i] > VOCAL_THRESHOLD
    ]
    if len(vocal_energies) >= 2:
        vocal_energies_sorted = sorted(vocal_energies)
        vocal_median = vocal_energies_sorted[len(vocal_energies_sorted) // 2]
        vocal_max = vocal_energies_sorted[-1]
        # Top 25% of vocal energy range → chorus (was 40%, more permissive)
        chorus_threshold = vocal_median + 0.75 * (vocal_max - vocal_median)
    elif len(vocal_energies) == 1:
        vocal_median = vocal_energies[0]
        vocal_max = vocal_energies[0]
        chorus_threshold = 0.65
    else:
        vocal_median = 0.5
        vocal_max = 1.0
        chorus_threshold = 0.65

    for i in range(n):
        is_first = i == 0
        is_last = i == n - 1
        v = vocals_avg[i]
        e = energy_avg[i]
        is_vocal = v > VOCAL_THRESHOLD

        if not is_vocal:
            if is_first:
                role, conf = "intro", 0.85
            elif is_last and e < 0.3:
                role, conf = "outro", 0.85
            elif is_last:
                role, conf = "outro", 0.80
            else:
                prev_vocal = vocals_avg[i - 1] > VOCAL_THRESHOLD if i > 0 else False
                next_vocal = vocals_avg[i + 1] > VOCAL_THRESHOLD if i < n - 1 else False
                if prev_vocal and next_vocal:
                    role, conf = "instrumental_break", 0.65
                else:
                    role, conf = "interlude", 0.60
        else:
            if e >= chorus_threshold:
                role = "chorus"
                conf = 0.75 + 0.10 * min(
                    1.0,
                    (e - chorus_threshold) / max(0.001, vocal_max - chorus_threshold),
                )
            else:
                role = "verse"
                conf = 0.65 + 0.10 * min(1.0, e / max(0.001, chorus_threshold))

        results[i] = {"role": role, "confidence": float(round(conf, 4))}

    return results


def _classify_by_labels(
    sections: list[tuple[int, int]],
    labels: list[str | None],
    vocals_avg: list[float],
    energy_avg: list[float],
    vocal_threshold: float,
) -> list[dict] | None:
    """Use segmentino repetition labels to guide role assignment.

    Returns None if labels don't provide enough signal.
    """
    n = len(sections)

    # Collect unique non-None labels
    unique_labels = list(dict.fromkeys(lb for lb in labels if lb is not None))
    if len(unique_labels) < 2:
        return None

    # For each unique label, compute average energy and count occurrences
    label_energy: dict[str, float] = {}
    label_count: dict[str, int] = {}
    label_vocal: dict[str, float] = {}

    for i, lb in enumerate(labels):
        if lb is None:
            continue
        label_energy[lb] = label_energy.get(lb, 0.0) + energy_avg[i]
        label_vocal[lb] = label_vocal.get(lb, 0.0) + vocals_avg[i]
        label_count[lb] = label_count.get(lb, 0) + 1

    # Normalise to per-occurrence averages
    for lb in unique_labels:
        c = label_count[lb]
        label_energy[lb] /= c
        label_vocal[lb] /= c

    # Only vocal labels (mean vocal > threshold) are chorus candidates
    vocal_labels = [lb for lb in unique_labels if label_vocal[lb] > vocal_threshold]
    if not vocal_labels:
        return None  # no vocal labels → fall back to heuristics

    # Identify chorus label: most-repeated vocal label with highest energy.
    # Tie-break: higher energy wins.
    max_count = max(label_count[lb] for lb in vocal_labels)
    chorus_candidates = [lb for lb in vocal_labels if label_count[lb] == max_count]
    chorus_label = max(chorus_candidates, key=lambda lb: label_energy[lb])

    # If all vocal labels repeat the same number of times, pick the highest energy
    if len(chorus_candidates) == len(vocal_labels):
        chorus_label = max(vocal_labels, key=lambda lb: label_energy[lb])

    # Assign roles based on the label-to-role mapping
    # First occurrence of a label gets "intro" if it's non-vocal or at position 0
    label_first_seen: dict[str, int] = {}
    for i, lb in enumerate(labels):
        if lb is not None and lb not in label_first_seen:
            label_first_seen[lb] = i

    results: list[dict] = [{}] * n
    chorus_energy = label_energy[chorus_label]

    for i in range(n):
        lb = labels[i]
        is_first_section = i == 0
        is_last_section = i == n - 1
        v = vocals_avg[i]
        e = energy_avg[i]
        is_vocal = v > vocal_threshold

        if not is_vocal:
            if is_first_section:
                role, conf = "intro", 0.85
            elif is_last_section and e < 0.3:
                role, conf = "outro", 0.85
            elif is_last_section:
                role, conf = "outro", 0.80
            elif lb is not None and label_first_seen.get(lb) == i:
                # First instance of a non-vocal label mid-song
                role, conf = "interlude", 0.65
            else:
                prev_vocal = vocals_avg[i - 1] > vocal_threshold if i > 0 else False
                next_vocal = vocals_avg[i + 1] > vocal_threshold if i < n - 1 else False
                if prev_vocal and next_vocal:
                    role, conf = "instrumental_break", 0.65
                else:
                    role, conf = "interlude", 0.60
        elif lb == chorus_label:
            # This section shares the chorus label
            conf = 0.80 + 0.10 * min(1.0, e / max(0.001, chorus_energy))
            role = "chorus"
        else:
            # Non-chorus vocal section — classify by energy relative to chorus
            energy_ratio = e / max(0.001, chorus_energy)
            is_first_of_label = label_first_seen.get(lb) == i

            if is_first_section and not is_vocal:
                role, conf = "intro", 0.85
            elif is_last_section:
                role, conf = "outro", 0.80
            elif energy_ratio >= 0.90:
                # Very close to chorus energy → pre_chorus or climax
                # pre_chorus: comes just before a chorus
                next_lb = labels[i + 1] if i + 1 < n else None
                if next_lb == chorus_label:
                    role, conf = "pre_chorus", 0.72
                else:
                    role, conf = "verse", 0.68
            elif energy_ratio >= 0.70:
                # Medium energy vocal section
                next_lb = labels[i + 1] if i + 1 < n else None
                prev_lb = labels[i - 1] if i > 0 else None
                if next_lb == chorus_label:
                    role, conf = "pre_chorus", 0.68
                elif prev_lb == chorus_label and label_count.get(lb, 1) == 1:
                    role, conf = "bridge", 0.65
                else:
                    role, conf = "verse", 0.65
            else:
                # Lower energy vocal — verse or bridge
                if label_count.get(lb, 1) == 1:
                    # Only appears once — likely a bridge
                    role, conf = "bridge", 0.62
                else:
                    role, conf = "verse", 0.65

        results[i] = {"role": role, "confidence": float(round(conf, 4))}

    return results
