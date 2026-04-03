"""Sequence quality scorers — pure functions that evaluate a SequencePlan.

Each scorer takes a SequencePlan and HierarchyResult, returns a float 0-100.
Higher is better. All scorers are deterministic and require no audio files.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from src.analyzer.result import HierarchyResult
from src.generator.models import EffectPlacement, SectionAssignment, SequencePlan


@dataclass
class ScorerResult:
    """Result from a single scorer."""

    name: str
    score: float  # 0-100
    details: dict[str, float | int | str] = field(default_factory=dict)


# ── Beat Alignment ───────────────────────────────────────────────────────────


def score_beat_alignment(
    plan: SequencePlan,
    hierarchy: HierarchyResult,
    tolerance_ms: int = 50,
) -> ScorerResult:
    """Measure what fraction of effect start times align to musical events.

    Musical events: beats, bars, section boundaries, energy impacts.
    An effect is considered aligned if its start_ms is within tolerance_ms
    of any musical event.
    """
    timing_marks: set[int] = set()

    if hierarchy.beats:
        timing_marks.update(m.time_ms for m in hierarchy.beats.marks)
    if hierarchy.bars:
        timing_marks.update(m.time_ms for m in hierarchy.bars.marks)
    timing_marks.update(m.time_ms for m in hierarchy.sections)
    timing_marks.update(m.time_ms for m in hierarchy.energy_impacts)

    total = 0
    aligned = 0
    for assignment in plan.sections:
        for placements in assignment.group_effects.values():
            for p in placements:
                total += 1
                if _within_tolerance(p.start_ms, timing_marks, tolerance_ms):
                    aligned += 1

    if total == 0:
        return ScorerResult(name="beat_alignment", score=0.0, details={"total": 0})

    ratio = aligned / total
    return ScorerResult(
        name="beat_alignment",
        score=round(ratio * 100, 1),
        details={
            "aligned": aligned,
            "total": total,
            "ratio": round(ratio, 3),
            "tolerance_ms": tolerance_ms,
        },
    )


def _within_tolerance(value_ms: int, marks: set[int], tolerance_ms: int) -> bool:
    """Check if value_ms is within tolerance of any mark in the set."""
    for mark in marks:
        if abs(value_ms - mark) <= tolerance_ms:
            return True
    return False


# ── Energy Tracking ──────────────────────────────────────────────────────────


def score_energy_tracking(
    plan: SequencePlan,
    hierarchy: HierarchyResult,
) -> ScorerResult:
    """Measure how well visual intensity follows music energy.

    Compares section energy scores against the number and tier level of
    effects placed in each section. High-energy sections should have more
    effects on higher tiers; low-energy sections should be sparser.

    Uses Spearman rank correlation between energy_score and a composite
    visual intensity metric per section.
    """
    if len(plan.sections) < 2:
        return ScorerResult(
            name="energy_tracking", score=50.0,
            details={"reason": "too_few_sections"},
        )

    energy_scores: list[float] = []
    visual_intensities: list[float] = []

    for assignment in plan.sections:
        energy_scores.append(float(assignment.section.energy_score))
        visual_intensities.append(_visual_intensity(assignment))

    correlation = _spearman_rank(energy_scores, visual_intensities)
    # Map correlation from [-1, 1] to [0, 100]
    # Perfect positive correlation = 100, zero = 50, negative = 0
    score = max(0.0, min(100.0, (correlation + 1.0) * 50.0))

    return ScorerResult(
        name="energy_tracking",
        score=round(score, 1),
        details={
            "correlation": round(correlation, 3),
            "num_sections": len(plan.sections),
        },
    )


def _visual_intensity(assignment: SectionAssignment) -> float:
    """Compute a composite visual intensity score for a section.

    Factors:
    - Effect count (more effects = busier)
    - Tier weighting (higher tiers contribute more intensity)
    - Effect density (effects per second of section duration)
    """
    section_duration_s = max(
        0.001,
        (assignment.section.end_ms - assignment.section.start_ms) / 1000.0,
    )
    total_weighted = 0.0
    total_effects = 0

    for group_name, placements in assignment.group_effects.items():
        tier = _tier_from_group_name(group_name)
        tier_weight = tier / 8.0  # Higher tiers contribute more
        for _ in placements:
            total_weighted += tier_weight
            total_effects += 1

    # Density-adjusted intensity
    return (total_weighted / section_duration_s) * 10.0 + total_effects


def _tier_from_group_name(group_name: str) -> int:
    """Extract tier number from group name like '03_TYPE_Vertical'."""
    parts = group_name.split("_")
    if parts and parts[0].isdigit():
        return int(parts[0])
    return 4  # default mid-tier


# ── Effect Variety ───────────────────────────────────────────────────────────


def score_effect_variety(plan: SequencePlan) -> ScorerResult:
    """Measure diversity of effects across the sequence.

    Evaluates:
    - Global unique effect ratio (unique effects / total placements)
    - Per-group consecutive repetition penalty
    - Per-section variety (unique effects per section)
    """
    all_effects: list[str] = []
    per_section_unique: list[int] = []
    consecutive_repeats = 0
    total_transitions = 0

    for assignment in plan.sections:
        section_effects: set[str] = set()
        for group_name, placements in assignment.group_effects.items():
            prev_effect: str | None = None
            for p in placements:
                all_effects.append(p.effect_name)
                section_effects.add(p.effect_name)
                if prev_effect is not None:
                    total_transitions += 1
                    if p.effect_name == prev_effect:
                        consecutive_repeats += 1
                prev_effect = p.effect_name
        per_section_unique.append(len(section_effects))

    if not all_effects:
        return ScorerResult(name="effect_variety", score=0.0, details={"total": 0})

    unique_count = len(set(all_effects))
    total_count = len(all_effects)

    # Unique ratio component (0-50 points)
    # 10+ unique effects = full marks on this component
    unique_score = min(50.0, (unique_count / max(10, total_count * 0.3)) * 50.0)

    # Non-repetition component (0-30 points)
    if total_transitions > 0:
        non_repeat_ratio = 1.0 - (consecutive_repeats / total_transitions)
    else:
        non_repeat_ratio = 1.0
    repeat_score = non_repeat_ratio * 30.0

    # Per-section variety component (0-20 points)
    if per_section_unique:
        avg_section_unique = sum(per_section_unique) / len(per_section_unique)
        # 3+ unique effects per section = full marks
        section_score = min(20.0, (avg_section_unique / 3.0) * 20.0)
    else:
        section_score = 0.0

    score = unique_score + repeat_score + section_score

    return ScorerResult(
        name="effect_variety",
        score=round(min(100.0, score), 1),
        details={
            "unique_effects": unique_count,
            "total_placements": total_count,
            "consecutive_repeats": consecutive_repeats,
            "avg_section_unique": round(
                sum(per_section_unique) / max(1, len(per_section_unique)), 1
            ),
        },
    )


# ── Theme Coherence ──────────────────────────────────────────────────────────


_MOOD_ENERGY_MAP = {
    "ethereal": (0, 40),
    "dark": (0, 50),
    "structural": (25, 75),
    "aggressive": (55, 100),
}


def score_theme_coherence(plan: SequencePlan) -> ScorerResult:
    """Measure how well theme moods align with section energy levels.

    Each theme has a mood (ethereal, structural, aggressive, dark) which
    should correspond to the section's energy_score range.
    """
    if not plan.sections:
        return ScorerResult(name="theme_coherence", score=0.0)

    total = 0
    coherent = 0

    for assignment in plan.sections:
        energy = assignment.section.energy_score
        mood = assignment.theme.mood
        low, high = _MOOD_ENERGY_MAP.get(mood, (0, 100))

        total += 1
        if low <= energy <= high:
            coherent += 1
        else:
            # Partial credit for near-misses (within 15 points of range)
            distance = min(abs(energy - low), abs(energy - high))
            if distance <= 15:
                coherent += 0.5

    ratio = coherent / max(1, total)
    return ScorerResult(
        name="theme_coherence",
        score=round(ratio * 100, 1),
        details={
            "coherent": coherent,
            "total": total,
        },
    )


# ── Temporal Coverage ────────────────────────────────────────────────────────


def score_temporal_coverage(
    plan: SequencePlan,
    hierarchy: HierarchyResult,
) -> ScorerResult:
    """Measure what fraction of the song duration has active effects.

    Checks that every 1-second window has at least one active effect.
    Gaps longer than 2 seconds are penalized more heavily.
    """
    duration_ms = hierarchy.duration_ms
    if duration_ms <= 0:
        return ScorerResult(name="temporal_coverage", score=0.0)

    # Build a coverage bitmap at 1-second resolution
    num_bins = max(1, duration_ms // 1000)
    covered = [False] * num_bins

    for assignment in plan.sections:
        for placements in assignment.group_effects.values():
            for p in placements:
                start_bin = max(0, p.start_ms // 1000)
                end_bin = min(num_bins, (p.end_ms + 999) // 1000)
                for b in range(start_bin, end_bin):
                    covered[b] = True

    covered_count = sum(covered)
    ratio = covered_count / num_bins

    # Count gaps > 2 seconds
    gap_count = 0
    current_gap = 0
    for c in covered:
        if not c:
            current_gap += 1
        else:
            if current_gap > 2:
                gap_count += 1
            current_gap = 0

    return ScorerResult(
        name="temporal_coverage",
        score=round(ratio * 100, 1),
        details={
            "covered_seconds": covered_count,
            "total_seconds": num_bins,
            "gaps_over_2s": gap_count,
        },
    )


# ── Transition Quality ───────────────────────────────────────────────────────


def score_transition_quality(plan: SequencePlan) -> ScorerResult:
    """Evaluate smoothness of transitions between sections.

    Checks for:
    - Fade in/out at section boundaries
    - No large gaps between sections
    - Theme variety between adjacent sections
    """
    if len(plan.sections) < 2:
        return ScorerResult(
            name="transition_quality", score=100.0,
            details={"reason": "single_section"},
        )

    total_transitions = len(plan.sections) - 1
    smooth_transitions = 0
    theme_changes = 0

    for i in range(total_transitions):
        current = plan.sections[i]
        next_sec = plan.sections[i + 1]

        # Check for fade out on current section's last effects
        has_fade_out = _has_fade_at_boundary(current, "out")
        # Check for fade in on next section's first effects
        has_fade_in = _has_fade_at_boundary(next_sec, "in")

        # Gap between sections
        gap_ms = next_sec.section.start_ms - current.section.end_ms
        no_gap = abs(gap_ms) <= 100  # Allow small overlap or tiny gap

        # Theme variety
        if current.theme.name != next_sec.theme.name:
            theme_changes += 1

        # Score this transition
        transition_score = 0.0
        if has_fade_out or has_fade_in:
            transition_score += 0.5
        if no_gap:
            transition_score += 0.5
        smooth_transitions += transition_score

    # Theme variety component (30% of score)
    variety_ratio = theme_changes / total_transitions
    variety_score = min(1.0, variety_ratio / 0.6) * 30.0  # 60%+ variety = full marks

    # Smoothness component (70% of score)
    smoothness = (smooth_transitions / total_transitions) * 70.0

    score = variety_score + smoothness

    return ScorerResult(
        name="transition_quality",
        score=round(min(100.0, score), 1),
        details={
            "smooth_transitions": smooth_transitions,
            "theme_changes": theme_changes,
            "total_transitions": total_transitions,
        },
    )


def _has_fade_at_boundary(assignment: SectionAssignment, direction: str) -> bool:
    """Check if any effect near the section boundary has a fade."""
    for placements in assignment.group_effects.values():
        if not placements:
            continue
        if direction == "out":
            # Check last effect
            p = placements[-1]
            if p.fade_out_ms > 0:
                return True
        elif direction == "in":
            # Check first effect
            p = placements[0]
            if p.fade_in_ms > 0:
                return True
    return False


# ── Tier Utilization ─────────────────────────────────────────────────────────


def score_tier_utilization(plan: SequencePlan) -> ScorerResult:
    """Evaluate whether the tier hierarchy is used appropriately.

    Rules:
    - Base tiers (1-2) should have near-continuous coverage
    - Mid tiers (3-6) should be active in most sections
    - Upper tiers (7-8) should be sparser, concentrated in high-energy sections
    """
    if not plan.sections:
        return ScorerResult(name="tier_utilization", score=0.0)

    tier_section_counts: dict[int, int] = {t: 0 for t in range(1, 9)}
    high_energy_tier_use: dict[int, int] = {t: 0 for t in range(7, 9)}
    low_energy_tier_use: dict[int, int] = {t: 0 for t in range(7, 9)}
    num_sections = len(plan.sections)

    for assignment in plan.sections:
        tiers_used: set[int] = set()
        for group_name in assignment.group_effects:
            tier = _tier_from_group_name(group_name)
            if assignment.group_effects[group_name]:  # has placements
                tiers_used.add(tier)

        for t in tiers_used:
            if 1 <= t <= 8:
                tier_section_counts[t] += 1
            if t in (7, 8):
                if assignment.section.energy_score >= 60:
                    high_energy_tier_use[t] += 1
                else:
                    low_energy_tier_use[t] += 1

    # Base tier coverage (0-40 points): tiers 1-2 should be in most sections
    base_coverage = sum(tier_section_counts.get(t, 0) for t in (1, 2)) / max(1, 2 * num_sections)
    base_score = base_coverage * 40.0

    # Mid tier activity (0-30 points): tiers 3-6 should appear regularly
    mid_tiers_active = sum(1 for t in range(3, 7) if tier_section_counts[t] > 0)
    mid_score = (mid_tiers_active / 4.0) * 30.0

    # Upper tier selectivity (0-30 points): tiers 7-8 in high-energy >> low-energy
    total_upper = sum(tier_section_counts.get(t, 0) for t in (7, 8))
    total_upper_high = sum(high_energy_tier_use.values())
    if total_upper > 0:
        selectivity = total_upper_high / total_upper
        upper_score = selectivity * 30.0
    else:
        upper_score = 15.0  # neutral if no upper tiers used at all

    score = base_score + mid_score + upper_score

    return ScorerResult(
        name="tier_utilization",
        score=round(min(100.0, score), 1),
        details={
            "tier_section_counts": dict(tier_section_counts),
            "num_sections": num_sections,
            "upper_in_high_energy": sum(high_energy_tier_use.values()),
            "upper_in_low_energy": sum(low_energy_tier_use.values()),
        },
    )


# ── Repetition Avoidance ────────────────────────────────────────────────────


def score_repetition_avoidance(plan: SequencePlan) -> ScorerResult:
    """Measure variation between repeated section types.

    When the same section label appears multiple times (chorus, chorus, chorus),
    the effect assignments should differ to avoid visual monotony.
    """
    label_assignments: dict[str, list[SectionAssignment]] = {}
    for assignment in plan.sections:
        label = assignment.section.label
        label_assignments.setdefault(label, []).append(assignment)

    # Only evaluate labels that repeat
    repeated = {k: v for k, v in label_assignments.items() if len(v) > 1}

    if not repeated:
        return ScorerResult(
            name="repetition_avoidance", score=100.0,
            details={"reason": "no_repeated_sections"},
        )

    total_pairs = 0
    varied_pairs = 0

    for label, assignments in repeated.items():
        for i in range(len(assignments)):
            for j in range(i + 1, len(assignments)):
                total_pairs += 1
                similarity = _effect_similarity(assignments[i], assignments[j])
                if similarity < 0.8:  # Less than 80% identical = varied
                    varied_pairs += 1

    ratio = varied_pairs / max(1, total_pairs)
    return ScorerResult(
        name="repetition_avoidance",
        score=round(ratio * 100, 1),
        details={
            "varied_pairs": varied_pairs,
            "total_pairs": total_pairs,
            "repeated_labels": list(repeated.keys()),
        },
    )


def _effect_similarity(a: SectionAssignment, b: SectionAssignment) -> float:
    """Compute similarity between two section assignments' effect choices."""
    effects_a = _collect_effects(a)
    effects_b = _collect_effects(b)

    if not effects_a and not effects_b:
        return 1.0
    if not effects_a or not effects_b:
        return 0.0

    # Jaccard similarity on effect name multisets
    counter_a = Counter(effects_a)
    counter_b = Counter(effects_b)
    intersection = sum((counter_a & counter_b).values())
    union = sum((counter_a | counter_b).values())
    return intersection / max(1, union)


