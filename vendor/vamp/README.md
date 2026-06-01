# Vendored Vamp plugins

Prebuilt, **self-contained** Vamp plugin binaries committed to the repo so that
real Vamp analysis works in ephemeral containers (Claude Code web sessions, CI
runners) without a compile step or a network download.

The canonical build-from-source recipe lives in `.devcontainer/Dockerfile`
(the "Build Vamp plugins from source" block). These vendored binaries are the
output of that same recipe, captured here so a fresh container that does *not*
run the Dockerfile (e.g. the web execution environment) still gets working
plugins by pointing `VAMP_PATH` at the directory for its platform.

## Layout

```
vendor/vamp/<platform>/<plugin>.{so,cat,n3}
```

| platform        | target                                  |
|-----------------|-----------------------------------------|
| `linux-x86_64`  | Linux glibc, x86-64                      |

## What's vendored

| plugin        | provides                                   | used by                                  |
|---------------|--------------------------------------------|------------------------------------------|
| `segmentino`  | L1 song structure (repetition labels A/B/C)| `src/analyzer/orchestrator.py`, `src/story/` |
| `nnls-chroma` | `chordino` chords + `nnls-chroma` chroma   | `src/analyzer/algorithms/vamp_harmony.py`|

Both `.so` files are linked to be self-contained — `ldd` shows only
`libstdc++`/`libm`/`libgcc_s`/`libc`. The Vamp SDK is linked statically
(`libvamp-sdk.a`) and armadillo is header-only, so no apt packages are
required at runtime.

This is a partial set. The full required panel (see `scripts/start.sh`) also
includes `qm-vamp-plugins`, `bbc-vamp-plugins`, `beatroot-vamp`, `pyin`, and
`vamp-aubio`; add them here using the recipe below as they are built.

## Activating

`src/analyzer/capabilities.py` discovers plugins via `VAMP_PATH` and the
standard system dirs. To use the vendored set in a session:

```bash
export VAMP_PATH="$PWD/vendor/vamp/linux-x86_64"
```

`scripts/install.sh` copies the vendored binaries for the current platform
into `$VAMP_DIR` automatically (offline fast path) before attempting any
network download.

## Rebuild recipe (linux-x86_64)

System packages: `build-essential`, `libboost-dev` (build-time only, for
nnls-chroma's `<boost/tokenizer.hpp>`), `vamp-plugin-sdk` (headers + static
lib at `/usr/lib/x86_64-linux-gnu/libvamp-sdk.a`).

```bash
# nnls-chroma (chordino + chroma) — static SDK link → self-contained
git clone --depth 1 https://github.com/c4dm/nnls-chroma && cd nnls-chroma
make -f Makefile.linux VAMP_SDK_DIR=/usr/include \
  CXXFLAGS="-O3 -ffast-math -I/usr/include -fPIC" \
  LDFLAGS="-shared -Wl,-soname=nnls-chroma.so \
           /usr/lib/x86_64-linux-gnu/libvamp-sdk.a \
           -Wl,--version-script=vamp-plugin.map"

# segmentino (L1 sections) — bundles armadillo (vendored in its repo) + qm-dsp
git clone --depth 1 https://github.com/c4dm/segmentino && cd segmentino
git clone --depth 1 https://github.com/c4dm/qm-dsp
git clone --depth 1 https://github.com/c4dm/vamp-plugin-sdk
git clone --depth 1 https://github.com/c4dm/nnls-chroma
touch .repoint.point   # deps placed manually; skip the repoint fetch step
make -f Makefile.linux
```

Verify with the project's own detector:

```bash
VAMP_PATH="$PWD/vendor/vamp/linux-x86_64" .venv-vamp/bin/python -c \
  "import vamp; print(vamp.list_plugins())"
```
