import io
import json
import zipfile
from typing import Any

BUNDLE_SCHEMA_VERSION = 1


class BundleInvalidError(Exception):
    pass


class BundleSchemaVersionError(Exception):
    pass


def pack(
    library: dict[str, Any],
    sessions: dict[str, dict[str, Any]],
) -> bytes:
    """Serialize library + sessions into a .xonset-bundle zip (bytes)."""
    library_out = {"bundle_schema_version": BUNDLE_SCHEMA_VERSION, **library}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("library.json", json.dumps(library_out, indent=2))
        for song_id, session in sessions.items():
            zf.writestr(f"songs/{song_id}/session.json", json.dumps(session, indent=2))
    return buf.getvalue()


def unpack(data: bytes) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Deserialize a .xonset-bundle zip. Returns (library, {song_id: session})."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise BundleInvalidError("Not a valid zip file") from exc

    with zf:
        names = set(zf.namelist())
        if "library.json" not in names:
            raise BundleInvalidError("library.json missing from bundle")

        library: dict[str, Any] = json.loads(zf.read("library.json"))
        sessions: dict[str, dict[str, Any]] = {}
        for name in names:
            if name.startswith("songs/") and name.endswith("/session.json"):
                song_id = name.split("/")[1]
                sessions[song_id] = json.loads(zf.read(name))

    return library, sessions


def check_schema_version(data: bytes) -> None:
    """Raise BundleSchemaVersionError if bundle was made by a newer app version."""
    library, _ = unpack(data)
    version = library.get("bundle_schema_version", 1)
    if version > BUNDLE_SCHEMA_VERSION:
        raise BundleSchemaVersionError(
            f"Bundle schema version {version} > supported {BUNDLE_SCHEMA_VERSION}"
        )
