import React from 'react';

interface SectionsEditModeBarProps {
  onSplit: () => void;
  onMerge: () => void;
  onDelete: () => void;
  onRename: () => void;
  onExit: () => void;
  canDelete: boolean;
  canMerge: boolean;
}

/**
 * Toolbar shown when sections edit mode is active (FR-042).
 * Buttons map 1:1 to keyboard shortcuts S/M/Del/R.
 */
export function SectionsEditModeBar({
  onSplit,
  onMerge,
  onDelete,
  onRename,
  onExit,
  canDelete,
  canMerge,
}: SectionsEditModeBarProps) {
  return (
    <div role="toolbar" aria-label="Section edit mode">
      <button data-testid="btn-split" onClick={onSplit}>
        Split (S)
      </button>
      <button data-testid="btn-merge" onClick={onMerge} disabled={!canMerge}>
        Merge (M)
      </button>
      <button data-testid="btn-delete" onClick={onDelete} disabled={!canDelete}>
        Delete (Del)
      </button>
      <button data-testid="btn-rename" onClick={onRename}>
        Rename (R)
      </button>
      <button data-testid="btn-exit" onClick={onExit}>
        Done
      </button>
    </div>
  );
}
