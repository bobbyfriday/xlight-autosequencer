"""Failing tests for src/review/storage/bundle.py — run before T018."""
import io
import zipfile
import pytest

from src.review.storage import bundle as bundle_storage


LIBRARY = {
    "schema_version": 1,
    "songs": [
        {
            "song_id": "aabbccddeeff0011",
            "title": "Highway Star",
            "status": "themed",
        }
    ],
    "folders": [{"id": "unfiled", "name": "Unfiled"}],
    "preferences": {"mode": "dark"},
    "layout": None,
}

SESSIONS = {
    "aabbccddeeff0011": {
        "schema_version": 1,
        "sections": [{"index": 0, "start_ms": 0, "end_ms": 30000}],
        "assignments": [{"section_index": 0, "theme_id": "quiet", "overrides": {}}],
    }
}


def test_pack_produces_zip():
    data = bundle_storage.pack(LIBRARY, SESSIONS)
    assert zipfile.is_zipfile(io.BytesIO(data))


def test_pack_contains_library_json():
    data = bundle_storage.pack(LIBRARY, SESSIONS)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "library.json" in zf.namelist()


def test_pack_contains_session_json():
    data = bundle_storage.pack(LIBRARY, SESSIONS)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "songs/aabbccddeeff0011/session.json" in zf.namelist()


def test_pack_excludes_audio():
    """Audio files must NOT be bundled (FR-049c)."""
    data = bundle_storage.pack(LIBRARY, SESSIONS)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
    assert not any(n.endswith(".mp3") or n.endswith(".wav") for n in names)


def test_unpack_round_trip():
    data = bundle_storage.pack(LIBRARY, SESSIONS)
    unpacked_lib, unpacked_sessions = bundle_storage.unpack(data)
    assert unpacked_lib["songs"][0]["song_id"] == "aabbccddeeff0011"
    assert "aabbccddeeff0011" in unpacked_sessions


def test_unpack_invalid_zip_raises():
    with pytest.raises(bundle_storage.BundleInvalidError):
        bundle_storage.unpack(b"not a zip file")


def test_unpack_missing_library_json_raises():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("songs/abc/session.json", "{}")
    with pytest.raises(bundle_storage.BundleInvalidError, match="library.json"):
        bundle_storage.unpack(buf.getvalue())


def test_schema_version_mismatch_raises():
    future_lib = {**LIBRARY, "bundle_schema_version": 999}
    data = bundle_storage.pack(future_lib, SESSIONS)
    # Unpack should succeed (schema check is caller responsibility), but
    # helper should detect it when caller uses check_schema_version:
    with pytest.raises(bundle_storage.BundleSchemaVersionError):
        bundle_storage.check_schema_version(data)
