"""Remaining CLI commands not yet split into dedicated modules.

These commands will be migrated to their own modules in future refactors.
For now they are imported from cli_old.py to avoid breaking existing
functionality.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from src.cli import cli

# ── Re-register commands from the legacy monolith ───────────────────────────
# Import the old module under a private name so its decorators fire,
# but redirect them to register on *our* cli group.
# We do this by monkey-patching the old module's `cli` reference.

import importlib
import src.cli_old as _old

# The old module defined its own `cli` group.  Steal its registered commands
# and re-register them on the new group.
for cmd_name, cmd_obj in list(_old.cli.commands.items()):
    if cmd_name not in cli.commands:
        cli.add_command(cmd_obj, cmd_name)

# Also steal any groups (like "scoring", "variant")
# These should already be included via the commands dict above.
