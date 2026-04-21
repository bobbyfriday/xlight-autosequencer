/**
 * T108: Client-side max-overlap section-mapping utility.
 *
 * Mirrors src/review/api/v1/overlap_mapping.py.
 * The review dialog uses this for instant UI rendering before the server confirms.
 */

export interface OldSection {
  index: number;
  start_ms: number;
  end_ms: number;
  kind: string;
  label: string;
  theme_id: string | null;
}

export interface NewSection {
  index: number;
  start_ms: number;
  end_ms: number;
  kind: string;
  label: string;
}

export type MappingAction = 'kept' | 'shifted' | 'needs_theme';

export interface MappingEntry {
  new_section_index: number;
  action: MappingAction;
  inherited_theme_id: string | null;
  inherited_from_old_index: number | null;
  overlap_ratio: number;
}

export interface DroppedEntry {
  old_section_index: number;
  theme_id: string | null;
}

export interface OverlapMappingResult {
  mapping: MappingEntry[];
  dropped: DroppedEntry[];
}

const OVERLAP_THRESHOLD = 0.3;

function intersectionMs(
  aStart: number,
  aEnd: number,
  bStart: number,
  bEnd: number,
): number {
  return Math.max(0, Math.min(aEnd, bEnd) - Math.max(aStart, bStart));
}

export function computeOverlapMapping(
  oldSections: OldSection[],
  newSections: NewSection[],
): OverlapMappingResult {
  if (newSections.length === 0) {
    const dropped: DroppedEntry[] = oldSections.map((s) => ({
      old_section_index: s.index,
      theme_id: s.theme_id,
    }));
    return { mapping: [], dropped };
  }

  const mapping: MappingEntry[] = [];
  const matchedOldIndexes = new Set<number>();

  for (const newSec of newSections) {
    const newDur = newSec.end_ms - newSec.start_ms;
    let bestOverlap = 0;
    let bestOld: OldSection | null = null;

    for (const oldSec of oldSections) {
      const overlap = intersectionMs(
        newSec.start_ms,
        newSec.end_ms,
        oldSec.start_ms,
        oldSec.end_ms,
      );
      if (overlap > bestOverlap) {
        bestOverlap = overlap;
        bestOld = oldSec;
      }
    }

    const ratio = newDur > 0 && bestOld !== null ? bestOverlap / newDur : 0;

    let action: MappingAction;
    let inheritedThemeId: string | null = null;
    let inheritedFromOldIndex: number | null = null;

    if (ratio >= OVERLAP_THRESHOLD && bestOld !== null) {
      const isExact =
        bestOld.start_ms === newSec.start_ms && bestOld.end_ms === newSec.end_ms;
      action = isExact ? 'kept' : 'shifted';
      inheritedThemeId = bestOld.theme_id;
      inheritedFromOldIndex = bestOld.index;
      matchedOldIndexes.add(bestOld.index);
    } else {
      action = 'needs_theme';
    }

    mapping.push({
      new_section_index: newSec.index,
      action,
      inherited_theme_id: inheritedThemeId,
      inherited_from_old_index: inheritedFromOldIndex,
      overlap_ratio: Math.round(ratio * 10000) / 10000,
    });
  }

  const dropped: DroppedEntry[] = oldSections
    .filter((s) => !matchedOldIndexes.has(s.index))
    .map((s) => ({
      old_section_index: s.index,
      theme_id: s.theme_id,
    }));

  return { mapping, dropped };
}
