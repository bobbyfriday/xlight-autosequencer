"""T008 — model cache paths under Application Support/XLight/models/."""
from __future__ import annotations

from pathlib import Path
from unittest import mock

from src.packaging.models_paths import (
    get_download_state_path,
    get_model_cache_root,
    get_torch_home,
)


def test_torch_home_layout(tmp_path: Path) -> None:
    with mock.patch("src.packaging.models_paths.Path.home", return_value=tmp_path):
        torch_home = get_torch_home()

    assert torch_home == (
        tmp_path
        / "Library"
        / "Application Support"
        / "XLight"
        / "models"
        / "torch-hub"
    )
    assert (torch_home / "hub" / "checkpoints").is_dir()


def test_model_cache_root_created(tmp_path: Path) -> None:
    with mock.patch("src.packaging.models_paths.Path.home", return_value=tmp_path):
        root = get_model_cache_root()

    assert root.is_dir()
    assert root.name == "models"


def test_download_state_path_location(tmp_path: Path) -> None:
    with mock.patch("src.packaging.models_paths.Path.home", return_value=tmp_path):
        state = get_download_state_path()
        cache_root = get_model_cache_root()

    assert state.parent == cache_root
    assert state.name == ".download-state.json"
