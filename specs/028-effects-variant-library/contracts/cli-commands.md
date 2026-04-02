# CLI Contracts: Effects Variant Library

**Feature**: 028-effects-variant-library
**Date**: 2026-04-01

## Commands

All commands are subcommands of the existing `xlight-analyze` CLI group.

---

### `variant list`

List all variants, optionally filtered.

```
xlight-analyze variant list [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--effect` | string | all | Filter by base effect name |
| `--energy` | choice | all | Filter: low, medium, high |
| `--tier` | choice | all | Filter: background, mid, foreground, hero |
| `--section` | string | all | Filter by section role (verse, chorus, etc.) |
| `--prop` | choice | all | Filter by prop type suitability (matrix, arch, etc.) |
| `--scope` | choice | all | Filter: single-prop, group |
| `--format` | choice | table | Output: table, json |

**Output**: Table with columns: Name, Base Effect, Energy, Tier, Speed, Direction, Scope, Description (truncated)

---

### `variant show <name>`

Show full details of a single variant.

```
xlight-analyze variant show <name>
```

| Argument | Type | Description |
|----------|------|-------------|
| `name` | string | Variant name (case-insensitive) |

**Output**: Full variant detail including all parameters, tags, and inherited base effect info.

---

### `variant create`

Create a new custom variant interactively or from a JSON file.

```
xlight-analyze variant create [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--from-file` | path | — | Create from a JSON file instead of interactive prompts |
| `--effect` | string | — | Base effect name (interactive if omitted) |
| `--name` | string | — | Variant name (interactive if omitted) |

**Output**: Confirmation with variant name and file path. Error messages if validation fails.

---

### `variant edit <name>`

Edit an existing custom variant. Opens variant JSON in editor or accepts a replacement file.

```
xlight-analyze variant edit <name> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--from-file` | path | Replace variant with contents of JSON file |

**Output**: Confirmation of update. Error if variant is built-in (read-only).

---

### `variant delete <name>`

Delete a custom variant.

```
xlight-analyze variant delete <name>
```

**Output**: Confirmation of deletion. Error if variant is built-in (read-only).

---

### `variant import <xsq-path>`

Extract effect variants from an .xsq sequence file.

```
xlight-analyze variant import <xsq-path> [OPTIONS]
```

| Argument/Option | Type | Description |
|-----------------|------|-------------|
| `xsq-path` | path | Path to .xsq file |
| `--dry-run` | flag | Show what would be imported without saving |
| `--auto-name` | flag | Auto-generate names without prompting |
| `--skip-duplicates` | flag | Silently skip duplicate variants |

**Output**: Per-variant status (imported/skipped/duplicate). Summary count at end.

---

### `variant coverage`

Show which base effects have variants and identify gaps.

```
xlight-analyze variant coverage [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | choice | table | Output: table, json |

**Output**: Table with columns: Effect Name, Category, Variant Count, Prop Coverage (how many prop types have at least one suitable variant), Tag Coverage (% of variants with complete tags).
