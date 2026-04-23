"""PyInstaller hook: madmom.

Auto-detection misses the nn.layers and comb_filters C extensions, plus
the shipped model data files.
"""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("madmom")

hiddenimports += [
    "madmom.ml.nn.layers",
    "madmom.audio.comb_filters",
    "madmom.features.beats",
    "madmom.features.downbeats",
    "madmom.features.onsets",
]