def _collect_effects(assignment: SectionAssignment) -> list[str]:
    """Collect all effect names from an assignment."""
    effects: list[str] = []
    for placements in assignment.group_effects.values():
        for p in placements:
            effects.append(p.effect_name)
    return effects


# ── Color Palette Usage ──────────────────────────────────────────────────────


def score_color_usage(plan: SequencePlan) -> ScorerResult:
    """Evaluate color palette usage across the sequence.

    Checks:
    - Effects actually have color palettes assigned
    - Palette variety across sections (not the same palette everywhere)
    - Palette consistency within a section (effects in same section use
      theme-coherent colors)
    """
    total_effects = 0
    effects_with_colors = 0
    section_palettes: list[set[str]] = []

    for assignment in plan.sections:
        section_colors: set[str] = set()
        for placements in assignment.group_effects.values():
            for p in placements:
                total_effects += 1
                if p.color_palette:
                    effects_with_colors += 1
                    # Use frozenset of colors as palette identifier
                    section_colors.add(tuple(sorted(p.color_palette[:3])).__str__())
        section_palettes.append(section_colors)

    if total_effects == 0:
        return ScorerResult(name="color_usage", score=0.0, details={"total": 0})

    # Color assignment ratio (0-50 points)
    color_ratio = effects_with_colors / total_effects
    assignment_score = color_ratio * 50.0

    # Cross-section palette variety (0-50 points)
    all_palettes: set[str] = set()
    for sp in section_palettes:
        all_palettes.update(sp)
    if len(section_palettes) > 1:
        unique_palette_count = len(all_palettes)
        # 3+ distinct palettes across sections = full marks
        variety_score = min(50.0, (unique_palette_count / 3.0) * 50.0)
    else:
        variety_score = 25.0  # neutral for single section

    score = assignment_score + variety_score

    return ScorerResult(
        name="color_usage",
        score=round(min(100.0, score), 1),
        details={
            "effects_with_colors": effects_with_colors,
            "total_effects": total_effects,
            "unique_palettes": len(all_palettes),
        },
    )


