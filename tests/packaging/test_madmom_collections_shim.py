"""Regression pin for the madmom / Python-3.10+ collections shim.

madmom 0.16.1's ``processors.py`` does ``from collections import
MutableSequence``, which moved to ``collections.abc`` in Python 3.10. The
analyzer restores deprecated numpy aliases before importing madmom; it must
also restore ``collections.MutableSequence`` or madmom fails to import and
``madmom_beats`` / ``madmom_downbeats`` silently vanish from the analysis.

Two of these checks are source-text pins (CI-safe — they don't import the
heavy analyzer stack), mirroring ``test_vamp_path_env.py``. The third
exercises the shim's effect for real.
"""
from __future__ import annotations

import collections
import collections.abc
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src" / "analyzer"
VAMP_RUNNER = _SRC / "vamp_runner.py"
CAPABILITIES = _SRC / "capabilities.py"

_SHIM_NEEDLE = "collections.MutableSequence = collections.abc.MutableSequence"


def test_vamp_runner_restores_mutable_sequence() -> None:
    source = VAMP_RUNNER.read_text()
    assert "_collections.MutableSequence = _collections_abc.MutableSequence" in source, (
        "The collections.MutableSequence shim was removed from "
        "src/analyzer/vamp_runner.py — madmom 0.16.1 will fail to import on "
        "Python 3.10+ and madmom_beats/madmom_downbeats will silently vanish."
    )


def test_capabilities_probe_restores_mutable_sequence() -> None:
    source = CAPABILITIES.read_text()
    # Must appear in BOTH the subprocess probe string and the in-process
    # branch; otherwise the probe reports madmom unavailable and the
    # orchestrator never schedules it.
    assert source.count(_SHIM_NEEDLE) >= 2, (
        "src/analyzer/capabilities.py must restore collections.MutableSequence "
        "in both the .venv-vamp probe string and the in-process madmom import "
        "branch, or madmom is reported unavailable on Python 3.10+."
    )


def test_shim_logic_restores_mutable_sequence() -> None:
    """The shim idiom actually makes the legacy import path resolve."""
    # collections.abc always has it; the shim copies it onto the collections
    # top level, which is exactly what `from collections import MutableSequence`
    # needs on Python 3.10+.
    if not hasattr(collections, "MutableSequence"):
        collections.MutableSequence = collections.abc.MutableSequence  # type: ignore[attr-defined]
    from collections import MutableSequence  # noqa: F401

    assert MutableSequence is collections.abc.MutableSequence
