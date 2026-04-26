# Proposal: ethereal sections render at ~5% brightness instead of as a dim wash

## Problem

Empirical FSEQ analysis of "01 - Baby Shark with Jaws Intro" shows that **63% of the song duration renders at ≤15/255 channel brightness** with only 3-6% of channels active. The xsq has 30-65 effects per 5-second window throughout the song — generator placement isn't the issue. The variants/tiers selected for low-energy sections produce near-invisible output because `_compute_active_tiers` returns `frozenset({8})` (HERO-only) for any section classified as `ethereal` mood.

That decision was made deliberately in PR #77 (commit 9d6a2c48) to keep "tier_utilization" low during silent passages. The user-visible effect on a kid's song with built-in dynamics ("Baby Shark") is that the show looks dead for the entire mid-song quiet block (34-58s) and the final 28 seconds — a song that has constant audio activity but quiet moments.

## Goal

Restore visible-but-dim show behavior during ethereal sections so quiet musical passages show a low-brightness wash across all props instead of an effectively-blank canvas with a couple heroes.

## Scope

- **In scope:** `_compute_active_tiers` in `src/generator/effect_placer.py`. Restore Tier 1 (BASE_All) to the active set for ethereal sections so every prop gets a 0.40-brightness wash; keep Tier 8 for hero focal points.
- **Out of scope:**
  - Section classification (sections are still classified by energy as ethereal/structural/aggressive — that's working correctly)
  - The `qm_boundary` label itself (it gets through to the generator unchanged; the issue is downstream of the label, in tier selection)
  - Theme palette / variant changes (separate PRs #6, #10, #13)
  - Section merger changes (short qm_boundary segments could merge into adjacent labeled sections, but that's a separate issue)

## Why this approach over the alternative

**Considered:** add a "carry mood from neighbour" rule that promotes qm_boundary sections to the surrounding labeled section's mood. Rejected because:

1. The underlying problem isn't qm_boundary-specific — section 5 of Baby Shark is labeled `A` (a normal segmentino label) but ALSO renders at 5-12 brightness because its audio energy is low and it gets classified ethereal. Any low-energy section, however labeled, hits the same dim path.
2. Mood-from-neighbour adds complexity (boundary inference, conflict resolution when neighbours disagree) for the same outcome the simple tier-set fix achieves with one constant change.

**Decided:** restore `{1, 8}` for ethereal as the active tier set. Tier 1's existing 0.40 brightness multiplier (already in `_TIER_BRIGHTNESS`) preserves the visual hierarchy — ethereal sections will be ~40% as bright as structural ones, not equally bright. That's the gradient the original-original implementation gave; PR #77 made the contrast binary.
