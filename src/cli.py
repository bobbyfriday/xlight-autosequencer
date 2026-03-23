"""CLI entry point for xlight-analyze."""
from __future__ import annotations

import errno
import json
import sys
import threading
import webbrowser
from pathlib import Path

import click

from src import export as export_mod
from src.analyzer.result import AnalysisResult


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

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
        flag = "  ** HIGH DENSITY" if t.avg_interval_ms > 0 and t.avg_interval_ms < 200 else ""
        click.echo(
            f"  {t.quality_score:<6.2f}  {t.name:<20} {t.element_type:<12} "
            f"{stem:<10} {t.mark_count:>6}      {t.avg_interval_ms:>4} ms{flag}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main CLI group
# ──────────────────────────────────────────────────────────────────────────────

@click.group()
def cli() -> None:
    """xlight-analyze — generate xLights timing tracks from audio."""


# ──────────────────────────────────────────────────────────────────────────────
# analyze command
# ──────────────────────────────────────────────────────────────────────────────

@cli.command("analyze")
@click.argument("mp3_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", default=None, help="Output JSON path (default: <input>_analysis.json)")
@click.option(
    "--algorithms", default="all",
    help="Comma-separated algorithm names, or 'all'",
)
@click.option("--no-vamp", is_flag=True, default=False, help="Skip Vamp plugin algorithms")
@click.option("--no-madmom", is_flag=True, default=False, help="Skip madmom algorithms")
@click.option("--top", "top_n", default=None, type=int, help="Auto-export top N tracks")
@click.option(
    "--stems/--no-stems", "use_stems", default=False,
    help="Run stem separation before analysis (requires demucs)",
)
def analyze_cmd(
    mp3_file: str,
    output: str | None,
    algorithms: str,
    no_vamp: bool,
    no_madmom: bool,
    top_n: int | None,
    use_stems: bool,
) -> None:
    """Run all analysis algorithms on MP3_FILE and write a JSON result."""
    from src.analyzer.runner import AnalysisRunner, default_algorithms

    audio_path = Path(mp3_file)

    # Determine output path
    if output is None:
        out_path = str(audio_path.parent / (audio_path.stem + "_analysis.json"))
    else:
        out_path = output

    # Check output is writable
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).touch()
    except OSError as exc:
        click.echo(f"ERROR: Cannot write to {out_path}: {exc}", err=True)
        sys.exit(3)

    # Build algorithm list
    algo_list = default_algorithms(
        include_vamp=not no_vamp,
        include_madmom=not no_madmom,
    )

    # Optional algorithm filter
    if algorithms.strip().lower() != "all":
        names = {n.strip() for n in algorithms.split(",")}
        algo_list = [a for a in algo_list if a.name in names]

    if no_vamp:
        click.echo("INFO: --no-vamp specified — Vamp algorithms skipped.", err=True)
    if no_madmom:
        click.echo("INFO: --no-madmom specified — madmom algorithms skipped.", err=True)

    total = len(algo_list)

    def progress(idx, total, name, mark_count):
        click.echo(f"  [{idx:>2}/{total}] {name:<35} ... done ({mark_count} marks)")

    # Quick load to show duration/BPM header before running
    try:
        from src.analyzer.audio import load
        import librosa, numpy as np
        audio, sr, meta = load(str(audio_path))
        try:
            tempo_arr, _ = librosa.beat.beat_track(y=audio, sr=sr, hop_length=512)
            bpm = float(np.atleast_1d(tempo_arr)[0])
        except Exception:
            bpm = 0.0
        click.echo(
            f"Analyzing: {audio_path} ({_format_duration(meta.duration_ms)}) | BPM: ~{bpm:.1f}"
        )
    except Exception as exc:
        click.echo(f"ERROR: Cannot load {mp3_file}: {exc}", err=True)
        sys.exit(1)

    # Stem separation (optional, requires demucs)
    stems = None
    if use_stems:
        try:
            from src.analyzer.stems import StemSeparator
            sep = StemSeparator()
            stems = sep.separate(audio_path)
        except Exception as exc:
            click.echo(
                f"WARNING: Stem separation failed ({exc}). Falling back to full-mix analysis.",
                err=True,
            )
            stems = None

    runner = AnalysisRunner(algo_list)

    try:
        result = runner.run(str(audio_path), progress_callback=progress, stems=stems)
    except Exception as exc:
        click.echo(f"ERROR: Analysis failed: {exc}", err=True)
        sys.exit(2)

    if not result.timing_tracks:
        click.echo("ERROR: All algorithms failed — no output written.", err=True)
        sys.exit(2)

    try:
        export_mod.write(result, out_path)
    except OSError as exc:
        click.echo(f"ERROR: Cannot write output: {exc}", err=True)
        sys.exit(3)

    click.echo(f"\nAnalysis complete. Output: {out_path}")
    _print_summary_table(result.timing_tracks)

    if top_n is not None:
        click.echo(f"\nAuto-selecting top {top_n} tracks by quality score...")
        top_path = str(audio_path.parent / f"{audio_path.stem}_top{top_n}.json")
        sorted_tracks = sorted(
            result.timing_tracks, key=lambda t: t.quality_score, reverse=True
        )[:top_n]
        top_result = AnalysisResult(
            schema_version=result.schema_version,
            source_file=result.source_file,
            filename=result.filename,
            duration_ms=result.duration_ms,
            sample_rate=result.sample_rate,
            estimated_tempo_bpm=result.estimated_tempo_bpm,
            run_timestamp=result.run_timestamp,
            algorithms=[
                a for a in result.algorithms
                if a.name in {t.algorithm_name for t in sorted_tracks}
            ],
            timing_tracks=sorted_tracks,
        )
        export_mod.write(top_result, top_path)
        click.echo(f"Output: {top_path}")
    else:
        click.echo("\nUse --top N or 'xlight-analyze export' to select tracks.")


