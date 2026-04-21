import json
import os
import tempfile
from typing import Any

from .paths import song_session_path

SCHEMA_VERSION = 1


def load_session(song_id: str) -> dict[str, Any] | None:
    p = song_session_path(song_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_session(
    song_id: str,
    sections: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
) -> None:
    if len(sections) != len(assignments):
        raise ValueError(
            f"sections length ({len(sections)}) != assignments length ({len(assignments)})"
        )
    p = song_session_path(song_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(
        {"schema_version": SCHEMA_VERSION, "sections": sections, "assignments": assignments},
        indent=2,
        ensure_ascii=False,
    )
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
