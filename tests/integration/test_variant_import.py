"""Integration tests for variant import — CLI and POST /variants/import."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.cli import cli
from src.effects.library import load_effect_library
from src.variants.library import load_variant_library

FIXTURES = Path(__file__).parent.parent / "fixtures"
EFFECTS_FIXTURE = FIXTURES / "effects" / "minimal_library_with_meteors.json"
VARIANTS_FIXTURE = FIXTURES / "variants" / "builtin_variants_minimal.json"
XSQ_FIXTURE = FIXTURES / "xsq" / "sample_sequence.xsq"


# ── CLI fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_custom_dir(tmp_path):
    return tmp_path / "custom_variants"


@pytest.fixture(autouse=True)
def inject_libs(tmp_custom_dir, monkeypatch):
    import src.cli as cli_module

    effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
    lib = load_variant_library(
        builtin_path=VARIANTS_FIXTURE,
        custom_dir=tmp_custom_dir,
        effect_library=effect_lib,
    )
    monkeypatch.setattr(cli_module, "_variant_library_override", lib)
    monkeypatch.setattr(cli_module, "_variant_effect_library_override", effect_lib)
    monkeypatch.setattr(cli_module, "_variant_custom_dir_override", tmp_custom_dir)


# ── Flask fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def app(tmp_path):
    import src.review.variant_routes as vr

    effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
    lib = load_variant_library(
        builtin_path=VARIANTS_FIXTURE,
        custom_dir=tmp_path,
        effect_library=effect_lib,
    )

    vr._library = lib
    vr._effect_library = effect_lib
    vr._custom_dir = tmp_path
    vr._builtin_path = VARIANTS_FIXTURE


    from src.review.server import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app

    vr._library = None
    vr._effect_library = None
    vr._custom_dir = None
    vr._builtin_path = None



@pytest.fixture
def client(app):
    return app.test_client()


# ── CLI tests ─────────────────────────────────────────────────────────────────

class TestVariantImportCLI:
    def test_dry_run_exits_zero(self):
        result = CliRunner().invoke(
            cli,
            ["variant", "import", str(XSQ_FIXTURE), "--dry-run"],
        )
        assert result.exit_code == 0

    def test_dry_run_shows_table(self):
        result = CliRunner().invoke(
            cli,
            ["variant", "import", str(XSQ_FIXTURE), "--dry-run"],
        )
        assert "Status" in result.output or "imported" in result.output.lower()

    def test_dry_run_does_not_save(self, tmp_custom_dir):
        CliRunner().invoke(
            cli,
            ["variant", "import", str(XSQ_FIXTURE), "--dry-run"],
        )
        # No files should be saved in the custom dir
        saved = list(tmp_custom_dir.glob("*.json")) if tmp_custom_dir.exists() else []
        assert saved == []

    def test_summary_line_present(self):
        result = CliRunner().invoke(
            cli,
            ["variant", "import", str(XSQ_FIXTURE), "--dry-run"],
        )
        assert "Imported:" in result.output
        assert "Duplicates:" in result.output
        assert "Unknown:" in result.output

    def test_skip_duplicates_option(self):
        result = CliRunner().invoke(
            cli,
            ["variant", "import", str(XSQ_FIXTURE), "--dry-run", "--skip-duplicates"],
        )
        assert result.exit_code == 0

    def test_json_format_is_valid(self):
        result = CliRunner().invoke(
            cli,
            ["variant", "import", str(XSQ_FIXTURE), "--dry-run", "--format", "json"],
        )
        assert result.exit_code == 0
        # JSON should be parseable
        lines = result.output.strip().split("\n")
        # Find the JSON output (before the summary line)
        json_part = "\n".join(
            line for line in lines
            if not line.startswith("Imported:")
        )
        data = json.loads(json_part)
        assert isinstance(data, list)

    def test_import_saves_files(self, tmp_custom_dir):
        """Non-dry-run import saves variant JSON files."""
        result = CliRunner().invoke(
            cli,
            ["variant", "import", str(XSQ_FIXTURE)],
        )
        assert result.exit_code == 0
        saved = list(tmp_custom_dir.glob("*.json")) if tmp_custom_dir.exists() else []
        # Should have saved at least one imported variant
        imported_count = int(
            result.output.split("Imported:")[1].split("|")[0].strip()
        )
        assert len(saved) == imported_count


# ── API tests ─────────────────────────────────────────────────────────────────

class TestVariantImportAPI:
    def test_post_import_returns_200(self, client):
        with open(XSQ_FIXTURE, "rb") as f:
            resp = client.post(
                "/variants/import",
                data={"file": (f, "sample_sequence.xsq")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200

    def test_post_import_returns_summary(self, client):
        with open(XSQ_FIXTURE, "rb") as f:
            resp = client.post(
                "/variants/import",
                data={"file": (f, "sample_sequence.xsq")},
                content_type="multipart/form-data",
            )
        data = resp.get_json()
        assert "summary" in data
        assert "imported" in data["summary"]
        assert "duplicates" in data["summary"]
        assert "unknown" in data["summary"]

    def test_post_import_returns_lists(self, client):
        with open(XSQ_FIXTURE, "rb") as f:
            resp = client.post(
                "/variants/import",
                data={"file": (f, "sample_sequence.xsq")},
                content_type="multipart/form-data",
            )
        data = resp.get_json()
        assert isinstance(data["imported"], list)
        assert isinstance(data["duplicates"], list)
        assert isinstance(data["unknown"], list)

    def test_post_import_dry_run_param(self, client):
        with open(XSQ_FIXTURE, "rb") as f:
            resp = client.post(
                "/variants/import?dry_run=true",
                data={"file": (f, "sample_sequence.xsq")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200

    def test_post_import_skip_duplicates_param(self, client):
        # First import to populate the library
        with open(XSQ_FIXTURE, "rb") as f:
            client.post(
                "/variants/import",
                data={"file": (f, "sample_sequence.xsq")},
                content_type="multipart/form-data",
            )
        # Second import with skip_duplicates=true should have fewer results
        with open(XSQ_FIXTURE, "rb") as f:
            resp = client.post(
                "/variants/import?skip_duplicates=true",
                data={"file": (f, "sample_sequence.xsq")},
                content_type="multipart/form-data",
            )
        data = resp.get_json()
        assert data["summary"]["duplicates"] == 0

    def test_post_no_file_returns_400(self, client):
        resp = client.post(
            "/variants/import",
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_post_empty_filename_returns_400(self, client):
        resp = client.post(
            "/variants/import",
            data={"file": (b"", "")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
