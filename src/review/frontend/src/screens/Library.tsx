import React, { useState, useMemo } from 'react';
import type { Song, Folder } from 'src/store/library';

type FilterStatus = 'all' | 'draft' | 'analyzed' | 'themed';

// Which screen to open for each status (FR-003)
function targetScreenForStatus(status: Song['status']): string {
  switch (status) {
    case 'themed':
      return 'theme';
    case 'analyzed':
      return 'timeline';
    case 'draft':
    default:
      return 'analyze';
  }
}

interface Props {
  songs: Song[];
  folders: Folder[];
  onSelectSong: (song: Song, screen: string) => void;
}

export function Library({ songs, folders, onSelectSong }: Props) {
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(
    () => new Set(folders.filter((f) => f.collapsed).map((f) => f.folder_id ?? (f as any).id)),
  );

  const filteredSongs = useMemo(() => {
    if (filterStatus === 'all') return songs;
    return songs.filter((s) => s.status === filterStatus);
  }, [songs, filterStatus]);

  function toggleFolder(folderId: string) {
    setCollapsedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  }

  // Build folder → songs map
  const songsByFolder = useMemo(() => {
    const map = new Map<string, Song[]>();
    for (const song of filteredSongs) {
      const fid = song.folder_id || 'unfiled';
      if (!map.has(fid)) map.set(fid, []);
      map.get(fid)!.push(song);
    }
    return map;
  }, [filteredSongs]);

  const FILTER_PILLS: { id: FilterStatus; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'draft', label: 'Draft' },
    { id: 'analyzed', label: 'Analyzed' },
    { id: 'themed', label: 'Themed' },
  ];

  // T134: Empty-library first-run centered drop target (FR-005c)
  if (songs.length === 0 && folders.every((f) => {
    const fid = (f as any).folder_id ?? (f as any).id;
    return fid === 'unfiled';
  })) {
    return (
      <div
        data-testid="library-empty-drop"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '60vh',
          gap: 16,
          color: 'var(--color-text-muted, #888)',
        }}
      >
        <div
          style={{
            border: '2px dashed var(--color-border, #444)',
            borderRadius: 12,
            padding: '48px 64px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <span style={{ fontSize: 40 }}>🎵</span>
          <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text, #f5f5f0)', margin: 0 }}>
            Drop an MP3 or WAV here to get started
          </p>
          <p style={{ fontSize: 13, margin: 0 }}>
            or use the upload button in the header
          </p>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="library-screen" style={{ padding: 24 }}>
      {/* Filter pills */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {FILTER_PILLS.map((pill) => (
          <button
            key={pill.id}
            role="button"
            aria-label={pill.label}
            data-active={String(filterStatus === pill.id)}
            onClick={() => setFilterStatus(pill.id)}
            style={{
              padding: '4px 14px',
              borderRadius: 16,
              border: '1px solid var(--color-border, #444)',
              background: filterStatus === pill.id ? 'var(--color-accent, #4ade80)' : 'transparent',
              color: filterStatus === pill.id ? '#000' : 'var(--color-text, #f5f5f0)',
              cursor: 'pointer',
              fontWeight: filterStatus === pill.id ? 600 : 400,
              fontSize: 13,
            }}
          >
            {pill.label}
          </button>
        ))}
      </div>

      {/* Folder sections */}
      {folders.map((folder) => {
        const folderId = (folder as any).folder_id ?? (folder as any).id;
        const folderSongs = songsByFolder.get(folderId) ?? [];
        const isCollapsed = collapsedFolders.has(folderId) || folder.collapsed;

        return (
          <div key={folderId} style={{ marginBottom: 24 }}>
            {/* Folder header */}
            <button
              data-testid={`folder-toggle-${folderId}`}
              onClick={() => toggleFolder(folderId)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-text-muted, #888)',
                fontWeight: 600,
                fontSize: 12,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: 8,
                padding: 0,
              }}
            >
              <span style={{ fontSize: 10 }}>{isCollapsed ? '▶' : '▼'}</span>
              {folder.name}
              <span style={{ fontWeight: 400, color: 'var(--color-text-muted, #888)', fontSize: 11 }}>
                ({folderSongs.length})
              </span>
            </button>

            {/* Songs in folder */}
            {!isCollapsed && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {folderSongs.length === 0 ? (
                  <p style={{ color: 'var(--color-text-muted, #888)', fontSize: 13, paddingLeft: 8 }}>
                    No songs in this folder
                  </p>
                ) : (
                  folderSongs.map((song) => (
                    <SongRow
                      key={song.song_id}
                      song={song}
                      onClick={() => onSelectSong(song, targetScreenForStatus(song.status))}
                    />
                  ))
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Songs not matching any folder (safety net) */}
      {filteredSongs.length === 0 && folders.length === 0 && (
        <p style={{ color: 'var(--color-text-muted, #888)' }}>No songs yet.</p>
      )}
    </div>
  );
}

interface SongRowProps {
  song: Song;
  onClick: () => void;
}

function StatusChip({ status }: { status: Song['status'] }) {
  const colors: Record<string, string> = {
    draft: '#888',
    analyzed: '#4ade80',
    themed: '#60a5fa',
    source_missing: '#ef4444',
  };
  return (
    <span
      data-testid={`status-chip-${status}`}
      style={{
        fontSize: 11,
        padding: '2px 8px',
        borderRadius: 10,
        border: `1px solid ${colors[status] ?? '#888'}`,
        color: colors[status] ?? '#888',
        textTransform: 'capitalize',
      }}
    >
      {status === 'source_missing' ? 'missing' : status}
    </span>
  );
}

function SongRow({ song, onClick }: SongRowProps) {
  return (
    <div
      data-testid={`song-row-${song.song_id}`}
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        borderRadius: 6,
        cursor: 'pointer',
        background: 'var(--color-surface, #1a1a1a)',
        border: '1px solid var(--color-border, #333)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontWeight: 500, fontSize: 14, color: 'var(--color-text, #f5f5f0)' }}>
          {song.title}
        </span>
        {song.artist && (
          <span style={{ fontSize: 12, color: 'var(--color-text-muted, #888)' }}>{song.artist}</span>
        )}
      </div>
      <StatusChip status={song.status} />
    </div>
  );
}
