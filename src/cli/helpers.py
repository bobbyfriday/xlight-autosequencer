"""Shared CLI helpers used across command modules."""
from __future__ import annotations

import click


def _format_duration(ms: int) -> str:
    total_s = ms // 1000
    return f"{total_s // 60}:{total_s % 60:02d}"


def _print_summary_table(tracks, *, limit: int | None = None) -> None:
    sorted_tracks = sorted(tracks, key=lambda t: t.quality_score, reverse=True)
    if limit is not None:
        sorted_tracks = sorted_tracks[:limit]
    click.echo("\nTrack Summary (sorted by quality score):")
    click.echo(f"  {'SCORE':<6}  {'NAME':<20} {'TYPE':<12} {'STEM':<10} {'MARKS':>6}   AVG INTERVAL")
    for t in sorted_tracks:
        stem = getattr(t, "stem_source", "full_mix") or "full_mix"
        bd = getattr(t, "score_breakdown", None)
        skip_note = ""
        if bd and bd.skipped_as_duplicate and bd.duplicate_of:
            skip_note = f"  [SKIPPED: near-identical to {bd.duplicate_of}]"
        flag = "  ** HIGH DENSITY" if t.avg_interval_ms > 0 and t.avg_interval_ms < 200 else ""
        click.echo(
            f"  {t.quality_score:<6.2f}  {t.name:<20} {t.element_type:<12} "
            f"{stem:<10} {t.mark_count:>6}      {t.avg_interval_ms:>4} ms{flag}{skip_note}"
        )


def _print_breakdown(tracks) -> None:
    """Print per-criterion score breakdowns for each track."""
    sorted_tracks = sorted(tracks, key=lambda t: t.quality_score, reverse=True)
    for t in sorted_tracks:
        bd = getattr(t, "score_breakdown", None)
        if bd is None:
            click.echo(f"\nTrack: {t.name} — no breakdown available")
            continue
        thresh_status = "PASS" if bd.passed_thresholds else f"FAIL ({', '.join(bd.threshold_failures)})"
        if bd.skipped_as_duplicate and bd.duplicate_of:
            click.echo(f"\nTrack: {t.name} (category: {bd.category})")
            click.echo(f"  Score: {bd.overall_score:.4f} | Thresholds: {thresh_status}")
            click.echo(f"  SKIPPED: near-identical to {bd.duplicate_of}")
        else:
            click.echo(f"\nTrack: {t.name} (category: {bd.category})")
            click.echo(f"  Score: {bd.overall_score:.4f} | Thresholds: {thresh_status}")
            for crit in bd.criteria:
                click.echo(
                    f"  {crit.name:<12} {crit.score:.2f}  "
                    f"({crit.measured_value:.3f}, target {crit.target_min:.2f}\u2013{crit.target_max:.2f}, "
                    f"weight {crit.weight:.2f}, contribution {crit.contribution:.4f})"
                )


def _rich_error(message: str, causes: list[str] | None = None, fixes: list[str] | None = None) -> str:
    """Format an error message with optional causes and fixes."""
    lines = [f"ERROR: {message}"]
    if causes:
        lines.append("\nPossible causes:")
        for c in causes:
            lines.append(f"  - {c}")
    if fixes:
        lines.append("\nHow to fix:")
        for f in fixes:
            lines.append(f"  {f}")
    return "\n".join(lines)