# ──────────────────────────────────────────────────────────────────────────────
# summary command
# ──────────────────────────────────────────────────────────────────────────────

@cli.command("summary")
@click.argument("analysis_json", type=click.Path(exists=True, dir_okay=False))
@click.option("--top", "top_n", default=None, type=int, help="Show only top N tracks")
def summary_cmd(analysis_json: str, top_n: int | None) -> None:
    """Print the scored summary table from an existing analysis JSON."""
    try:
        result = export_mod.read(analysis_json)
    except Exception as exc:
        click.echo(f"ERROR: Cannot read {analysis_json}: {exc}", err=True)
        sys.exit(1)

    duration_str = _format_duration(result.duration_ms)
    click.echo(
        f"Source: {result.filename} ({duration_str}) | BPM: {result.estimated_tempo_bpm} "
        f"| Analyzed: {result.run_timestamp} | {len(result.timing_tracks)} tracks"
    )
    _print_summary_table(result.timing_tracks, limit=top_n)


# ──────────────────────────────────────────────────────────────────────────────
# export command
# ──────────────────────────────────────────────────────────────────────────────

@cli.command("export")
@click.argument("analysis_json", type=click.Path(exists=True, dir_okay=False))
@click.option("--select", "select_names", default=None, help="Comma-separated track names")
@click.option("--top", "top_n", default=None, type=int, help="Top N tracks by quality score")
@click.option("--output", default=None, help="Output path (default: <input>_selected.json)")
def export_cmd(
    analysis_json: str,
    select_names: str | None,
    top_n: int | None,
    output: str | None,
) -> None:
    """Filter an existing analysis to a subset of tracks and write a new JSON."""
    if select_names is None and top_n is None:
        click.echo("ERROR: Provide --select <names> or --top <N>.", err=True)
        sys.exit(5)

    try:
        result = export_mod.read(analysis_json)
    except Exception as exc:
        click.echo(f"ERROR: Cannot read {analysis_json}: {exc}", err=True)
        sys.exit(1)

    if top_n is not None:
        selected = sorted(
            result.timing_tracks, key=lambda t: t.quality_score, reverse=True
        )[:top_n]
        label = f"top {top_n}"
    else:
        names = {n.strip() for n in select_names.split(",")}
        track_map = {t.name: t for t in result.timing_tracks}
        missing = names - track_map.keys()
        if missing:
            click.echo(
                f"ERROR: Track(s) not found: {', '.join(sorted(missing))}. "
                f"Available: {', '.join(sorted(track_map.keys()))}",
                err=True,
            )
            sys.exit(4)
        selected = [track_map[n] for n in names if n in track_map]
        label = f"selected {len(selected)}"

    in_path = Path(analysis_json)
    out_path = output or str(in_path.parent / (in_path.stem.replace("_analysis", "") + "_selected.json"))

    filtered = AnalysisResult(
        schema_version=result.schema_version,
        source_file=result.source_file,
        filename=result.filename,
        duration_ms=result.duration_ms,
        sample_rate=result.sample_rate,
        estimated_tempo_bpm=result.estimated_tempo_bpm,
        run_timestamp=result.run_timestamp,
        algorithms=[
            a for a in result.algorithms
            if a.name in {t.algorithm_name for t in selected}
        ],
        timing_tracks=selected,
    )

    try:
        export_mod.write(filtered, out_path)
    except OSError as exc:
        click.echo(f"ERROR: Cannot write output: {exc}", err=True)
        sys.exit(3)

    click.echo(
        f"Exporting {label} of {len(result.timing_tracks)} tracks from {analysis_json}"
    )
    _print_summary_table(selected)
    click.echo(f"\nOutput: {out_path}")


