/**
 * T107: Client-side overlap-mapping tests — mirrors test_overlap_mapping.py.
 * The review dialog computes this mapping client-side for instant UI rendering.
 */
import { describe, it, expect } from 'vitest';
import { computeOverlapMapping, type OldSection, type NewSection } from '../../src/util/overlap';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function oldSec(index: number, start_ms: number, end_ms: number, theme_id = 'shimmer-wash'): OldSection {
  return { index, start_ms, end_ms, kind: 'verse', label: `Section ${index}`, theme_id };
}

function newSec(index: number, start_ms: number, end_ms: number): NewSection {
  return { index, start_ms, end_ms, kind: 'verse', label: `Section ${index}` };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('computeOverlapMapping', () => {
  it('identical sections map to themselves with action kept', () => {
    const old = [oldSec(0, 0, 10000, 'theme-a'), oldSec(1, 10000, 20000, 'theme-b')];
    const next = [newSec(0, 0, 10000), newSec(1, 10000, 20000)];
    const result = computeOverlapMapping(old, next);
    result.mapping.forEach((m) => {
      expect(['kept', 'shifted']).toContain(m.action);
    });
  });

  it('shifted boundary (200ms) keeps carry-over theme', () => {
    const old = [oldSec(0, 0, 10000, 'theme-a'), oldSec(1, 10000, 20000, 'theme-b')];
    const next = [newSec(0, 0, 10200), newSec(1, 10200, 20000)];
    const result = computeOverlapMapping(old, next);
    const byIdx = Object.fromEntries(result.mapping.map((m) => [m.new_section_index, m]));
    expect(['kept', 'shifted']).toContain(byIdx[0].action);
    expect(byIdx[0].inherited_theme_id).toBe('theme-a');
    expect(['kept', 'shifted']).toContain(byIdx[1].action);
    expect(byIdx[1].inherited_theme_id).toBe('theme-b');
  });

  it('low overlap (< 0.3) produces needs_theme', () => {
    // New section overlaps old by 1000ms of 10000ms = 0.10 < 0.3
    const old = [oldSec(0, 0, 10000, 'theme-a')];
    const next = [newSec(0, 9000, 19000)];
    const result = computeOverlapMapping(old, next);
    expect(result.mapping[0].action).toBe('needs_theme');
    expect(result.mapping[0].inherited_theme_id).toBeNull();
  });

  it('0.3 threshold boundary is accepted (carry-over)', () => {
    // New section 10000ms, overlap with old 3000ms = 0.3
    const old = [oldSec(0, 0, 10000, 'theme-a')];
    const next = [newSec(0, 7000, 17000)];
    const result = computeOverlapMapping(old, next);
    expect(['kept', 'shifted']).toContain(result.mapping[0].action);
    expect(result.mapping[0].inherited_theme_id).toBe('theme-a');
  });

  it('just below 0.3 gives needs_theme', () => {
    // 2999ms of 10000ms = 0.2999
    const old = [oldSec(0, 0, 10000, 'theme-a')];
    const next = [newSec(0, 7001, 17001)];
    const result = computeOverlapMapping(old, next);
    expect(result.mapping[0].action).toBe('needs_theme');
  });

  it('old section not claimed by any new section is dropped', () => {
    const old = [oldSec(0, 0, 10000, 'theme-a'), oldSec(1, 10000, 20000, 'theme-b')];
    // New covers only old[0] territory
    const next = [newSec(0, 0, 10000)];
    const result = computeOverlapMapping(old, next);
    expect(result.dropped.length).toBeGreaterThanOrEqual(1);
    const droppedIdxs = result.dropped.map((d) => d.old_section_index);
    expect(droppedIdxs).toContain(1);
  });

  it('no dropped when all old sections are mapped', () => {
    const old = [oldSec(0, 0, 10000, 'theme-a'), oldSec(1, 10000, 20000, 'theme-b')];
    const next = [newSec(0, 0, 10000), newSec(1, 10000, 20000)];
    const result = computeOverlapMapping(old, next);
    expect(result.dropped).toHaveLength(0);
  });

  it('new section in entirely new territory needs_theme', () => {
    const old = [oldSec(0, 0, 10000, 'theme-a')];
    const next = [newSec(0, 0, 10000), newSec(1, 10000, 20000)];
    const result = computeOverlapMapping(old, next);
    const byIdx = Object.fromEntries(result.mapping.map((m) => [m.new_section_index, m]));
    expect(byIdx[1].action).toBe('needs_theme');
  });

  it('split: both halves carry over theme from old section', () => {
    const old = [oldSec(0, 0, 20000, 'theme-a')];
    const next = [newSec(0, 0, 10000), newSec(1, 10000, 20000)];
    const result = computeOverlapMapping(old, next);
    const byIdx = Object.fromEntries(result.mapping.map((m) => [m.new_section_index, m]));
    expect(byIdx[0].inherited_theme_id).toBe('theme-a');
    expect(byIdx[1].inherited_theme_id).toBe('theme-a');
  });

  it('result has mapping and dropped keys', () => {
    const result = computeOverlapMapping([oldSec(0, 0, 10000)], [newSec(0, 0, 10000)]);
    expect(result).toHaveProperty('mapping');
    expect(result).toHaveProperty('dropped');
  });

  it('each mapping entry has required fields', () => {
    const result = computeOverlapMapping([oldSec(0, 0, 10000)], [newSec(0, 0, 10000)]);
    for (const entry of result.mapping) {
      expect(entry).toHaveProperty('new_section_index');
      expect(entry).toHaveProperty('action');
      expect(entry).toHaveProperty('inherited_theme_id');
    }
  });

  it('empty inputs return empty results', () => {
    const result = computeOverlapMapping([], []);
    expect(result.mapping).toHaveLength(0);
    expect(result.dropped).toHaveLength(0);
  });

  it('only new sections all need_theme', () => {
    const result = computeOverlapMapping([], [newSec(0, 0, 10000), newSec(1, 10000, 20000)]);
    result.mapping.forEach((m) => {
      expect(m.action).toBe('needs_theme');
    });
  });
});
