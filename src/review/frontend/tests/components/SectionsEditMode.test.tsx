/**
 * T109: Failing tests for SectionsEditMode component (US3).
 *
 * Covers: mode toggle, S/M/Del/R keyboard shortcuts (FR-042),
 * ghost-boundary rendering, section-rename inline edit.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { useKeyboardStore } from '../../src/store/keyboard';
import { SectionsEditModeBar } from '../../src/components/SectionsEditMode/SectionsEditModeBar';
import { GhostBoundaryMarker } from '../../src/components/SectionsEditMode/GhostBoundaryMarker';
import { SectionRenameField } from '../../src/components/SectionsEditMode/SectionRenameField';
import { SectionsEditMode } from '../../src/components/SectionsEditMode/SectionsEditMode';

beforeEach(() => {
  // Reset keyboard store between tests
  useKeyboardStore.setState({ bindings: [], suspended: false });
});

// ---------------------------------------------------------------------------
// SectionsEditModeBar — mode toggle + button toolbar
// ---------------------------------------------------------------------------

describe('SectionsEditModeBar', () => {
  it('renders the edit mode toolbar', () => {
    render(
      <SectionsEditModeBar
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
        onExit={vi.fn()}
        canDelete={true}
        canMerge={true}
      />
    );
    expect(screen.getByRole('toolbar')).toBeTruthy();
  });

  it('renders Split, Merge, Delete, Rename buttons', () => {
    render(
      <SectionsEditModeBar
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
        onExit={vi.fn()}
        canDelete={true}
        canMerge={true}
      />
    );
    expect(screen.getByTestId('btn-split')).toBeTruthy();
    expect(screen.getByTestId('btn-merge')).toBeTruthy();
    expect(screen.getByTestId('btn-delete')).toBeTruthy();
    expect(screen.getByTestId('btn-rename')).toBeTruthy();
  });

  it('calls onSplit when Split button is clicked', () => {
    const onSplit = vi.fn();
    render(
      <SectionsEditModeBar
        onSplit={onSplit}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
        onExit={vi.fn()}
        canDelete={true}
        canMerge={true}
      />
    );
    fireEvent.click(screen.getByTestId('btn-split'));
    expect(onSplit).toHaveBeenCalledOnce();
  });

  it('calls onMerge when Merge button is clicked', () => {
    const onMerge = vi.fn();
    render(
      <SectionsEditModeBar
        onSplit={vi.fn()}
        onMerge={onMerge}
        onDelete={vi.fn()}
        onRename={vi.fn()}
        onExit={vi.fn()}
        canDelete={true}
        canMerge={true}
      />
    );
    fireEvent.click(screen.getByTestId('btn-merge'));
    expect(onMerge).toHaveBeenCalledOnce();
  });

  it('calls onDelete when Delete button is clicked', () => {
    const onDelete = vi.fn();
    render(
      <SectionsEditModeBar
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={onDelete}
        onRename={vi.fn()}
        onExit={vi.fn()}
        canDelete={true}
        canMerge={true}
      />
    );
    fireEvent.click(screen.getByTestId('btn-delete'));
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it('Delete button is disabled when canDelete is false', () => {
    render(
      <SectionsEditModeBar
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
        onExit={vi.fn()}
        canDelete={false}
        canMerge={true}
      />
    );
    const btn = screen.getByTestId('btn-delete') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('Merge button is disabled when canMerge is false', () => {
    render(
      <SectionsEditModeBar
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
        onExit={vi.fn()}
        canDelete={true}
        canMerge={false}
      />
    );
    const btn = screen.getByTestId('btn-merge') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('calls onExit when Exit/Done button is clicked', () => {
    const onExit = vi.fn();
    render(
      <SectionsEditModeBar
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
        onExit={onExit}
        canDelete={true}
        canMerge={true}
      />
    );
    fireEvent.click(screen.getByTestId('btn-exit'));
    expect(onExit).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Keyboard shortcuts via SectionsEditMode mount/unmount (FR-042)
// ---------------------------------------------------------------------------

describe('SectionsEditMode keyboard shortcuts', () => {
  it('registers S shortcut in timeline scope on mount', () => {
    const onSplit = vi.fn();
    render(
      <SectionsEditMode
        onSplit={onSplit}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />
    );
    const store = useKeyboardStore.getState();
    const binding = store.bindings.find((b) => b.key === 's' && b.scope === 'timeline');
    expect(binding).toBeTruthy();
  });

  it('registers M shortcut in timeline scope on mount', () => {
    render(
      <SectionsEditMode
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />
    );
    const store = useKeyboardStore.getState();
    const binding = store.bindings.find((b) => b.key === 'm' && b.scope === 'timeline');
    expect(binding).toBeTruthy();
  });

  it('registers Delete shortcut in timeline scope on mount', () => {
    render(
      <SectionsEditMode
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />
    );
    const store = useKeyboardStore.getState();
    const binding = store.bindings.find(
      (b) => b.key === 'Delete' && b.scope === 'timeline',
    );
    expect(binding).toBeTruthy();
  });

  it('registers R shortcut in timeline scope on mount', () => {
    render(
      <SectionsEditMode
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />
    );
    const store = useKeyboardStore.getState();
    const binding = store.bindings.find((b) => b.key === 'r' && b.scope === 'timeline');
    expect(binding).toBeTruthy();
  });

  it('unregisters all shortcuts on unmount', () => {
    const { unmount } = render(
      <SectionsEditMode
        onSplit={vi.fn()}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />
    );
    unmount();
    const store = useKeyboardStore.getState();
    const timelineBindings = store.bindings.filter((b) => b.scope === 'timeline');
    expect(timelineBindings).toHaveLength(0);
  });

  it('S dispatch calls onSplit', () => {
    const onSplit = vi.fn();
    render(
      <SectionsEditMode
        onSplit={onSplit}
        onMerge={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />
    );
    act(() => {
      useKeyboardStore.getState().dispatch('s', 'timeline');
    });
    expect(onSplit).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// GhostBoundaryMarker — ghost boundary UI on the timeline
// ---------------------------------------------------------------------------

describe('GhostBoundaryMarker', () => {
  it('renders a marker element', () => {
    render(
      <GhostBoundaryMarker
        at_ms={5000}
        durationMs={20000}
        confidence={0.7}
        onPromote={vi.fn()}
      />
    );
    expect(screen.getByTestId('ghost-boundary-marker')).toBeTruthy();
  });

  it('calls onPromote when marker is clicked', () => {
    const onPromote = vi.fn();
    render(
      <GhostBoundaryMarker
        at_ms={5000}
        durationMs={20000}
        confidence={0.7}
        onPromote={onPromote}
      />
    );
    fireEvent.click(screen.getByTestId('ghost-boundary-marker'));
    expect(onPromote).toHaveBeenCalledWith(5000);
  });

  it('marker is positioned proportionally to at_ms / durationMs', () => {
    const { container } = render(
      <GhostBoundaryMarker
        at_ms={5000}
        durationMs={20000}
        confidence={0.7}
        onPromote={vi.fn()}
      />
    );
    const marker = container.querySelector('[data-testid="ghost-boundary-marker"]') as HTMLElement;
    // at_ms/durationMs = 0.25 → left should be 25%
    expect(marker.style.left).toBe('25%');
  });
});

// ---------------------------------------------------------------------------
// SectionRenameField — inline edit
// ---------------------------------------------------------------------------

describe('SectionRenameField', () => {
  it('renders an input with the current label', () => {
    render(
      <SectionRenameField
        initialLabel="Verse 1"
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input.value).toBe('Verse 1');
  });

  it('calls onSubmit with new label on Enter', () => {
    const onSubmit = vi.fn();
    render(
      <SectionRenameField
        initialLabel="Verse 1"
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Chorus A' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSubmit).toHaveBeenCalledWith('Chorus A');
  });

  it('calls onCancel on Escape', () => {
    const onCancel = vi.fn();
    render(
      <SectionRenameField
        initialLabel="Verse 1"
        onSubmit={vi.fn()}
        onCancel={onCancel}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.keyDown(input, { key: 'Escape' });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('does not call onSubmit for empty label', () => {
    const onSubmit = vi.fn();
    render(
      <SectionRenameField
        initialLabel="Verse 1"
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('does not call onSubmit for whitespace-only label', () => {
    const onSubmit = vi.fn();
    render(
      <SectionRenameField
        initialLabel="Verse 1"
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
