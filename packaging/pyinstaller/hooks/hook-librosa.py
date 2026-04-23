"""PyInstaller hook: librosa — collect data files and hidden imports."""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("librosa")

hiddenimports += [
    "librosa.util.exceptions",
    "scipy.sparse.csgraph._validation",
    "sklearn.utils._cython_blas",
]
