"""Tests for layout endpoints — T052."""
from __future__ import annotations

import io
import pytest


_VALID_XLIGHTS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<xlights_rgbeffects>
  <model name="Arch 1" DisplayAs="Arch" parm1="50" parm2="1"
         WorldPosX="0" WorldPosY="0" WorldPosZ="0"
         ScaleX="1" ScaleY="1" />
  <model name="Tree 1" DisplayAs="Tree 360" parm1="100" parm2="16"
         WorldPosX="5" WorldPosY="0" WorldPosZ="0"
         ScaleX="1" ScaleY="1" />
</xlights_rgbeffects>
"""

_INVALID_XML = b"this is not xml <<<"
_NO_MODELS_XML = b"""<?xml version="1.0"?><xlights_rgbeffects></xlights_rgbeffects>"""


class TestGetLayout:
    def test_returns_200_no_layout(self, client):
        resp = client.get("/api/v1/layout")
        assert resp.status_code == 200

    def test_no_layout_returns_null(self, client):
        data = client.get("/api/v1/layout").get_json()
        assert data.get("layout") is None or data.get("layout_id") is None


class TestPostLayout:
    def test_valid_xml_returns_201(self, client):
        resp = client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_VALID_XLIGHTS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201

    def test_layout_fields_present(self, client):
        data = client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_VALID_XLIGHTS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        ).get_json()
        layout = data["layout"]
        assert "layout_id" in layout
        assert "display_name" in layout
        assert "imported_at" in layout
        assert "props" in layout
        assert "total_pixels" in layout

    def test_props_extracted(self, client):
        data = client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_VALID_XLIGHTS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        ).get_json()
        assert len(data["layout"]["props"]) == 2

    def test_replaced_prior_true_on_second_import(self, client):
        client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_VALID_XLIGHTS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        )
        data = client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_VALID_XLIGHTS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        ).get_json()
        assert data["replaced_prior"] is True

    def test_replaced_prior_false_on_first_import(self, client):
        data = client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_VALID_XLIGHTS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        ).get_json()
        assert data["replaced_prior"] is False

    def test_invalid_xml_returns_400(self, client):
        resp = client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_INVALID_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "invalid_xml"

    def test_no_props_returns_400(self, client):
        resp = client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_NO_MODELS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "no_props_found"

    def test_get_layout_after_import(self, client):
        client.post(
            "/api/v1/layout",
            data={"layout_xml": (io.BytesIO(_VALID_XLIGHTS_XML), "xlights_rgbeffects.xml")},
            content_type="multipart/form-data",
        )
        data = client.get("/api/v1/layout").get_json()
        assert data.get("layout_id") is not None or data.get("layout", {}) is not None
