"""POST /api/v1/import — multipart MP3/WAV upload with SHA-256 dedup (T043)."""
from __future__ import annotations

import hashlib
import io
import datetime
import tempfile
import os
from pathlib import Path

from flask import jsonify, request

from . import api_v1
from src.review.storage.library import load_library, save_library

_ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".aiff", ".aif"}
_MAX_BYTES = 200 * 1024 * 1024  # 200 MB


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _duration_ms(audio_bytes: bytes, ext: str) -> int:
    """Compute duration_ms from raw audio bytes using wave (WAV) or fallback."""
    if ext in (".wav",):
        import wave as _wave
        try:
            with _wave.open(io.BytesIO(audio_bytes)) as w:
                return int(w.getnframes() / w.getframerate() * 1000)
        except Exception:
            pass
    # For MP3/FLAC/AIFF use mutagen if available, else librosa
    try:
        import mutagen
        f = mutagen.File(io.BytesIO(audio_bytes))
        if f is not None and f.info:
            return int(f.info.length * 1000)
    except Exception:
        pass
    try:
        import soundfile as sf
        data, sr = sf.read(io.BytesIO(audio_bytes))
        return int(len(data) / sr * 1000)
    except Exception:
        pass
    return 0


def _read_id3(audio_bytes: bytes) -> tuple[str | None, str | None]:
    """Return (title, artist) from ID3 tags, or (None, None)."""
    try:
        import mutagen
        f = mutagen.File(io.BytesIO(audio_bytes), easy=True)
        if f is None:
            return None, None
        title = (f.get("title") or [None])[0]
        artist = (f.get("artist") or [None])[0]
        return title, artist
    except Exception:
        return None, None


@api_v1.route("/import", methods=["POST"])
def import_song():
    # Validate file present
    if "audio" not in request.files:
        return jsonify({"error": {"code": "missing_file", "message": "No audio file provided"}}), 400

    f = request.files["audio"]
    filename = f.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in _ALLOWED_EXTENSIONS:
        return jsonify({"error": {"code": "unsupported_format",
                                   "message": f"Unsupported file type: {ext}"}}), 400

    audio_bytes = f.read()
    if len(audio_bytes) > _MAX_BYTES:
        return jsonify({"error": {"code": "audio_too_large",
                                   "message": "File exceeds 200 MB limit"}}), 413

    # Compute content hash — first 16 hex chars of SHA-256
    song_id = hashlib.sha256(audio_bytes).hexdigest()[:16]

    source_path = request.form.get("source_path") or None
    folder_id = request.form.get("folder_id") or "unfiled"

    # Always persist the audio bytes into the state directory so the pipeline
    # has a stable path regardless of where the user's original file lives.
    from src.review.storage.paths import library_root
    audio_dir = library_root() / "songs" / song_id / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    stored_audio_path = audio_dir / filename
    if not stored_audio_path.exists():
        tmp_path = stored_audio_path.with_suffix(".tmp")
        tmp_path.write_bytes(audio_bytes)
        os.replace(str(tmp_path), str(stored_audio_path))

    # stored_audio_path is always the canonical source path
    canonical_path = str(stored_audio_path)

    lib = load_library()

    # Check for existing song with same song_id
    existing = next((s for s in lib["songs"] if s["song_id"] == song_id), None)

    if existing is not None:
        # Ensure the canonical path is recorded
        if canonical_path not in existing["source_paths"]:
            existing["source_paths"].insert(0, canonical_path)
        # Also record the original source path if provided
        if source_path and source_path not in existing["source_paths"]:
            existing["source_paths"].append(source_path)
        save_library(lib)
        return jsonify({"created": False, "source_path_added": True, "song": existing}), 200

    # Compute duration
    duration_ms = _duration_ms(audio_bytes, ext)

    # Read ID3 tags
    id3_title, id3_artist = _read_id3(audio_bytes)

    title = id3_title or Path(filename).stem
    artist = id3_artist or None

    # canonical stored path first, original source path second (if different)
    source_paths = [canonical_path]
    if source_path and source_path != canonical_path:
        source_paths.append(source_path)

    song = {
        "song_id": song_id,
        "title": title,
        "artist": artist,
        "duration_ms": duration_ms,
        "bpm": None,
        "key": None,
        "time_signature": None,
        "status": "draft",
        "source_paths": source_paths,
        "folder_id": folder_id,
        "imported_at": _now_iso(),
        "last_opened_at": None,
    }

    lib["songs"].append(song)
    save_library(lib)

    return jsonify({"created": True, "song": song}), 201
