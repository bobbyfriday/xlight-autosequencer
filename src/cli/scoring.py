"""Scoring subcommand group."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from src.cli import cli


# ──────────────────────────────────────────────────────────────────────────────
# scoring subcommand group
# ──────────────────────────────────────────────────────────────────────────────

@cli.group("scoring")
def scoring_cmd() -> None:
    """Manage scoring configurations and profiles."""


@scoring_cmd.command("list")
def scoring_list_cmd() -> None:
    """List all available scoring profiles (project-local and user-global)."""
    from src.analyzer.scoring_config import list_profiles

    profiles = list_profiles()
    if not profiles:
        click.echo("No scoring profiles found.")
        click.echo("Use 'xlight-analyze scoring save <name> --from <config.toml>' to create one.")
        click.echo("Use 'xlight-analyze scoring defaults' to see the default configuration.")
        return

    click.echo("Scoring Profiles:")
    click.echo(f"  {'NAME':<20} {'SOURCE':<10}")
    for p in profiles:
        click.echo(f"  {p['name']:<20} {p['source']:<10}")
    click.echo("\n  (default)            built-in     Standard scoring weights")


@scoring_cmd.command("show")
@click.argument("name")
def scoring_show_cmd(name: str) -> None:
    """Display a scoring profile's configuration."""
    from src.analyzer.scoring_config import get_profile_path, ScoringConfig

    path = get_profile_path(name)
    if path is None:
        click.echo(f"ERROR: Profile '{name}' not found.", err=True)
        sys.exit(7)

    click.echo(f"Profile: {name} ({path})")
    click.echo(path.read_text(encoding="utf-8"))


@scoring_cmd.command("save")
@click.argument("name")
@click.option("--from", "source_path", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="Path to the TOML config file to save as a profile")
@click.option("--scope", default="project",
              type=click.Choice(["project", "user"], case_sensitive=False),
              help="Save to project-local (.scoring/) or user-global (~/.config/xlight/scoring/)")
def scoring_save_cmd(name: str, source_path: str, scope: str) -> None:
    """Save a TOML config file as a named scoring profile."""
    from src.analyzer.scoring_config import save_profile, ScoringConfig

    # Validate the config first
    try:
        ScoringConfig.from_toml(Path(source_path))
    except (ValueError, Exception) as exc:
        click.echo(f"ERROR: Invalid scoring config: {exc}", err=True)
        sys.exit(6)

    dest = save_profile(name, Path(source_path), scope=scope)
    click.echo(f"Saved profile '{name}' to {dest}")


@scoring_cmd.command("defaults")
def scoring_defaults_cmd() -> None:
    """Print the built-in default scoring configuration as TOML."""
    from src.analyzer.scoring_config import generate_default_toml

    click.echo(generate_default_toml(), nl=False)
