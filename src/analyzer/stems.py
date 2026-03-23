"""Stem separation: StemSet dataclass, StemSeparator, StemCache."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


# ── StemSet ───────────────────────────────────────────────────────────────────

@dataclass
class StemSet:
    """Six audio arrays from Demucs htdemucs_6s separation, held in memory."""

    drums: np.ndarray
    bass: np.ndarray
    vocals: np.ndarray
    guitar: np.ndarray
    piano: np.ndarray
    other: np.ndarray
    sample_rate: int

    def get(self, stem_name: str) -> np.ndarray | None:
        """Return the array for *stem_name*, or None if not a valid stem."""
        return getattr(self, stem_name, None)


# ── StemCache ─────────────────────────────────────────────────────────────────

_STEM_NAMES = ["drums", "bass", "vocals", "guitar", "piano", "other"]


class StemCache:
    """
    On-disk cache of WAV stems for a single source audio file.

    Cache layout (adjacent to source file by default):
        <source_dir>/.stems/<md5_hash>/drums.wav
                                       bass.wav
                                       ...
                                       manifest.json

    The MD5 hash of the source file is both the directory name and the
    cache key, so a stale cache is detected simply by recomputing the hash.
    """

    def __init__(self, source_path: Path, cache_root: Path | None = None) -> None:
        self.source_path = source_path.resolve()
        self._cache_root = cache_root or (source_path.parent / ".stems")
        self.source_hash = _md5_file(self.source_path)
        self.stem_dir = self._cache_root / self.source_hash

    def is_valid(self) -> bool:
        """Return True if the cache directory exists and the manifest is readable."""
        manifest = self.stem_dir / "manifest.json"
        if not manifest.exists():
            return False
        try:
            data = json.loads(manifest.read_text())
            return data.get("source_hash") == self.source_hash
        except Exception:
            return False

    def save(self, stem_set: StemSet) -> None:
        """Write all stems as float32 WAV files and a manifest.json."""
        import soundfile as sf

        self.stem_dir.mkdir(parents=True, exist_ok=True)
        stem_files: dict[str, str] = {}

        for name in _STEM_NAMES:
            arr = getattr(stem_set, name)
            wav_path = self.stem_dir / f"{name}.wav"
            sf.write(str(wav_path), arr, stem_set.sample_rate, subtype="FLOAT")
            stem_files[name] = f"{name}.wav"

        manifest = {
            "source_hash": self.source_hash,
            "source_path": str(self.source_path),
            "created_at": int(time.time() * 1000),
            "stems": stem_files,
        }
        (self.stem_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    def load(self) -> StemSet:
        """Load stems from WAV files and return a StemSet."""
        import librosa

        manifest = json.loads((self.stem_dir / "manifest.json").read_text())
        arrays: dict[str, np.ndarray] = {}
        sr: int = 0

        for name in _STEM_NAMES:
            wav_file = manifest["stems"][name]
            wav_path = self.stem_dir / wav_file
            arr, file_sr = librosa.load(str(wav_path), sr=None, mono=True, dtype=np.float32)
            arrays[name] = arr
            sr = int(file_sr)

        return StemSet(**arrays, sample_rate=sr)


# ── StemSeparator ─────────────────────────────────────────────────────────────

class StemSeparator:
    """
    Separates an audio file into six stems using Demucs htdemucs_6s.

    Checks the StemCache before running Demucs. On a cache hit the model
    is not loaded at all.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir  # passed through to StemCache

    def separate(self, audio_path: Path) -> StemSet:
        """
        Return a StemSet for *audio_path*.

        Checks cache first; runs Demucs if no valid cache exists; writes
        result to cache before returning.
        """
        cache = StemCache(audio_path, cache_root=self._cache_dir)

        if cache.is_valid():
            print(f"Stem separation: cache hit ({cache.source_hash[:8]})", file=sys.stderr)
            return cache.load()

        print("Stem separation: checking cache...", file=sys.stderr)
        print("  → No cache found. Separating (this may take 1-2 minutes)...", file=sys.stderr)

        stem_set = self._run_demucs(audio_path, cache.source_hash)

        cache.save(stem_set)
        print(f"  → Stems cached to {cache.stem_dir}/", file=sys.stderr)

        return stem_set

    def _run_demucs(self, audio_path: Path, source_hash: str) -> StemSet:
        """Run Demucs htdemucs_6s and return a StemSet of mono float32 arrays."""
        from demucs.api import Separator

        separator = Separator("htdemucs_6s")
        _, separated = separator.separate_audio_file(audio_path)
        sr: int = separator.samplerate

        arrays: dict[str, np.ndarray] = {}
        for name in _STEM_NAMES:
            tensor = separated[name]
            # tensor shape: (channels, samples) — collapse to mono
            mono = tensor.mean(dim=0).numpy().astype(np.float32)
            arrays[name] = mono

        return StemSet(**arrays, sample_rate=sr)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _md5_file(path: Path) -> str:
    """Return the MD5 hex digest of a file's contents."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
