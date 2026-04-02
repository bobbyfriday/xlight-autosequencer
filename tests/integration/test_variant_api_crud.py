"""Integration tests for variant CRUD API: POST, PUT, DELETE /variants."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.effects.library import load_effect_library
from src.variants.library import load_variant_library

FIXTURES = Path(__file__).parent.parent / "fixtures"
EFFECTS_FIXTURE = FIXTURES / "effects" / "minimal_library_with_meteors.json"
VARIANTS_FIXTURE = FIXTURES / "variants" / "builtin_variants_minimal.json"

_VALID_VARIANT = {
    "name": "My Variant",
    "base_effect": "Fire",
    "description": "integration test variant",
    "parameter_overrides": {"E_SLIDER_Fire_Height": 60},
    "tags": {
        "tier_affinity": "mid",
        "energy_level": "medium",
        "speed_feel": "moderate",
        "direction": None,
        "section_roles": [],
        "scope": "group",
        "genre_affinity": "any",
    },
}


@pytest.fixture
def app(tmp_path):
    import src.review.variant_routes as vr

    effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
    lib = load_variant_library(
        builtin_path=VARIANTS_FIXTURE,
        custom_dir=tmp_path,
        effect_library=effect_lib,
    )

    # Add a custom variant for edit/delete tests
    custom_variant_data = {
        "name": "My Variant",
        "base_effect": "Fire",
        "description": "test",
        "parameter_overrides": {},
        "tags": {},
    }
    (tmp_path / "my_variant.json").write_text(
        json.dumps(custom_variant_data), encoding="utf-8"
    )
    # Reload the library to include it
    lib = load_variant_library(
        builtin_path=VARIANTS_FIXTURE,
        custom_dir=tmp_path,
        effect_library=effect_lib,
    )

    vr._library = lib
    vr._effect_library = effect_lib
    vr._custom_dir = tmp_path
    vr._builtin_path = VARIANTS_FIXTURE
    vr._builtin_names = None

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


class TestPostVariants:
    def test_create_returns_201(self, client):
        new_variant = dict(_VALID_VARIANT)
        new_variant["name"] = "Brand New Variant"
        resp = client.post(
            "/variants",
            data=json.dumps(new_variant),
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_create_returns_created_variant(self, client):
        new_variant = dict(_VALID_VARIANT)
        new_variant["name"] = "Created Variant"
        resp = client.post(
            "/variants",
            data=json.dumps(new_variant),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["name"] == "Created Variant"

    def test_create_duplicate_name_returns_409(self, client):
        # "My Variant" already exists (added in fixture)
        resp = client.post(
            "/variants",
            data=json.dumps(_VALID_VARIANT),
            content_type="application/json",
        )
        assert resp.status_code == 409
        assert "error" in resp.get_json()

    def test_create_validation_error_returns_400(self, client):
        bad_variant = {
            "name": "Bad Variant",
            "base_effect": "NonExistentEffect",
            "description": "bad",
            "parameter_overrides": {},
            "tags": {},
        }
        resp = client.post(
            "/variants",
            data=json.dumps(bad_variant),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_create_missing_required_fields_returns_400(self, client):
        resp = client.post(
            "/variants",
            data=json.dumps({"name": "Incomplete"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestPutVariants:
    def test_update_custom_returns_200(self, client):
        update = dict(_VALID_VARIANT)
        update["description"] = "updated description"
        resp = client.put(
            "/variants/My Variant",
            data=json.dumps(update),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_update_returns_updated_variant(self, client):
        update = dict(_VALID_VARIANT)
        update["description"] = "updated via PUT"
        resp = client.put(
            "/variants/My Variant",
            data=json.dumps(update),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["description"] == "updated via PUT"

    def test_update_builtin_returns_403(self, client):
        update = {
            "name": "Fire Blaze High",
            "base_effect": "Fire",
            "description": "trying to edit builtin",
            "parameter_overrides": {},
            "tags": {},
        }
        resp = client.put(
            "/variants/Fire Blaze High",
            data=json.dumps(update),
            content_type="application/json",
        )
        assert resp.status_code == 403

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put(
            "/variants/No Such Variant",
            data=json.dumps(_VALID_VARIANT),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestDeleteVariants:
    def test_delete_custom_returns_204(self, client):
        resp = client.delete("/variants/My Variant")
        assert resp.status_code == 204

    def test_delete_builtin_returns_403(self, client):
        resp = client.delete("/variants/Fire Blaze High")
        assert resp.status_code == 403

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/variants/No Such Variant")
        assert resp.status_code == 404

    def test_delete_removes_variant(self, client):
        # Verify it exists first
        assert client.get("/variants/My Variant").status_code == 200
        # Delete it
        client.delete("/variants/My Variant")
        # Now it should be gone
        resp = client.get("/variants/My Variant")
        assert resp.status_code == 404
