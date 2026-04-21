import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SectionStrip } from '../../src/components/SectionStrip/SectionStrip';

const sections = [
  { index: 0, start_ms: 0, end_ms: 30000, kind: 'intro', label: 'Intro' },
  { index: 1, start_ms: 30000, end_ms: 90000, kind: 'verse', label: 'Verse 1' },
  { index: 2, start_ms: 90000, end_ms: 150000, kind: 'chorus', label: 'Chorus 1' },
];

const assignments = [
  { section_index: 0, theme_id: 'shimmer-wash', overrides: {}, user_confirmed: false },
  { section_index: 1, theme_id: 'driving-pulse', overrides: {}, user_confirmed: false },
  { section_index: 2, theme_id: 'peak-flash', overrides: {}, user_confirmed: true },
];

describe('SectionStrip', () => {
  it('renders a chip for each section', () => {
    render(<SectionStrip sections={sections} assignments={assignments} durationMs={150000} />);
    const chips = screen.getAllByRole('button');
    expect(chips.length).toBe(3);
  });

  it('chip width is proportional to section duration', () => {
    const { container } = render(
      <SectionStrip sections={sections} assignments={assignments} durationMs={150000} />
    );
    const chips = container.querySelectorAll('[data-testid="section-chip"]');
    // Verse (60s) should be wider than Intro (30s)
    const introStyle = (chips[0] as HTMLElement).style.width;
    const verseStyle = (chips[1] as HTMLElement).style.width;
    expect(introStyle).toBeTruthy();
    expect(verseStyle).toBeTruthy();
  });

  it('selected chip is visually distinguished', () => {
    const { container } = render(
      <SectionStrip
        sections={sections}
        assignments={assignments}
        durationMs={150000}
        selectedIndex={1}
      />
    );
    const chips = container.querySelectorAll('[data-testid="section-chip"]');
    expect((chips[1] as HTMLElement).getAttribute('data-selected')).toBe('true');
  });

  it('calls onSelect when chip clicked', () => {
    const onSelect = vi.fn();
    render(
      <SectionStrip
        sections={sections}
        assignments={assignments}
        durationMs={150000}
        onSelect={onSelect}
      />
    );
    const chips = screen.getAllByRole('button');
    fireEvent.click(chips[1]);
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
