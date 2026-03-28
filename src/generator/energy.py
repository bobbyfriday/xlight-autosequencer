"""Section energy derivation from L5 energy curves and L0 impacts."""
from __future__ import annotations

from src.analyzer.result import TimingMark, ValueCurve
from src.generator.models import SectionEnergy, energy_to_mood


def derive_section_energies(
    sections: list[TimingMark],
    energy_curves: dict[str, ValueCurve],
    energy_impacts: list[TimingMark],
) -> list[SectionEnergy]:
    """Derive energy scores for each section from L5 curves and L0 impacts.

    For each section:
    1. Extract full_mix energy curve frames within the section's time range
    2. Average those frame values -> base_energy (0-100)
    3. Count L0 energy_impacts within the section
    4. Boost: final = min(100, base_energy + impact_count * 5)
    5. Map to mood tier: 0-33=ethereal, 34-66=structural, 67-100=aggressive
    """
    full_mix = energy_curves.get("full_mix")

    # Clamp section boundaries so they don't overlap —
    # each section ends at the next section's start time
    clamped: list[tuple[int, int, str]] = []
    for i, section in enumerate(sections):
        start_ms = section.time_ms
        end_ms = start_ms + (section.duration_ms or 0)
        if i + 1 < len(sections):
            next_start = sections[i + 1].time_ms
            end_ms = min(end_ms, next_start)
        clamped.append((start_ms, end_ms, section.label or "unknown"))

    result: list[SectionEnergy] = []
    for start_ms, end_ms, label in clamped:
        if end_ms <= start_ms:
            continue

        base_energy = _average_energy_in_range(full_mix, start_ms, end_ms)
        impact_count = _count_impacts_in_range(energy_impacts, start_ms, end_ms)
        final_energy = min(100, base_energy + impact_count * 5)

        result.append(SectionEnergy(
            label=label,
            start_ms=start_ms,
            end_ms=end_ms,
            energy_score=final_energy,
            mood_tier=energy_to_mood(final_energy),
            impact_count=impact_count,
        ))

    return result


def slice_curve(
    curve: ValueCurve | None, start_ms: int, end_ms: int
) -> list[int]:
    """Extract values from a ValueCurve within a time range.

    Shared utility — also used by value_curves.py.
    """
    if curve is None or not curve.values or curve.fps <= 0:
        return []

    ms_per_frame = 1000 / curve.fps
    start_frame = max(0, int(start_ms / ms_per_frame))
    end_frame = min(len(curve.values), int(end_ms / ms_per_frame))

    if start_frame >= end_frame:
        return []

    return curve.values[start_frame:end_frame]


def _average_energy_in_range(
    curve: ValueCurve | None, start_ms: int, end_ms: int
) -> int:
    """Average the energy curve values within a time range."""
    frames = slice_curve(curve, start_ms, end_ms)
    if not frames:
        return 0
    return round(sum(frames) / len(frames))


def _count_impacts_in_range(
    impacts: list[TimingMark], start_ms: int, end_ms: int
) -> int:
    """Count how many L0 energy impacts fall within a time range."""
    return sum(1 for imp in impacts if start_ms <= imp.time_ms < end_ms)
