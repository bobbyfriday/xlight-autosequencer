"""PyInstaller hook: demucs — ensure pretrained registry is reachable."""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("demucs")

hiddenimports += [
    "demucs.pretrained",
    "demucs.apply",
    "demucs.htdemucs",
    "demucs.hdemucs",
]
