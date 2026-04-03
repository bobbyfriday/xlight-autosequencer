"""Analysis result cache keyed by MD5 of the source audio file."""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import contextlib
import tempfile

from src import export as export_mod
from src.analyzer.result import AnalysisResult
from src.paths import PathContext


@contextlib.contextmanager
def _file_lock(path: Path, timeout: float = 10.0):
    """Advisory file lock using a .lock sidecar file.

    Uses fcntl on Unix. Falls back to no-op if locking is unavailable.
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_fd = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(lock_path, "w")
        try:
            import fcntl
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, OSError):
            # fcntl not available (Windows) or lock contention — proceed without lock
            pass
        yield
    finally:
        if lock_fd is not None:
            try:
                import fcntl
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            lock_fd.close()
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


@dataclass
class CacheStatus:
    """Snapshot of cache state for a given audio file, used by the wizard UI."""

    exists: bool
    is_valid: bool
    age_seconds: Optional[float]
    cache_path: Optional[Path]
    track_count: int
    suggested_path: Optional[str] = None  # cross-env path suggestion when audio not found

    @classmethod
    def from_audio_path(
        cls,
        audio_path: Path,
        output_path: Optional[Path] = None,
    ) -> "CacheStatus":
        """Return a CacheStatus snapshot for *audio_path*.

        If *output_path* is omitted the default cache path is derived the same
        way as :class:`AnalysisCache` (``<audio_dir>/analysis/<stem>_analysis.json``
        or ``<audio_dir>/<stem>_analysis.json``).
        """
        if output_path is None:
            # Mirror the default output path used by analyze_cmd
            analysis_dir = audio_path.parent / "analysis"
            if analysis_dir.is_dir():
                candidate = analysis_dir / f"{audio_path.stem}_analysis.json"
            else:
                candidate = audio_path.parent / f"{audio_path.stem}_analysis.json"
            output_path = candidate

        if not audio_path.exists():
            suggestion = PathContext().suggest_path(str(audio_path))
            return cls(
                exists=False,
                is_valid=False,
                age_seconds=None,
                cache_path=None,
                track_count=0,
                suggested_path=suggestion,
            )

        if not output_path.exists():
            return cls(
                exists=False,
                is_valid=False,
                age_seconds=None,
                cache_path=None,
                track_count=0,
            )

        age = time.time() - output_path.stat().st_mtime
        cache = AnalysisCache(audio_path, output_path)
        valid = cache.is_valid()
        track_count = 0
        if valid:
            try:
                result = cache.load()
                track_count = len(result.timing_tracks)
            except (MemoryError, SystemExit, KeyboardInterrupt):
                raise
            except Exception:
                pass

        return cls(
            exists=True,
            is_valid=valid,
            age_seconds=age,
            cache_path=output_path,
            track_count=track_count,
        )


class AnalysisCache:
    """Cache wrapper around the existing _analysis.json output file.

    A cache hit requires:
    - The output JSON file exists.
    - Its ``source_hash`` field matches the MD5 hex digest of the source audio.
    """

    def __init__(self, audio_path: Path, output_path: Path) -> None:
        self._audio_path = audio_path
        self._output_path = output_path
        self._md5: str | None = None  # computed lazily and cached

    # ── Public API ────────────────────────────────────────────────────────────

    def is_valid(self) -> bool:
        """Return True if the output JSON exists and its source_hash matches the audio MD5."""
        if not self._output_path.exists():
            return False
        try:
            result = export_mod.read(str(self._output_path))
        except (MemoryError, SystemExit, KeyboardInterrupt):
            raise
        except Exception:
            return False
        if result.source_hash is None:
            return False
        return result.source_hash == self._compute_md5()

    def load(self) -> AnalysisResult:
        """Deserialise and return the cached AnalysisResult."""
        return export_mod.read(str(self._output_path))

    def save(self, result: AnalysisResult) -> None:
        """Stamp ``source_hash`` onto *result* and atomically write to the output path."""
        result.source_hash = self._compute_md5()
        with _file_lock(self._output_path):
            # Write to temp file first, then rename for atomicity
            self._output_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=str(self._output_path.parent),
                suffix=".tmp",
            )
            try:
                os.close(tmp_fd)
                export_mod.write(result, tmp_path)
                os.replace(tmp_path, str(self._output_path))
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _compute_md5(self) -> str:
        """Return the MD5 hex digest of the source audio file (computed once)."""
        if self._md5 is None:
            h = hashlib.md5()
            with open(self._audio_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            self._md5 = h.hexdigest()
        return self._md5
