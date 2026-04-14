"""Tests for the generation wizard."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.generator.models import GenerationConfig
from src.generator_wizard import GenerationWizard


class TestGenerationWizard:
    """Tests for GenerationWizard metadata detection and config construction."""

    def test_config_from_paths(self, tmp_path: Path):
        """Wizard constructs a valid GenerationConfig from audio and layout paths."""
        audio = tmp_path / "song.mp3"
        audio.touch()
        layout = tmp_path / "layout.xml"
        layout.write_text("<xlights_rgbeffects/>")

        wizard = GenerationWizard()
        config = wizard.build_config(
            audio_path=audio,
            layout_path=layout,
            genre="rock",
            occasion="christmas",
        )

        assert isinstance(config, GenerationConfig)
        assert config.audio_path == audio
        assert config.layout_path == layout
        assert config.genre == "rock"
        assert config.occasion == "christmas"

    def test_default_genre_and_occasion(self, tmp_path: Path):
        """Defaults to 'pop' genre and 'general' occasion."""
        audio = tmp_path / "song.mp3"
        audio.touch()
        layout = tmp_path / "layout.xml"
        layout.write_text("<xlights_rgbeffects/>")

        wizard = GenerationWizard()
        config = wizard.build_config(audio_path=audio, layout_path=layout)

        assert config.genre == "pop"
        assert config.occasion == "general"

    def test_output_dir_defaults_to_show_dir_when_available(self, tmp_path: Path, monkeypatch):
        """Output dir defaults to the xLights show directory when one is resolvable."""
        audio = tmp_path / "music" / "song.mp3"
        audio.parent.mkdir(parents=True)
        audio.touch()
        layout = tmp_path / "layout.xml"
        layout.write_text("<xlights_rgbeffects/>")
        show_dir = tmp_path / "xlights_show"
        show_dir.mkdir()

        monkeypatch.setattr("src.paths.get_show_dir", lambda: show_dir)

        wizard = GenerationWizard()
        config = wizard.build_config(audio_path=audio, layout_path=layout)

        assert config.output_dir == show_dir

    def test_output_dir_falls_back_to_audio_parent(self, tmp_path: Path, monkeypatch):
        """Output dir falls back to the audio file's parent when no show dir is available."""
        audio = tmp_path / "music" / "song.mp3"
        audio.parent.mkdir(parents=True)
        audio.touch()
        layout = tmp_path / "layout.xml"
        layout.write_text("<xlights_rgbeffects/>")

        monkeypatch.setattr("src.paths.get_show_dir", lambda: None)

        wizard = GenerationWizard()
        config = wizard.build_config(audio_path=audio, layout_path=layout)

        assert config.output_dir == audio.parent

    def test_metadata_detection_from_filename(self, tmp_path: Path):
        """Wizard extracts title from filename when no ID3 tags."""
        audio = tmp_path / "Jingle Bells.mp3"
        audio.touch()

        wizard = GenerationWizard()
        metadata = wizard.detect_metadata(audio)

        assert metadata["title"] == "Jingle Bells"

    def test_metadata_defaults(self, tmp_path: Path):
        """Metadata has sensible defaults when file has no tags."""
        audio = tmp_path / "song.mp3"
        audio.touch()

        wizard = GenerationWizard()
        metadata = wizard.detect_metadata(audio)

        assert "title" in metadata
        assert "artist" in metadata
        assert "genre" in metadata
