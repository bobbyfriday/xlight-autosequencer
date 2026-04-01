"""Tests for library entry deletion and file cleanup."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from src.library import Library, LibraryEntry, delete_files_for_entry


@pytest.fixture
def lib_path(tmp_path):
    """Create a temporary library index."""
    path = tmp_path / "library.json"
    path.write_text(json.dumps({"version": "1.0", "entries": []}))
    return path


@pytest.fixture
def lib(lib_path):
    return Library(index_path=lib_path)


@pytest.fixture
def sample_entry(tmp_path):
    """Create a sample library entry with files on disk."""
    song_dir = tmp_path / "songs" / "test_song"
    song_dir.mkdir(parents=True)

    mp3_path = song_dir / "test_song.mp3"
    mp3_path.write_bytes(b"fake mp3 data")

    analysis_path = song_dir / "test_song_hierarchy.json"
    analysis_path.write_text(json.dumps({"schema_version": "2.0.0"}))

    story_path = song_dir / "test_song_story.json"
    story_path.write_text(json.dumps({"sections": []}))

    stems_dir = song_dir / "stems"
    stems_dir.mkdir()
    (stems_dir / "drums.mp3").write_bytes(b"fake drums")
    (stems_dir / "vocals.mp3").write_bytes(b"fake vocals")

    return LibraryEntry(
        source_hash="abc123def",
        source_file=str(mp3_path),
        filename="test_song.mp3",
        analysis_path=str(analysis_path),
        duration_ms=180000,
        estimated_tempo_bpm=120.0,
        track_count=22,
        stem_separation=True,
        analyzed_at=1711843200000,
    )


class TestLibraryRemoveEntry:
    def test_remove_existing_entry(self, lib, sample_entry):
        lib.upsert(sample_entry)
        assert lib.find_by_hash("abc123def") is not None

        result = lib.remove_entry("abc123def")
        assert result is True
        assert lib.find_by_hash("abc123def") is None

    def test_remove_nonexistent_entry(self, lib):
        result = lib.remove_entry("nonexistent")
        assert result is False

    def test_remove_preserves_other_entries(self, lib, sample_entry):
        lib.upsert(sample_entry)

        other = LibraryEntry(
            source_hash="other123",
            source_file="/fake/other.mp3",
            filename="other.mp3",
            analysis_path="/fake/other_hierarchy.json",
            duration_ms=200000,
            estimated_tempo_bpm=140.0,
            track_count=10,
            stem_separation=False,
            analyzed_at=1711843200001,
        )
        lib.upsert(other)

        lib.remove_entry("abc123def")
        assert lib.find_by_hash("abc123def") is None
        assert lib.find_by_hash("other123") is not None


class TestDeleteFilesForEntry:
    def test_deletes_analysis_files(self, sample_entry):
        deleted = delete_files_for_entry(sample_entry)
        assert len(deleted) > 0
        assert not Path(sample_entry.analysis_path).exists()

    def test_deletes_story_file(self, sample_entry):
        mp3 = Path(sample_entry.source_file)
        story_path = mp3.parent / (mp3.stem + "_story.json")
        assert story_path.exists()

        delete_files_for_entry(sample_entry)
        assert not story_path.exists()

    def test_deletes_stems_directory(self, sample_entry):
        mp3 = Path(sample_entry.source_file)
        stems_dir = mp3.parent / "stems"
        assert stems_dir.exists()

        delete_files_for_entry(sample_entry)
        assert not stems_dir.exists()

    def test_preserves_source_mp3(self, sample_entry):
        """Source MP3 should NOT be deleted by delete_files_for_entry."""
        delete_files_for_entry(sample_entry)
        assert Path(sample_entry.source_file).exists()

    def test_handles_missing_files_gracefully(self, tmp_path):
        """Should not error if files don't exist."""
        entry = LibraryEntry(
            source_hash="missing123",
            source_file=str(tmp_path / "nonexistent.mp3"),
            filename="nonexistent.mp3",
            analysis_path=str(tmp_path / "nonexistent_hierarchy.json"),
            duration_ms=0,
            estimated_tempo_bpm=0.0,
            track_count=0,
            stem_separation=False,
            analyzed_at=0,
        )
        deleted = delete_files_for_entry(entry)
        assert deleted == []


class TestDeleteViaAPI:
    """Test DELETE /library/<hash> endpoint."""

    @pytest.fixture
    def client(self, lib_path, sample_entry):
        lib = Library(index_path=lib_path)
        lib.upsert(sample_entry)

        with patch("src.library.DEFAULT_LIBRARY_PATH", lib_path):
            from src.review.server import create_app
            app = create_app(analysis_path=None, audio_path=None)
            app.config["TESTING"] = True
            yield app.test_client()

    def test_delete_returns_200(self, client):
        resp = client.delete("/library/abc123def")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "deleted"
        assert data["files_deleted"] is False

    def test_delete_missing_returns_404(self, client):
        resp = client.delete("/library/nonexistent")
        assert resp.status_code == 404

    def test_delete_with_files(self, client):
        resp = client.delete("/library/abc123def?delete_files=true")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["files_deleted"] is True
