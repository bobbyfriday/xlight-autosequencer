## ADDED Requirements

### Requirement: Panel manifest carries tier intent per fixture

Each entry in `panel_manifest.json`'s `slugs` array MAY be either a
plain string (legacy) OR an object with `slug: str` and
`tier_intent: list[str]`. The `tier_intent` list, when present, names
the tier prefixes (e.g., `"06_PROP"`, `"01_BASE"`) that the fixture is
expected to activate at least once across its sections. Manifests
SHALL be validated at panel-load time so a malformed entry is reported
before generation starts.

#### Scenario: Plain-string slug (legacy compatibility)

- **WHEN** the manifest's `slugs` array contains the string
  `"funshine"`
- **THEN** the fixture is loaded with empty `tier_intent` and the
  verify-coverage gate is a no-op for that fixture

#### Scenario: Object slug with tier_intent

- **WHEN** the manifest contains
  `{"slug": "structural-no-phrase", "tier_intent": ["06_PROP", "08_HERO"]}`
- **THEN** the panel runner generates the fixture as usual AND the
  verify-coverage gate later asserts both `06_PROP` and `08_HERO`
  appear in the resulting `tier_placement_breakdown` payload

#### Scenario: Malformed entry rejected

- **WHEN** the manifest contains an object missing the `slug` key, or
  with `tier_intent` set to a non-list value
- **THEN** the panel loader raises `ValueError` naming the offending
  entry, before any generation runs

### Requirement: verify-coverage subcommand asserts tier intent matches reality

The CLI SHALL expose `xlight-evaluate microscope verify-coverage` that
reads the panel manifest, runs the panel (or reads a previously-written
output dir), and asserts every fixture's actual tier breakdown is a
superset of its declared `tier_intent`. Exit codes:
- `0` — every fixture's tier breakdown covers its declared intent
- `6` — at least one fixture is missing a declared tier (regression)
- `2` — manifest malformed or output dir empty/incomplete

#### Scenario: All fixtures cover their intent

- **WHEN** every fixture's `tier_placement_breakdown.payload.active_tiers`
  is a superset of its declared `tier_intent`
- **THEN** the command exits 0 and prints "✓ N fixtures, M tier
  intents verified"

#### Scenario: A fixture missed a declared tier

- **WHEN** a fixture declares `tier_intent: ["06_PROP", "08_HERO"]` but
  its actual `active_tiers` is `["08_HERO"]`
- **THEN** the command exits 6 and the message names the fixture and
  the missing tier prefix(es)

#### Scenario: Output dir missing

- **WHEN** `--output-dir` is supplied but no `metrics.json` exists
  for one or more declared slugs
- **THEN** the command exits 2 with a message naming the missing
  slug(s) and suggesting `microscope panel` be run first

### Requirement: Each tier in {01_BASE, 02_GEO, 04_BEAT, 06_PROP, 08_HERO} has at least one fixture exercising it

After this proposal is implemented, the default panel manifest
SHALL contain at least one fixture whose `tier_intent` includes each
of `01_BASE`, `02_GEO`, `04_BEAT`, `06_PROP`, and `08_HERO`. Tier
`07_COMP` is explicitly out of scope (see design.md non-goals); tiers
`03_TYPE` and `05_TEX` are not partition tiers and do not need
fixture coverage at this layer.

#### Scenario: Coverage matrix audit

- **WHEN** running `xlight-evaluate microscope verify-coverage` on
  the default panel manifest
- **THEN** the union of all fixtures' `tier_intent` lists includes
  every tier prefix in the required set above

#### Scenario: A required tier has no fixture

- **WHEN** the manifest is edited to remove the only fixture
  exercising tier 6 PROP
- **THEN** verify-coverage exits non-zero with a message naming
  tier 6 as orphaned, even if all remaining fixtures pass their
  individual `tier_intent` checks
