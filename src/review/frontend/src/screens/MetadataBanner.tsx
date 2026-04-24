import { useEffect, useState } from 'react';

interface GeniusMatch {
  url: string;
  artist: string;
  title: string;
  genius_id?: number;
}

interface GeniusLookup {
  section_source: string | null;
  match: GeniusMatch | null;
  reject_reason: string | null;
}

interface Props {
  songId: string;
  /** ID3-derived display title (from song.title on the Song record). */
  id3Title: string;
  /** ID3-derived display artist (may be empty on files with no tag). */
  id3Artist: string;
  /** Persisted override from PATCH /api/v1/songs/<id>/metadata, or null. */
  overrideArtist: string | null;
  /** Persisted override title, or null. */
  overrideTitle: string | null;
  /** Live Genius lookup result from SSE event or /analysis response. */
  genius: GeniusLookup | null;
  /**
   * Called after a successful PATCH so the parent can refresh its copy
   * of the song record (override values land on the song object).
   */
  onSaved: (next: { override_artist: string | null; override_title: string | null }) => void;
}

export function MetadataBanner({
  songId, id3Title, id3Artist, overrideArtist, overrideTitle, genius, onSaved,
}: Props) {
  const [artist, setArtist] = useState(overrideArtist ?? id3Artist ?? '');
  const [title, setTitle] = useState(overrideTitle ?? id3Title ?? '');
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Re-sync from props when the song record changes from outside (e.g. parent
  // refetched library). Don't clobber in-progress edits; only update when the
  // field isn't focused.
  useEffect(() => {
    setArtist((prev) => (document.activeElement?.getAttribute('data-field') === 'artist' ? prev : (overrideArtist ?? id3Artist ?? '')));
    setTitle((prev) => (document.activeElement?.getAttribute('data-field') === 'title' ? prev : (overrideTitle ?? id3Title ?? '')));
  }, [overrideArtist, overrideTitle, id3Artist, id3Title]);

  const currentArtist = overrideArtist ?? id3Artist ?? '';
  const currentTitle = overrideTitle ?? id3Title ?? '';
  const hasChanges = artist !== currentArtist || title !== currentTitle;

  async function save() {
    if (!hasChanges) return;
    setSaving(true);
    setSaveError(null);
    try {
      // Only send fields that actually changed. "" clears an override; omit
      // the key entirely when the user didn't touch that field, so we don't
      // clobber an existing override by accident.
      const body: Record<string, string> = {};
      if (artist !== currentArtist) body.artist = artist;
      if (title !== currentTitle) body.title = title;
      const res = await fetch(`/api/v1/songs/${songId}/metadata`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        setSaveError(j?.error?.message ?? `Save failed (${res.status})`);
        return;
      }
      const updated = await res.json();
      onSaved({
        override_artist: updated.override_artist ?? null,
        override_title: updated.override_title ?? null,
      });
      setSavedAt(Date.now());
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  const rejectReason = genius?.reject_reason ?? null;
  const match = genius?.match ?? null;
  const sourceIsGenius = genius?.section_source === 'genius';

  const matchLooksSuspicious =
    match != null &&
    currentArtist.trim() !== '' &&
    match.artist.trim().toLowerCase() !== currentArtist.trim().toLowerCase();

  return (
    <div
      data-testid="metadata-banner"
      style={{
        padding: '12px 32px',
        background: 'rgba(255,255,255,0.03)',
        borderBottom: '1px solid var(--color-border, #2a2a2a)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        fontSize: 13,
      }}
    >
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ color: 'var(--color-text-muted, #888)', fontSize: 12, letterSpacing: 0.5 }}>
          ARTIST
        </label>
        <input
          data-testid="metadata-artist"
          data-field="artist"
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
          placeholder={id3Artist || '(unknown)'}
          style={{
            minWidth: 180,
            padding: '4px 8px',
            background: 'var(--color-surface-2, #1e1e24)',
            border: `1px solid ${overrideArtist ? 'var(--color-accent, #d97757)' : 'var(--color-border, #333)'}`,
            borderRadius: 4,
            color: 'var(--color-text, #f5f5f0)',
            fontSize: 13,
          }}
        />
        <label style={{ color: 'var(--color-text-muted, #888)', fontSize: 12, letterSpacing: 0.5 }}>
          TITLE
        </label>
        <input
          data-testid="metadata-title"
          data-field="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
          placeholder={id3Title || '(unknown)'}
          style={{
            flex: 1,
            minWidth: 240,
            padding: '4px 8px',
            background: 'var(--color-surface-2, #1e1e24)',
            border: `1px solid ${overrideTitle ? 'var(--color-accent, #d97757)' : 'var(--color-border, #333)'}`,
            borderRadius: 4,
            color: 'var(--color-text, #f5f5f0)',
            fontSize: 13,
          }}
        />
        {saving && <span style={{ color: 'var(--color-text-muted, #888)' }}>saving…</span>}
        {savedAt != null && !saving && !hasChanges && (
          <span data-testid="metadata-saved" style={{ color: 'var(--color-accent, #4ade80)', fontSize: 12 }}>
            ✓ saved — will apply on next re-analyze
          </span>
        )}
        {saveError && (
          <span data-testid="metadata-save-error" style={{ color: 'var(--color-error, #d43a2f)', fontSize: 12 }}>
            {saveError}
          </span>
        )}
      </div>

      {/* Genius provenance sub-row */}
      {match != null && (
        <div
          data-testid="genius-match-row"
          style={{
            display: 'flex', gap: 8, alignItems: 'baseline', fontSize: 12,
            color: sourceIsGenius ? 'var(--color-text-muted, #888)' : 'var(--color-warning, #e0a82e)',
          }}
        >
          <span>{sourceIsGenius ? 'Matched on Genius:' : 'Genius returned (rejected):'}</span>
          <a
            href={match.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'inherit', textDecoration: 'underline' }}
          >
            {match.artist} — {match.title}
          </a>
          {matchLooksSuspicious && (
            <span data-testid="genius-match-mismatch" style={{ color: 'var(--color-warning, #e0a82e)' }}>
              ⚠ artist differs from this song's metadata — check the tag
            </span>
          )}
        </div>
      )}

      {rejectReason && (
        <div
          data-testid="genius-reject-reason"
          style={{
            fontSize: 12,
            color: 'var(--color-warning, #e0a82e)',
            padding: '6px 10px',
            background: 'rgba(224,168,46,0.08)',
            borderRadius: 4,
            borderLeft: '2px solid var(--color-warning, #e0a82e)',
          }}
        >
          Falling back to heuristic labels — Genius result rejected because: {rejectReason}. Correcting the artist/title above and re-analyzing usually fixes this.
        </div>
      )}

      {/* Friendly hint when ID3 is empty so users know what to type */}
      {!id3Artist && !overrideArtist && (
        <div style={{ fontSize: 12, color: 'var(--color-text-muted, #888)' }}>
          No artist tag on this file — type the artist above so Genius can match it.
        </div>
      )}
    </div>
  );
}
