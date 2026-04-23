import React, { useEffect } from 'react';
import { useKeyboardStore } from 'src/store/keyboard';

interface SectionsEditModeProps {
  /** Called when user presses S (split at playhead). */
  onSplit: () => void;
  /** Called when user presses M (merge with next section). */
  onMerge: () => void;
  /** Called when user presses Delete (delete selected section). */
  onDelete: () => void;
  /** Called when user presses R (rename selected section). */
  onRename: () => void;
}

/**
 * Mounts the TIMELINE sections-edit-mode keyboard shortcuts (FR-042).
 * Shortcuts are registered on mount and unregistered on unmount so they
 * are only active while the edit mode is open.
 */
export function SectionsEditMode({ onSplit, onMerge, onDelete, onRename }: SectionsEditModeProps) {
  const register = useKeyboardStore((s) => s.register);

  useEffect(() => {
    const unregister = [
      register({ key: 's', scope: 'timeline', handler: onSplit }),
      register({ key: 'm', scope: 'timeline', handler: onMerge }),
      register({ key: 'Delete', scope: 'timeline', handler: onDelete }),
      register({ key: 'r', scope: 'timeline', handler: onRename }),
    ];
    return () => unregister.forEach((fn) => fn());
  }, [register, onSplit, onMerge, onDelete, onRename]);

  // This component only manages keyboard shortcuts; it renders nothing.
  return null;
}
