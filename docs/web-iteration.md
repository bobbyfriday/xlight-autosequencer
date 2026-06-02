# Iterating in Claude Code on the Web

A fresh web session starts in a **bare** container: no Python deps, no ffmpeg,
no frontend build. This page describes the automated bootstrap that fixes that,
the gotchas it works around, and the generator iteration loops you can run.

## Automatic light bootstrap (SessionStart hook)

`.claude/hooks/session-start.sh` runs on every web session (registered in
`.claude/settings.json`). It installs the **light stack** so the test suite,
the CLI, and the fast generator/microscope loop work immediately:

- `ffmpeg` (MP3 loading)
- the package + `[dev,ui-tests]` extras (`pip install -e ".[dev,ui-tests]"`)
- the React frontend bundle (`npm install && npm run build`)

The hook is **synchronous** (the session waits for it) and always exits 0 — a
partial environment is reported, never fatal. Logs land in
`/tmp/session-start-{apt,pip,npm}.log`. It runs only when `CLAUDE_CODE_REMOTE=true`;
local dev uses `scripts/install.sh`.

> Changing the hook to async (faster startup, but tests may run before deps
> finish installing) is a one-line edit — emit `{"async": true, "asyncTimeout": 300000}`
> as the first stdout line.

### Three gotchas the hook works around

1. **`blinker` blocks pip.** Debian ships `blinker` with no `RECORD` file, so
   `pip install -e .` aborts trying to uninstall it. Fix:
   `pip install --ignore-installed blinker` first.
2. **`apt-get update` is blocked.** Two third-party PPAs (deadsnakes,
   ondrej/php) 403 under the network policy. `apt-get install -y ffmpeg`
   *without* `update` works off cached lists; the fallback drops those PPA
   `.list` files then updates.
3. **`pytest` is shadowed.** A uv-isolated `/root/.local/bin/pytest` (no
   project deps) wins on PATH. **Always run `python3 -m pytest`**, never bare
   `pytest`.

## Running the test flows

The CI "cheap tier" (unit + integration, no browser/heavy analyzer):

```bash
python3 -m pytest tests/ -m "not ui and not content and not slow and not capture_only" \
  --ignore=tests/integration/test_themes_integration.py \
  --ignore=tests/unit/test_genius_segments.py \
  --ignore=tests/unit/test_librosa_hpss.py \
  --ignore=tests/unit/test_repetition_policy.py \
  --ignore=tests/unit/test_section_profiler.py \
  --ignore=tests/unit/test_stem_inspector.py \
  --ignore=tests/validation/test_scenarios.py
```

Expect ~2800 passing in ~100s. Known non-issues on a **root** web container:
`test_stems_paths::...unwritable` fails because root bypasses `chmod`, so the
read-only-dir fallback never triggers — it is not a real regression.

## Fast generator iteration loop (no xLights, no vamp)

The generator places effects **per section**. With no vamp/madmom, analysis
finds no sections and the generator emits an **unlit** sequence. Supply a
committed `*_story.json` to drive placement on the light stack:

```python
from tools.render_panel.run import _generate, _count_model_placements
xsq = _generate(
    song="tests/fixtures/cc0_music/maple_leaf_rag.mp3",
    layout="tests/fixtures/render_panel/xlights_rgbeffects.xml",
    story="tests/fixtures/render_panel/maple_leaf_rag_story.json",
    out_dir="/tmp/gen", variation_seed=42,
)
print(_count_model_placements(xsq))   # 43 -> lit
```

The **microscope** measures visual-quality metrics over a generated XSQ (pure
Python, no xLights):

```bash
xlight-evaluate microscope run tests/fixtures/cc0_music/maple_leaf_rag.mp3 \
  --layout tests/fixtures/reference/layout.xml
# writes microscope-out/microscope/<slug>/metrics.json
```

Note: `microscope run` does its own analysis, so without the analyzer sidecar
its placement metrics read `0 / no_placements`. For lit metrics, install the
analyzer stack (below) or measure a story-fed XSQ.

## Visual render loop (heavy, on demand)

Generate → headless xLights → MP4 → contact sheet. Pulls Xvfb + a software-GL
stack + the xLights AppImage (~98 MB):

```bash
scripts/setup-heavy.sh render
python3 -m tools.render_panel.run panel \
  --manifest tests/fixtures/render_panel/manifest.json
# -> render-out/panel_contact_sheet.jpg
```

## Full analyzer sidecar (heavy, on demand)

Real section detection (vamp plugins + madmom + demucs in `.venv-vamp`), so the
generator produces lit sequences straight from a bare MP3:

```bash
scripts/setup-heavy.sh analyzer    # delegates to scripts/install.sh
```
