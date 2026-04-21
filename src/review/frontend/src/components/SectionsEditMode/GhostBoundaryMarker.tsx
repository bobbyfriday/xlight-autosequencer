import React from 'react';

interface GhostBoundaryMarkerProps {
  at_ms: number;
  durationMs: number;
  confidence: number;
  onPromote: (at_ms: number) => void;
}

/**
 * Renders a ghost boundary marker at the proportional position on the timeline.
 * Clicking it calls onPromote with the boundary's at_ms value.
 */
export function GhostBoundaryMarker({
  at_ms,
  durationMs,
  confidence,
  onPromote,
}: GhostBoundaryMarkerProps) {
  const leftPct = durationMs > 0 ? `${(at_ms / durationMs) * 100}%` : '0%';

  return (
    <button
      data-testid="ghost-boundary-marker"
      title={`Ghost boundary (confidence: ${Math.round(confidence * 100)}%) — click to promote`}
      style={{
        position: 'absolute',
        left: leftPct,
        opacity: 0.5 + confidence * 0.5,
      }}
      onClick={() => onPromote(at_ms)}
      aria-label={`Promote ghost boundary at ${at_ms}ms`}
    />
  );
}
