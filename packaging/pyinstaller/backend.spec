# PyInstaller spec for the XLight backend sidecar.
#
# Builds a macOS onedir executable consumed by Tauri as an externalBin
# sidecar. The executable must be renamed to `backend-<arch>-apple-darwin`
# by `packaging/scripts/build-backend.sh` before Tauri will accept it.
#
# Targets one arch at a time (pass --target-arch to pyinstaller CLI).

# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

REPO_ROOT = Path(SPECPATH).resolve().parent.parent  # packaging/pyinstaller/ -> repo root

# ── Collect heavy native stacks ─────────────────────────────────────────
# collect_all returns (datas, binaries, hiddenimports). We aggregate.
datas = []
binaries = []
hiddenimports = []

for pkg in ["madmom", "librosa", "soundfile", "demucs"]:
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        # Optional deps: skip if not installed on this build machine.
        continue
    datas += d
    binaries += b
    hiddenimports += h

# Torch is CPU-only for this build. `collect_all("torch")` pulls a large
# tree; we accept that cost to avoid hunting dynamic imports.
try:
    d, b, h = collect_all("torch")
    datas += d
    binaries += b
    hiddenimports += [m for m in h if "cuda" not in m.lower()]
except Exception:
    pass

# ── Application data — builtin JSON catalogs ────────────────────────────
datas += [
    (str(REPO_ROOT / "src/effects/builtin_effects.json"), "src/effects"),
    (str(REPO_ROOT / "src/themes/builtin_themes.json"), "src/themes"),
]
# Variant builtins folder (feature 033)
variants_root = REPO_ROOT / "src/variants/builtins"
if variants_root.is_dir():
    datas += [(str(p), str(p.parent.relative_to(REPO_ROOT))) for p in variants_root.glob("*.json")]

# ── Hidden imports known to be missed by auto-detection ─────────────────
hiddenimports += [
    "madmom.ml.nn.layers",
    "madmom.audio.comb_filters",
    "librosa.util.exceptions",
    "scipy.sparse.csgraph._validation",
    "sklearn.utils._cython_blas",
    "demucs.pretrained",
    "demucs.apply",
    "torch._C",
    "torch.jit",
    "pkg_resources.py2_warn",
]


a = Analysis(
    [str(REPO_ROOT / "src/review/bundled_entrypoint.py")],
    pathex=[str(REPO_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(REPO_ROOT / "packaging/pyinstaller/hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Keep the bundle lean — we don't use any GUI toolkit.
        "tkinter",
        "matplotlib",
        # Torch CUDA / ROCm subpackages.
        "torch.cuda",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="backend",  # renamed to backend-<arch>-apple-darwin by build script
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX breaks codesigning
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # set via pyinstaller --target-arch flag
    codesign_identity=None,  # signing done post-build by sign-backend.sh
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="backend",
)
