"""GET /api/v1/manifest — package build metadata.

In bundled mode, returns the contents of the Contents/Resources/
packaging-manifest.json shipped with the .app. In dev mode, returns a
stub indicating dev build.
"""
from __future__ import annotations

from flask import jsonify

from src.packaging.bundled_mode import get_manifest, is_bundled
from src.review.api.v1 import api_v1


@api_v1.get("/manifest")
def manifest():
    m = get_manifest()
    if m is not None:
        return jsonify(m)
    # Dev stub — frontend still uses this to render the About dialog.
    return jsonify({
        "app_version": "dev",
        "build_timestamp": None,
        "target_arch": None,
        "frontend_commit": None,
        "backend_commit": None,
        "bundled_vamp_plugins": [],
        "download_model_manifest_url": None,
        "is_bundled": is_bundled(),
    })