# ──────────────────────────────────────────────────────────────────────────────
# review command
# ──────────────────────────────────────────────────────────────────────────────

@cli.command("review")
@click.argument("analysis_json", required=False, default=None, type=click.Path(dir_okay=False))
def review_cmd(analysis_json: str | None) -> None:
    """Launch the track review UI in the default browser."""
    from src.review.server import create_app

    if analysis_json is None:
        app = create_app()
        url = "http://127.0.0.1:5173/"
        click.echo(f"Starting upload UI at {url}")
        click.echo("Press Ctrl-C to stop.")
        threading.Timer(0.5, webbrowser.open, args=[url]).start()
        try:
            app.run(host="127.0.0.1", port=5173, use_reloader=False, debug=False)
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                click.echo(
                    "ERROR: Port 5173 is already in use.\n"
                    "Kill the process using that port and try again.",
                    err=True,
                )
                sys.exit(5)
            raise
        return

    analysis_path = Path(analysis_json)
    if not analysis_path.exists():
        click.echo(f"ERROR: Analysis file not found: {analysis_json}", err=True)
        sys.exit(4)

    try:
        with open(analysis_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        click.echo(f"ERROR: Cannot read {analysis_json}: {exc}", err=True)
        sys.exit(4)

    audio_path_str = data.get("source_file", "")
    if not audio_path_str or not Path(audio_path_str).exists():
        click.echo(
            f"ERROR: Audio file not found: {audio_path_str!r}\n"
            "The analysis JSON's 'source_file' path does not exist on this machine.",
            err=True,
        )
        sys.exit(3)

    app = create_app(str(analysis_path.resolve()), audio_path_str)

    url = "http://127.0.0.1:5173/"
    click.echo(f"Starting review UI at {url}")
    click.echo("Press Ctrl-C to stop.")

    threading.Timer(0.5, webbrowser.open, args=[url]).start()

    try:
        app.run(host="127.0.0.1", port=5173, use_reloader=False, debug=False)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            click.echo(
                "ERROR: Port 5173 is already in use.\n"
                "Kill the process using that port and try again.",
                err=True,
            )
            sys.exit(5)
        raise


def main() -> None:
    cli()
