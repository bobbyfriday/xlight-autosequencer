"""Max-overlap section-mapping algorithm — T106 (US3).

Maps new sections to old sections by maximum time overlap.
Research §10 specifies a 0.3 threshold (intersection / new_duration).
"""
from __future__ import annotations

_OVERLAP_THRESHOLD = 0.3


def _intersection_ms(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Return the intersection duration between two [start, end) intervals."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def compute_overlap_mapping(
    old_sections: list[dict],
    new_sections: list[dict],
) -> dict:
    """Compute section mapping from old to new using max-overlap algorithm.

    Parameters
    ----------
    old_sections:
        List of old section dicts, each with ``start_ms``, ``end_ms``, ``index``,
        and ``theme_id``.
    new_sections:
        List of new section dicts with ``start_ms``, ``end_ms``, ``index``.

    Returns
    -------
    dict with two keys:
      ``mapping``: list of mapping entries for each new section.
        Each entry: {
          new_section_index: int,
          action: "kept" | "shifted" | "needs_theme",
          inherited_theme_id: str | None,
          inherited_from_old_index: int | None,
          overlap_ratio: float,
        }
      ``dropped``: list of old section entries that were not the best match
        for any new section: {old_section_index: int, theme_id: str | None}
    """
    if not new_sections:
        # All old sections become orphans
        dropped = [
            {"old_section_index": s["index"], "theme_id": s.get("theme_id")}
            for s in old_sections
        ]
        return {"mapping": [], "dropped": dropped}

    mapping: list[dict] = []
    # Track which old section indexes are claimed as the primary match
    matched_old_indexes: set[int] = set()

    for new_sec in new_sections:
        new_idx = new_sec["index"]
        new_start = new_sec["start_ms"]
        new_end = new_sec["end_ms"]
        new_dur = new_end - new_start

        best_overlap = 0
        best_old: dict | None = None
        best_old_idx: int | None = None

        for old_sec in old_sections:
            overlap = _intersection_ms(new_start, new_end, old_sec["start_ms"], old_sec["end_ms"])
            if overlap > best_overlap:
                best_overlap = overlap
                best_old = old_sec
                best_old_idx = old_sec["index"]

        if new_dur > 0 and best_old is not None:
            ratio = best_overlap / new_dur
        else:
            ratio = 0.0

        if ratio >= _OVERLAP_THRESHOLD and best_old is not None:
            # Determine carried-over action: if boundaries are identical → "kept", else "shifted"
            is_exact = (
                best_old["start_ms"] == new_start and best_old["end_ms"] == new_end
            )
            action = "kept" if is_exact else "shifted"
            theme_id = best_old.get("theme_id")
            if best_old_idx is not None:
                matched_old_indexes.add(best_old_idx)
        else:
            action = "needs_theme"
            theme_id = None
            best_old_idx = None

        mapping.append({
            "new_section_index": new_idx,
            "action": action,
            "inherited_theme_id": theme_id,
            "inherited_from_old_index": best_old_idx,
            "overlap_ratio": round(ratio, 4),
        })

    # Dropped = old sections that were not the best match for ANY new section
    dropped = [
        {"old_section_index": old_sec["index"], "theme_id": old_sec.get("theme_id")}
        for old_sec in old_sections
        if old_sec["index"] not in matched_old_indexes
    ]

    return {"mapping": mapping, "dropped": dropped}