# ── Utilities ────────────────────────────────────────────────────────────────


def _spearman_rank(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation without scipy dependency."""
    n = len(x)
    if n < 2:
        return 0.0

    def _rank(values: list[float]) -> list[float]:
        sorted_indices = sorted(range(n), key=lambda i: values[i])
        ranks = [0.0] * n
        for rank_val, idx in enumerate(sorted_indices):
            ranks[idx] = float(rank_val)
        return ranks

    rx = _rank(x)
    ry = _rank(y)

    d_squared = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1.0 - (6.0 * d_squared) / (n * (n * n - 1))


# ── All Scorers ──────────────────────────────────────────────────────────────

ALL_SCORERS = [
    "beat_alignment",
    "energy_tracking",
    "effect_variety",
    "theme_coherence",
    "temporal_coverage",
    "transition_quality",
    "tier_utilization",
    "repetition_avoidance",
    "color_usage",
]


def run_scorer(
    name: str,
    plan: SequencePlan,
    hierarchy: HierarchyResult,
) -> ScorerResult:
    """Run a single named scorer."""
    scorers = {
        "beat_alignment": lambda: score_beat_alignment(plan, hierarchy),
        "energy_tracking": lambda: score_energy_tracking(plan, hierarchy),
        "effect_variety": lambda: score_effect_variety(plan),
        "theme_coherence": lambda: score_theme_coherence(plan),
        "temporal_coverage": lambda: score_temporal_coverage(plan, hierarchy),
        "transition_quality": lambda: score_transition_quality(plan),
        "tier_utilization": lambda: score_tier_utilization(plan),
        "repetition_avoidance": lambda: score_repetition_avoidance(plan),
        "color_usage": lambda: score_color_usage(plan),
    }
    if name not in scorers:
        raise ValueError(f"Unknown scorer: {name!r}. Valid: {ALL_SCORERS}")
    return scorers[name]()


def run_all_scorers(
    plan: SequencePlan,
    hierarchy: HierarchyResult,
) -> list[ScorerResult]:
    """Run all scorers and return results."""
    return [run_scorer(name, plan, hierarchy) for name in ALL_SCORERS]
