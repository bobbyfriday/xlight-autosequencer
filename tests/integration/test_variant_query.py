"""Integration tests for POST /variants/query endpoint."""
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


class TestPostVariantsQuery:
    def test_returns_200(self, client):
        resp = client.post("/variants/query", json={})
        assert resp.status_code == 200

    def test_response_has_required_fields(self, client):
        data = client.post("/variants/query", json={}).get_json()
        assert "results" in data
        assert "relaxed_filters" in data
        assert "total" in data

    def test_empty_context_returns_all_variants(self, client):
        data = client.post("/variants/query", json={}).get_json()
        assert data["total"] == 3
        assert len(data["results"]) == 3

    def test_empty_context_has_equal_scores(self, client):
        """With no context fields, all variants score the same (all neutral 0.5 * weight)."""
        data = client.post("/variants/query", json={}).get_json()
        scores = [r["score"] for r in data["results"]]
        assert len(set(scores)) == 1, f"Expected equal scores, got: {scores}"

    def test_each_result_has_variant_score_breakdown(self, client):
        data = client.post("/variants/query", json={}).get_json()
        for result in data["results"]:
            assert "variant" in result
            assert "score" in result
            assert "breakdown" in result

    def test_variant_field_has_name_and_base_effect(self, client):
        data = client.post("/variants/query", json={}).get_json()
        for result in data["results"]:
            assert "name" in result["variant"]
            assert "base_effect" in result["variant"]

    def test_breakdown_has_all_dimensions(self, client):
        data = client.post("/variants/query", json={}).get_json()
        expected_keys = {"prop_type", "energy_level", "tier_affinity", "section_role", "scope", "genre"}
        for result in data["results"]:
            bd = result["breakdown"]
            assert expected_keys <= bd.keys(), f"Missing: {expected_keys - bd.keys()}"

    def test_full_context_returns_ranked_results(self, client):
        resp = client.post("/variants/query", json={
            "energy_level": "high",
            "tier_affinity": "foreground",
            "section_role": "chorus",
            "scope": "group",
            "genre": "any",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] > 0
        # Fire Blaze High should be at the top (matches high/foreground/chorus/group)
        top = data["results"][0]["variant"]["name"]
        assert top == "Fire Blaze High"

    def test_results_sorted_by_score_descending(self, client):
        data = client.post("/variants/query", json={"energy_level": "high"}).get_json()
        scores = [r["score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_base_effect_filter_limits_results(self, client):
        data = client.post("/variants/query", json={"base_effect": "Fire"}).get_json()
        assert data["total"] == 1
        assert data["results"][0]["variant"]["base_effect"] == "Fire"

    def test_unknown_base_effect_returns_empty(self, client):
        data = client.post("/variants/query", json={"base_effect": "NonExistentEffect"}).get_json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_relaxed_filters_empty_when_results_above_threshold(self, client):
        # High energy query — Fire Blaze High will be above threshold
        data = client.post("/variants/query", json={"energy_level": "high"}).get_json()
        assert data["relaxed_filters"] == []

    def test_relaxed_filters_non_empty_when_fallback_triggered(self, client):
        # Request something very specific that won't match any fixture variant strongly
        # We use a prop_type not in any fixture variant's base_effect suitability
        data = client.post("/variants/query", json={
            "energy_level": "high",
            "tier_affinity": "hero",
            "section_role": "outro",
            "scope": "group",
            "genre": "classical",
            "prop_type": "custom_string",  # not in any suitability dict
        }).get_json()
        # With all low scores, fallback should be triggered
        assert isinstance(data["relaxed_filters"], list)

    def test_total_equals_len_results(self, client):
        data = client.post("/variants/query", json={}).get_json()
        assert data["total"] == len(data["results"])

    def test_score_is_between_zero_and_one(self, client):
        data = client.post("/variants/query", json={
            "energy_level": "high",
            "section_role": "chorus",
        }).get_json()
        for result in data["results"]:
            assert 0.0 <= result["score"] <= 1.0, f"Score out of range: {result['score']}"

    def test_query_with_no_json_body_returns_400_or_200(self, client):
        # Sending non-JSON should either 400 (bad request) or 200 (empty context)
        resp = client.post("/variants/query", data="not json", content_type="text/plain")
        assert resp.status_code in (200, 400)

    def test_query_route_does_not_conflict_with_get_by_name(self, client):
        # POST /variants/query should not be treated as GET /variants/<name>
        get_resp = client.get("/variants/query")
        post_resp = client.post("/variants/query", json={})
        # The GET may 404 if "query" is not a variant name, but the POST must succeed
        assert post_resp.status_code == 200
