"""T009 — pin existing VAMP_PATH behavior in src/analyzer/capabilities.py.

The capability probe already prepends `VAMP_PATH` to its plugin search
(line ~97 of capabilities.py at the time of writing). This test is a
regression pin: if someone rewrites capabilities.py and drops the env
var handling, this test will fail loudly.

We deliberately DON'T import `capabilities` at module level — on some
systems that triggers pyannote/torchaudio compatibility errors that are
unrelated to the VAMP_PATH behavior we're checking.
"""
from __future__ import annotations

from pathlib import Path


CAPABILITIES_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "analyzer"
    / "capabilities.py"
)


def test_vamp_path_env_is_consulted_by_plugin_search() -> None:
    source = CAPABILITIES_PATH.read_text()

    # Regression-pin: the env var must be read and split on pathsep into
    # the plugin search list.
    assert 'os.environ.get("VAMP_PATH"' in source or "os.environ.get('VAMP_PATH'" in source, (
        "VAMP_PATH env-var read appears to have been removed from "
        "src/analyzer/capabilities.py — the packaged Tauri launcher "
        "depends on this to surface bundled plugins. See 052 plan R5."
    )
    assert "vamp_path.split(os.pathsep)" in source, (
        "VAMP_PATH must be split on os.pathsep (not ':' or ';' directly) "
        "to stay cross-platform."
    )
