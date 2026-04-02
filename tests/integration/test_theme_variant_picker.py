"""Integration tests for variant picker wiring in the theme editor (T004-T005)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.effects.library import load_effect_library
from src.variants.library import load_variant_library

FIXTURES = Path(__file__).parent.parent / "fixtures"
EFFECTS_FIXTURE = FIXTURES / "effects" / "minimal_library_with_meteors.json"
VARIANTS_FIXTURE = FIXTURES / "variants" / "builtin_variants_minimal.json"
THEMES_FIXTURE = FIXTURES / "themes" / "minimal_themes.json"


@pytest.fixture
def app(tmp_path):
    """Flask test app with theme and variant routes wired to fixture data."""
    import src.review.variant_routes as vr
    import src.review.theme_routes as tr

    effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
    variant_lib = load_variant_library(
        builtin_path=VARIANTS_FIXTURE,
        custom_dir=tmp_path / "custom_variants",
        effect_library=effect_lib,
    )

    # Wire variant routes
    vr._library = variant_lib
    vr._effect_library = effect_lib
    vr._custom_dir = tmp_path / "custom_variants"
    vr._builtin_path = VARIANTS_FIXTURE

    # Wire theme routes
    tr._library = None  # force re-load
    tr._effect_library = effect_lib
    tr._custom_dir = tmp_path / "custom_themes"
    tr._builtin_path = THEMES_FIXTURE
    tr._builtin_names_cache = None

    # Ensure custom dirs exist
    (tmp_path / "custom_themes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "custom_variants").mkdir(parents=True, exist_ok=True)

    from src.review.server import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app

    vr._library = None
    vr._effect_library = None
    vr._custom_dir = None
    vr._builtin_path = None

    tr._library = None
    tr._effect_library = None
    tr._custom_dir = None
    tr._builtin_path = None
    tr._builtin_names_cache = None


@pytest.fixture
def client(app):
    return app.test_client()


class TestVariantPickerFetchesByEffect:
    """T004: GET /variants?effect=X returns variants for the variant picker."""

    def test_filter_by_bars_returns_bars_variant(self, client):
        data = client.get("/variants?effect=Bars").get_json()
        assert len(data["variants"]) >= 1
        assert all(v["base_effect"] == "Bars" for v in data["variants"])

    def test_filter_by_fire_returns_fire_variant(self, client):
        data = client.get("/variants?effect=Fire").get_json()
        assert len(data["variants"]) >= 1
        assert all(v["base_effect"] == "Fire" for v in data["variants"])

    def test_variant_has_tags_for_picker_display(self, client):
        data = client.get("/variants?effect=Fire").get_json()
        v = data["variants"][0]
        assert "tags" in v
        tags = v["tags"]
        assert "energy_level" in tags
        assert "tier_affinity" in tags
        assert "section_roles" in tags

    def test_variant_has_description(self, client):
        data = client.get("/variants?effect=Fire").get_json()
        v = data["variants"][0]
        assert v["description"]

    def test_no_variants_for_unknown_effect(self, client):
        data = client.get("/variants?effect=NoSuchEffect").get_json()
        assert data["variants"] == []

    def test_no_variants_for_on_effect(self, client):
        data = client.get("/variants?effect=On").get_json()
        assert data["variants"] == []


class TestSaveThemeWithVariantRef:
    """T005: Saving a theme with variant_ref preserves it."""

    def _make_theme(self, name, variant_ref=None):
        layer = {
            "effect": "Fire",
            "blend_mode": "Normal",
            "parameter_overrides": {"E_SLIDER_Fire_Height": 85},
        }
        if variant_ref is not None:
            layer["variant_ref"] = variant_ref
        return {
            "name": name,
            "mood": "aggressive",
            "occasion": "general",
            "genre": "any",
            "intent": "Test theme with variant ref",
            "palette": ["#FF4400", "#FF8800"],
            "layers": [layer],
            "variants": [],
        }

    def test_save_theme_with_variant_ref(self, client):
        theme = self._make_theme("Variant Test Theme", variant_ref="Fire Blaze High")
        resp = client.post(
            "/themes/api/save",
            json={"theme": theme},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_saved_variant_ref_appears_in_list(self, client):
        theme = self._make_theme("VRef Persist Test", variant_ref="Fire Blaze High")
        client.post("/themes/api/save", json={"theme": theme}, content_type="application/json")

        # Reload and check
        list_resp = client.get("/themes/api/list")
        themes = list_resp.get_json()["themes"]
        saved = next(t for t in themes if t["name"] == "VRef Persist Test")
        assert saved["layers"][0]["variant_ref"] == "Fire Blaze High"

    def test_save_theme_without_variant_ref(self, client):
        theme = self._make_theme("No VRef Theme")
        resp = client.post("/themes/api/save", json={"theme": theme}, content_type="application/json")
        assert resp.status_code == 200

        list_resp = client.get("/themes/api/list")
        themes = list_resp.get_json()["themes"]
        saved = next(t for t in themes if t["name"] == "No VRef Theme")
        # variant_ref should be None/null
        assert saved["layers"][0].get("variant_ref") is None

    def test_save_theme_with_missing_variant_ref_still_loads(self, client):
        """A theme with a variant_ref pointing to a nonexistent variant should still
        load successfully — the variant_ref is preserved but has no effect on validation."""
        theme = self._make_theme("Broken VRef Theme", variant_ref="No Such Variant")
        resp = client.post("/themes/api/save", json={"theme": theme}, content_type="application/json")
        # The save should succeed — missing variant_ref is a warning, not an error
        assert resp.status_code == 200

        list_resp = client.get("/themes/api/list")
        themes = list_resp.get_json()["themes"]
        saved = next(t for t in themes if t["name"] == "Broken VRef Theme")
        # The variant_ref should be preserved even though the variant doesn't exist
        assert saved["layers"][0]["variant_ref"] == "No Such Variant"

    def test_variant_ref_null_when_cleared(self, client):
        """Saving a theme with variant_ref=null should clear it."""
        # First save with a variant_ref
        theme = self._make_theme("Clear VRef Theme", variant_ref="Fire Blaze High")
        client.post("/themes/api/save", json={"theme": theme}, content_type="application/json")

        # Now save again without variant_ref
        theme2 = self._make_theme("Clear VRef Theme", variant_ref=None)
        resp = client.post(
            "/themes/api/save",
            json={"theme": theme2, "original_name": "Clear VRef Theme"},
            content_type="application/json",
        )
        assert resp.status_code == 200

        list_resp = client.get("/themes/api/list")
        themes = list_resp.get_json()["themes"]
        saved = next(t for t in themes if t["name"] == "Clear VRef Theme")
        assert saved["layers"][0].get("variant_ref") is None


class TestContextAwareScoring:
    """T012: POST /variants/query returns scored variants for context-aware picker."""

    def test_query_returns_scored_results(self, client):
        resp = client.post(
            "/variants/query",
            json={"base_effect": "Fire", "energy_level": "high"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert len(data["results"]) >= 1

    def test_query_results_sorted_by_score(self, client):
        resp = client.post(
            "/variants/query",
            json={"base_effect": "Fire", "energy_level": "high"},
            content_type="application/json",
        )
        data = resp.get_json()
        scores = [r["score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_query_results_have_breakdown(self, client):
        resp = client.post(
            "/variants/query",
            json={"base_effect": "Fire", "energy_level": "high"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert len(data["results"]) >= 1, "Expected at least one scored result"
        r = data["results"][0]
        assert "breakdown" in r
        assert isinstance(r["breakdown"], dict)

    def test_query_with_tier_affinity(self, client):
        resp = client.post(
            "/variants/query",
            json={"base_effect": "Fire", "tier_affinity": "foreground"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
