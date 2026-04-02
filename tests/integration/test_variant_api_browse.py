"""Integration tests for variant browse API: GET /variants, GET /variants/<name>, GET /variants/coverage."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.effects.library import load_effect_library
from src.variants.library import load_variant_library

FIXTURES = Path(__file__).parent.parent / "fixtures"
EFFECTS_FIXTURE = FIXTURES / "effects" / "minimal_library_with_meteors.json"
VARIANTS_FIXTURE = FIXTURES / "variants" / "builtin_variants_minimal.json"


@pytest.fixture
def app(tmp_path):
    """Flask test app with variant routes wired to fixture data."""
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
    vr._builtin_names = None  # let it recompute from _builtin_path

    from src.review.server import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app

    vr._library = None
    vr._effect_library = None
    vr._custom_dir = None
    vr._builtin_path = None
    vr._builtin_names = None


@pytest.fixture
def client(app):
    return app.test_client()


class TestGetVariants:
    def test_returns_200(self, client):
        resp = client.get("/variants")
        assert resp.status_code == 200

    def test_returns_all_variants(self, client):
        data = client.get("/variants").get_json()
        assert len(data["variants"]) == 3

    def test_variants_have_required_fields(self, client):
        v = client.get("/variants").get_json()["variants"][0]
        for field in ("name", "base_effect", "description", "parameter_overrides", "tags",
                      "is_builtin", "inherited"):
            assert field in v, f"Missing field: {field}"

    def test_inherited_has_base_effect_info(self, client):
        data = client.get("/variants").get_json()
        fire = next(v for v in data["variants"] if v["name"] == "Fire Blaze High")
        inh = fire["inherited"]
        assert inh["category"] == "nature"
        assert "layer_role" in inh
        assert "prop_suitability" in inh

    def test_is_builtin_true_for_builtin(self, client):
        data = client.get("/variants").get_json()
        assert all(v["is_builtin"] for v in data["variants"])

    def test_filter_by_effect(self, client):
        data = client.get("/variants?effect=Meteors").get_json()
        assert len(data["variants"]) == 1
        assert data["variants"][0]["base_effect"] == "Meteors"

    def test_filter_by_effect_case_insensitive(self, client):
        data = client.get("/variants?effect=meteors").get_json()
        assert len(data["variants"]) == 1

    def test_filter_by_energy(self, client):
        data = client.get("/variants?energy=high").get_json()
        assert all(v["tags"]["energy_level"] == "high" for v in data["variants"])

    def test_filter_by_tier(self, client):
        data = client.get("/variants?tier=background").get_json()
        assert all(v["tags"]["tier_affinity"] == "background" for v in data["variants"])

    def test_filter_by_section(self, client):
        # Fire Blaze High and Bars Sweep Left both have chorus
        data = client.get("/variants?section=chorus").get_json()
        assert len(data["variants"]) == 2

    def test_filter_by_scope(self, client):
        data = client.get("/variants?scope=single-prop").get_json()
        assert len(data["variants"]) == 1
        assert data["variants"][0]["tags"]["scope"] == "single-prop"

    def test_free_text_search_name(self, client):
        data = client.get("/variants?q=Meteors").get_json()
        assert len(data["variants"]) == 1
        assert data["variants"][0]["name"] == "Meteors Gentle Rain"

    def test_free_text_search_description(self, client):
        data = client.get("/variants?q=gentle").get_json()
        assert len(data["variants"]) == 1

    def test_free_text_case_insensitive(self, client):
        data = client.get("/variants?q=METEOR").get_json()
        assert len(data["variants"]) == 1

    def test_returns_total_count(self, client):
        data = client.get("/variants").get_json()
        assert data["total"] == 3

    def test_total_reflects_filters(self, client):
        data = client.get("/variants?energy=high").get_json()
        assert data["total"] == len(data["variants"])

    def test_filters_applied_populated(self, client):
        data = client.get("/variants?energy=high").get_json()
        assert data["filters_applied"].get("energy") == "high"

    def test_filters_applied_empty_when_no_filters(self, client):
        data = client.get("/variants").get_json()
        assert data["filters_applied"] == {}


class TestGetVariantByName:
    def test_returns_200_for_existing(self, client):
        resp = client.get("/variants/Fire Blaze High")
        assert resp.status_code == 200

    def test_returns_correct_variant(self, client):
        data = client.get("/variants/Fire Blaze High").get_json()
        assert data["name"] == "Fire Blaze High"
        assert data["base_effect"] == "Fire"

    def test_case_insensitive_lookup(self, client):
        resp = client.get("/variants/fire blaze high")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Fire Blaze High"

    def test_includes_inherited_info(self, client):
        data = client.get("/variants/Fire Blaze High").get_json()
        assert data["inherited"]["category"] == "nature"
        assert data["inherited"]["layer_role"] == "standalone"

    def test_is_builtin_true(self, client):
        data = client.get("/variants/Fire Blaze High").get_json()
        assert data["is_builtin"] is True

    def test_returns_404_for_unknown(self, client):
        resp = client.get("/variants/No Such Variant")
        assert resp.status_code == 404

    def test_404_has_error_field(self, client):
        data = client.get("/variants/No Such Variant").get_json()
        assert "error" in data


class TestGetVariantsCoverage:
    def test_returns_200(self, client):
        resp = client.get("/variants/coverage")
        assert resp.status_code == 200

    def test_returns_coverage_array(self, client):
        data = client.get("/variants/coverage").get_json()
        assert "coverage" in data
        assert isinstance(data["coverage"], list)

    def test_coverage_entries_have_required_fields(self, client):
        data = client.get("/variants/coverage").get_json()
        entry = next(e for e in data["coverage"] if e["variant_count"] > 0)
        for field in ("effect", "category", "variant_count", "tag_completeness"):
            assert field in entry, f"Missing field: {field}"

    def test_total_variants_correct(self, client):
        data = client.get("/variants/coverage").get_json()
        assert data["total_variants"] == 3

    def test_effects_with_and_without_variants(self, client):
        data = client.get("/variants/coverage").get_json()
        assert "effects_with_variants" in data
        assert "effects_without_variants" in data
        # fixture has Fire, Bars, Meteors — all 3 have 1 variant each
        assert data["effects_with_variants"] == 3

    def test_coverage_not_confused_with_variant_by_name(self, client):
        # /variants/coverage must resolve to the coverage endpoint, not a variant named "coverage"
        resp = client.get("/variants/coverage")
        data = resp.get_json()
        assert "coverage" in data  # not {"error": "Variant not found: coverage"}
