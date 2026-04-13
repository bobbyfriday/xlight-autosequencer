# CLI Contract: Sequence Generator Commands

**Date**: 2026-03-26

## New CLI Commands

### `xlight-analyze generate`

Generate a complete xLights sequence from an MP3 and layout file.

```
xlight-analyze generate <audio.mp3> <layout.xml> [OPTIONS]
```

**Arguments**:
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `audio` | PATH | Yes | Path to MP3 file |
| `layout` | PATH | Yes | Path to xLights `xlights_rgbeffects.xml` |

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output-dir` | PATH | Same as audio file | Directory for .xsq output |
| `--genre` | STRING | Auto-detect | Song genre (rock, pop, classical, etc.) |
| `--occasion` | STRING | "general" | "christmas", "halloween", or "general" |
| `--fresh` | FLAG | false | Force re-analysis (skip cache) |
| `--no-wizard` | FLAG | false | Skip interactive wizard, use defaults/flags |
| `--section` | STRING | None | Regenerate only this section type (e.g., "chorus") |
| `--theme-override` | STRING | None | Override theme for a section: "chorus=Inferno" (repeatable) |

**Output**:
- `<song_name>.xsq` in output directory
- Summary printed to stdout with section-theme mappings
- FSEQ rendering instructions printed at end

**Exit Codes**:
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid input, missing layout, analysis failure) |
| 130 | User cancelled wizard |

---

### `xlight-analyze generate-wizard`

Interactive wizard for sequence generation (same as `generate` without `--no-wizard`).

```
xlight-analyze generate-wizard [audio.mp3]
```

If audio path omitted, wizard prompts for it. Walks through:
1. Audio file selection
2. Layout file selection
3. Song metadata confirmation (title, artist, genre, occasion)
4. Generation plan preview (section→theme table)
5. Theme override prompts
6. Generation confirmation

---

## Modified Commands

### `xlight-analyze wizard` (existing)

No changes. The existing wizard handles analysis configuration. The new `generate-wizard` is a separate command for sequence generation.
