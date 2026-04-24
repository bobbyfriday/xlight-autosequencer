"""Download CC0 music fixtures for end-to-end validation testing.

All tracks are CC0 from FreePD via the SoundSafari/CC0-1.0-Music GitHub repo.
No attribution required.

After download, each MP3's SHA-256 is verified against the expected hash in
`tests/fixtures/cc0_music/manifest.json`. A mismatch means the source URL was
silently replaced upstream; the file is deleted and the script exits with code 8
(infrastructure failure) so a drifted MP3 cannot shift the acceptance-gate
baseline invisibly.

Usage:
    python -m tests.validation.download_fixtures             # download + verify
    python -m tests.validation.download_fixtures --force     # re-download all
    python -m tests.validation.download_fixtures --update-hashes
        # deliberate rotation — re-download and rewrite manifest hashes

Exit codes:
    0  all tracks present and hashes match (or --update-hashes succeeded)
    8  infrastructure failure — network error after retries, or hash mismatch
"""
from __future__ import annotations

import hashlib
import json
import socket
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "cc0_music"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"

DOWNLOAD_TIMEOUT_SEC = 30
RETRY_DELAYS_SEC = (2, 4, 8)  # three attempts total: first immediate, then these
EXIT_INFRA_FAILURE = 8


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found at {MANIFEST_PATH}. Run with --update-hashes to create it."
        )
    return json.loads(MANIFEST_PATH.read_text())


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_with_retry(url: str, dest: Path) -> None:
    socket.setdefaulttimeout(DOWNLOAD_TIMEOUT_SEC)
    last_err: Exception | None = None
    attempts = [0, *RETRY_DELAYS_SEC]  # 0s, 2s, 4s, 8s = 4 attempts total
    for attempt, delay in enumerate(attempts):
        if delay:
            time.sleep(delay)
        try:
            urlretrieve(url, str(dest))
            return
        except (URLError, TimeoutError, socket.timeout) as err:
            last_err = err
            print(f"    attempt {attempt + 1} failed: {err}", flush=True)
    raise RuntimeError(f"download failed after {len(attempts)} attempts: {last_err}") from last_err


def download_all(*, force: bool = False, update_hashes: bool = False) -> list[Path]:
    """Download all CC0 fixtures; verify hashes; return local paths.

    - force: re-download even if file exists.
    - update_hashes: after download, write computed hashes back to manifest
      (deliberate rotation path). Skips hash verification.
    """
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    if update_hashes and not MANIFEST_PATH.exists():
        # Bootstrap: manifest must at least list the tracks to download.
        raise FileNotFoundError(
            f"Cannot --update-hashes without a manifest at {MANIFEST_PATH}. "
            "Create the manifest with track URLs first (hashes can be placeholders)."
        )

    manifest = _load_manifest()
    tracks = manifest["tracks"]
    downloaded: list[Path] = []

    for track in tracks:
        filename = track["filename"]
        url = track["source_url"]
        expected_sha = track.get("sha256", "")
        path = FIXTURES_DIR / filename

        if path.exists() and not force and not update_hashes:
            if expected_sha and _sha256(path) != expected_sha:
                print(f"  MISMATCH (cached): {filename}")
                path.unlink()
            else:
                print(f"  exists: {filename}")
                downloaded.append(path)
                continue

        print(f"  downloading: {filename} ...", flush=True)
        _download_with_retry(url, path)
        size_mb = path.stat().st_size / (1024 * 1024)
        actual_sha = _sha256(path)

        if update_hashes:
            track["sha256"] = actual_sha
            print(f"    {size_mb:.1f} MB  sha256={actual_sha[:16]}… (updated)")
        elif expected_sha and actual_sha != expected_sha:
            path.unlink()
            raise RuntimeError(
                f"sha256 mismatch for {filename}\n"
                f"  expected: {expected_sha}\n"
                f"  observed: {actual_sha}\n"
                f"Source URL may have been replaced. Investigate before running the gate."
            )
        else:
            print(f"    {size_mb:.1f} MB  sha256 OK")

        downloaded.append(path)

    if update_hashes:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"\nManifest hashes updated: {MANIFEST_PATH}")

    return downloaded


if __name__ == "__main__":
    force = "--force" in sys.argv
    update_hashes = "--update-hashes" in sys.argv
    mode = "update-hashes" if update_hashes else ("force" if force else "verify")
    print(f"Downloading CC0 music fixtures (mode: {mode})...")
    try:
        paths = download_all(force=force, update_hashes=update_hashes)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(EXIT_INFRA_FAILURE)
    print(f"\n{len(paths)} tracks ready in {FIXTURES_DIR}")
