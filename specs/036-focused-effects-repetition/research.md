# Research: Focused Effect Vocabulary + Embrace Repetition

## R1: How to derive WorkingSet weights from theme layers

**Decision**: Bottom-layer effect gets highest weight (0.40), each subsequent layer
gets half the previous weight. Remaining weight distributed to the layer's effect_pool
variants (if any) as accent effects.

**Rationale**: Reference analysis shows the dominant effect accounts for 30-73% of
placements. In the theme model, layer 0 (bottom) is the base/background effect that
covers the most screen time. Upper layers are overlays/accents. This natural hierarchy
maps directly to a weight curve.

**Example** (3-layer theme like "Stellar Wind"):
- Layer 0 ("Butterfly Medium Fast"): weight 0.40 → base effect "Butterfly"
- Layer 1 ("Shockwave Medium Thin"): weight 0.20 → base effect "Shockwave"
- Layer 2 ("Ripple Fast Medium"): weight 0.10 → base effect "Ripple"
- Layer 2 effect_pool ("Ripple Circle", "Spirals 3D Slow Spin"): weight 0.10 each
- Remaining 0.10: distributed to alternate layer variants

**Alternatives considered**:
- Equal weights across layers: Rejected — produces the uniform distribution we're trying
  to fix. Reference sequences show steep curves, not flat.
- Hand-curated weights per theme: Rejected — requires data entry across 21+ themes and
  falls out of sync when themes are edited.
- Energy-based dynamic weighting: Deferred to Phase 2 — adds complexity without clear
  benefit at this stage.

## R2: How to replace _PROP_EFFECT_POOL with WorkingSet

**Decision**: Tiers 6-7 (PROP, COMPOUND) draw from the same WorkingSet as other tiers
instead of the hardcoded `_PROP_EFFECT_POOL`. The WorkingSet already contains the
theme's preferred effects, which are more coherent than a static pool of 10 effects.

**Rationale**: The hardcoded pool (`Meteors, Single Strand, Ripple, Spirals, Bars,
Curtain, Shockwave, Fire, Strobe, Galaxy`) is a secondary source of over-rotation.
Reference sequences show prop groups using the same effects as the rest of the display
(SingleStrand dominates on both arches and matrices in Light of Christmas).

**Prop suitability**: The existing `prop_suitability` field on EffectDefinition already
rates effects for different prop types. The variant scorer uses this field (0.30 weight
in scoring). This natural filtering is sufficient — no separate pool needed.

**Alternatives considered**:
- Keep _PROP_EFFECT_POOL but narrow it: Rejected — two separate pools means two sources
  of visual incoherence.
- WorkingSet + prop suitability filter: This is what we're doing. The WorkingSet provides
  the vocabulary, prop_suitability scores provide the prop-appropriate ranking.

## R3: How to modify repetition penalties

**Decision**: Three changes to rotation.py:
1. **Remove intra-section dedup**: Delete the `used_in_section` tracking and the
   preference for unused variants (lines 269-275). Within a section, the same variant
   is reused on every group assignment — this is the desired behavior.
2. **Relax cross-section penalty**: Change from 0.5x to 0.85x for same-label sections.
   This still provides slight variety across repeated sections but doesn't force a
   completely different effect.
3. **Preserve transition continuity**: Keep the existing logic that forces at least one
   group to retain its variant from the previous section (lines 316-328). This creates
   smooth transitions.

**Rationale**: Reference sequences show 15-63 consecutive same effect+palette on a
single model. The current 0.3x implicit penalty and 0.5x cross-section penalty are
the primary cause of excessive variety. Removing intra-section dedup and relaxing
cross-section penalty directly addresses this.

**Alternatives considered**:
- Remove all penalties entirely: Rejected — some cross-section variation is desirable.
  Reference sequences do shift effects at section boundaries even when the "label" repeats.
- Make penalties configurable: Deferred — adds complexity. Start with the fixed values
  and tune based on analyzer output.

## R4: Beat tier (Tier 4) exclusion

**Decision**: Beat tier (Tier 4) is excluded from Phase 1 changes. Its chase pattern
(`beat N → group N mod len(groups)`) is preserved as-is.

**Rationale**: Clarified during spec session. The beat tier's chase pattern is a distinct
rhythmic feature that provides the only beat-synchronized visual element. Changing it
risks losing visual beat connection. Phase 1 focuses on tiers 1-2, 5-8 where sustained
repetition makes the biggest visual impact.

## R5: Toggle mechanism

**Decision**: Two boolean flags in the generation config:
- `focused_vocabulary: bool = True` (new default: on)
- `embrace_repetition: bool = True` (new default: on)

When disabled, each falls back to the pre-Phase-1 behavior:
- focused_vocabulary=False → full _PROP_EFFECT_POOL and unconstrained variant selection
- embrace_repetition=False → 0.5x cross-section penalty and intra-section dedup active

**Rationale**: FR-006/FR-007/FR-008 require independent toggles. Boolean flags in the
existing config dataclass are the simplest mechanism. Default=True because this is the
new desired behavior — users who generate via the web UI or CLI get the improved output
by default.

**Alternatives considered**:
- Settings file toggle: Rejected — generation config is the right scope, not global settings.
- Enum-based modes: Rejected — overkill for two booleans.
