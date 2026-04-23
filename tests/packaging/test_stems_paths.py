"""T006 — stems cache-root writable-fallback behavior."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest import mock

import pytest

from src.packaging.stems_paths import resolve_cache_root, _user_fallback_root


def test_prefers_source_adjacent_when_writable(tmp_path: Path) -> None:
    song_dir = tmp_path / "MySong"
    song_dir.mkdir()
    source = song_dir / "MySong.mp3"
    source.touch()

    result = resolve_cache_root(source)

    assert result == song_dir / "stems"


def test_uses_named_subdir_when_parent_name_differs(tmp_path: Path) -> None:
    source = tmp_path / "track.mp3"
    source.touch()

    result = resolve_cache_root(source)

    assert result == tmp_path / "track" / "stems"


def test_falls_back_to_application_support_when_parent_unwritable(
    tmp_path: Path,
) -> None:
    song_dir = tmp_path / "readonly"
    song_dir.mkdir()
    source = song_dir / "readonly.mp3"
    source.touch()

    # Make the song directory read-only so the probe fails.
    os.chmod(song_dir, stat.S_IREAD | stat.S_IEXEC)

    fake_home = tmp_path / "fake_home"
    with mock.patch("src.packaging.stems_paths.Path.home", return_value=fake_home):
        try:
            result = resolve_cache_root(source)
        finally:
            # Restore so pytest cleanup can remove the tmp_path tree.
            os.chmod(song_dir, stat.S_IRWXU)

    expected = (
        fake_home
        / "Library"
        / "Application Support"
        / "XLight"
        / "stems"
        / "readonly"
        / "stems"
    )
    assert result == expected
    assert result.is_dir()


def test_user_fallback_root_shape() -> None:
    root = _user_fallback_root()
    assert root.name == "stems"
    assert root.parent.name == "XLight"
