import React, { useState } from 'react';
import { api } from 'src/api/client';
import type { MappingEntry, DroppedEntry } from 'src/util/overlap';

interface Section {
  index: number;
  start_ms: number;
  end_ms: number;
  kind: string;
  label: string;
}

interface ReanalysisDialogProps {
  songId: string;
  runId: string;
  /** Max-overlap mapping computed client-side from overlap.ts. */
  mapping: MappingEntry[];
  /** Old sections that have no new counterpart. */
  dropped: DroppedEntry[];
  /** New section list from the pending run. */
  newSections: Section[];
  /** Called with the server response after commit succeeds. */
  onConfirm: (result: { sections: Section[]; assignments: unknown[] }) => void;
  /** Called when the user cancels — prior analysis must remain intact. */
  onCancel: () => void;
}

/**
 * Review dialog shown before committing a force re-analysis result.
 * Lists carry-over / shifted / dropped / needs-theme rows so the user
 * understands what will change before confirming (FR-013a).
 */
export function ReanalysisDialog({
  songId,
  runId,
  mapping,
  dropped,
  newSections,
  onConfirm,
  onCancel,
}: ReanalysisDialogProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      const assignmentMapping = mapping.map((entry) => ({
        new_section_index: entry.new_section_index,
        inherited_from_old_index: entry.inherited_from_old_index,
        action: entry.action,
      }));
      const result = await api.post<{ sections: Section[]; assignments: unknown[] }>(
        `/songs/${songId}/analyze/commit`,
        { run_id: runId, assignment_mapping: assignmentMapping },
      );
      onConfirm(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Commit failed');
      setSubmitting(false);
    }
  }

  const newSectionsByIdx = Object.fromEntries(newSections.map((s) => [s.index, s]));

  return (
    <div role="dialog" aria-modal="true" aria-label="Review re-analysis">
      <h2>Review Re-analysis</h2>
      <p>The analyzer produced a new section list. Review the changes before applying.</p>

      {/* Mapping rows */}
      <table>
        <thead>
          <tr>
            <th>Status</th>
            <th>New section</th>
            <th>Theme</th>
          </tr>
        </thead>
        <tbody>
          {mapping.map((entry) => {
            const sec = newSectionsByIdx[entry.new_section_index];
            const label = sec?.label ?? `Section ${entry.new_section_index}`;

            if (entry.action === 'kept') {
              return (
                <tr key={`kept-${entry.new_section_index}`} data-testid={`row-kept-${entry.new_section_index}`}>
                  <td>Kept</td>
                  <td>{label}</td>
                  <td>{entry.inherited_theme_id}</td>
                </tr>
              );
            }
            if (entry.action === 'shifted') {
              return (
                <tr key={`shifted-${entry.new_section_index}`} data-testid={`row-shifted-${entry.new_section_index}`}>
                  <td>Shifted</td>
                  <td>{label}</td>
                  <td>{entry.inherited_theme_id}</td>
                </tr>
              );
            }
            // needs_theme
            return (
              <tr key={`needs-theme-${entry.new_section_index}`} data-testid={`row-needs-theme-${entry.new_section_index}`}>
                <td>Needs theme</td>
                <td>{label}</td>
                <td>—</td>
              </tr>
            );
          })}

          {/* Dropped rows */}
          {dropped.map((d) => (
            <tr key={`dropped-${d.old_section_index}`} data-testid={`row-dropped-${d.old_section_index}`}>
              <td>Dropped</td>
              <td>Old section {d.old_section_index}</td>
              <td>{d.theme_id ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {error && <p role="alert">{error}</p>}

      <div>
        <button
          data-testid="btn-cancel"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </button>
        <button
          data-testid="btn-confirm"
          onClick={handleConfirm}
          disabled={submitting}
        >
          {submitting ? 'Applying…' : 'Apply Changes'}
        </button>
      </div>
    </div>
  );
}
