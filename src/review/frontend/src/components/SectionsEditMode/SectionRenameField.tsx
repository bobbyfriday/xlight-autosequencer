import React, { useState, useRef, useEffect } from 'react';

interface SectionRenameFieldProps {
  initialLabel: string;
  onSubmit: (label: string) => void;
  onCancel: () => void;
}

/**
 * Inline text field for renaming a section.
 * Enter submits (if label is non-empty, non-whitespace); Escape cancels.
 */
export function SectionRenameField({ initialLabel, onSubmit, onCancel }: SectionRenameFieldProps) {
  const [value, setValue] = useState(initialLabel);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      if (value.trim()) {
        onSubmit(value);
      }
    } else if (e.key === 'Escape') {
      onCancel();
    }
  }

  return (
    <input
      ref={inputRef}
      type="text"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onKeyDown={handleKeyDown}
      aria-label="Rename section"
    />
  );
}
