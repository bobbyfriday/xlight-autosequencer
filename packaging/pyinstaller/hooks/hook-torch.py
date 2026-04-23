"""PyInstaller hook: torch (CPU-only).

Collect everything except CUDA/ROCm subpackages which we do not ship.
"""
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = collect_all("torch")

hiddenimports = [m for m in hiddenimports if "cuda" not in m.lower() and "rocm" not in m.lower()]
hiddenimports += [
    "torch._C",
    "torch.jit",
    "torch.nn.functional",
]

datas += copy_metadata("torch")
