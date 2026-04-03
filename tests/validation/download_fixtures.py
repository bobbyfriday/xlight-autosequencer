"""Download CC0 music fixtures for end-to-end validation testing.

All tracks are CC0/public domain from the SoundSafari/CC0-1.0-Music
GitHub repository. No attribution required.

Usage:
    python -m tests.validation.download_fixtures
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import urlretrieve

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "cc0_music"

TRACKS = {
    "space_ambience.mp3": (
        "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/"
        "main/freepd.com/Space%20Ambience.mp3"
    ),
    "nostalgic_piano.mp3": (
        "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/"
        "main/freepd.com/Nostalgic%20Piano.mp3"
    ),
    "maple_leaf_rag.mp3": (
        "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/"
        "main/freepd.com/Maple%20Leaf%20Rag.mp3"
    ),
    "funshine.mp3": (
        "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/"
        "main/freepd.com/Funshine.mp3"
    ),
    "black_box_legendary.mp3": (
        "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/"
        "main/pixbay.com/black-box-legendary-9509.mp3"
    ),
}


def download_all(force: bool = False) -> list[Path]:
    """Download all CC0 music fixtures. Skips existing files unless force=True."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for filename, url in TRACKS.items():
        path = FIXTURES_DIR / filename
        if path.exists() and not force:
            print(f"  exists: {path.name}")
            downloaded.append(path)
            continue

        print(f"  downloading: {filename} ...", end=" ", flush=True)
        urlretrieve(url, str(path))
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"{size_mb:.1f} MB")
        downloaded.append(path)

    return downloaded


if __name__ == "__main__":
    force = "--force" in sys.argv
    print("Downloading CC0 music fixtures...")
    paths = download_all(force=force)
    print(f"\n{len(paths)} tracks ready in {FIXTURES_DIR}")
