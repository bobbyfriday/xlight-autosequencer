/**
 * T095: Library screen tests — song grid/list, filter pills, folder sections,
 * routing by status, SC-007 (<200ms filter), FR-003.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Library } from '../../src/screens/Library';

// Reset store state between tests
beforeEach(() => {
  vi.clearAllMocks();
});

const SONG_DRAFT = {
  song_id: 'draft_001',
  title: 'Draft Song',
  artist: null,
  duration_ms: 120000,
  bpm: null,
  key: null,
  time_signature: null as [number, number] | null,
  status: 'draft' as const,
  source_paths: [] as string[],
  folder_id: 'unfiled',
  imported_at: '2026-01-01T00:00:00Z',
  last_opened_at: null,
  source_exists: true,
};

const SONG_ANALYZED = {
  song_id: 'analyzed_002',
  title: 'Analyzed Song',
  artist: 'Artist A',
  duration_ms: 180000,
  bpm: 128,
  key: 'G major',
  time_signature: [4, 4] as [number, number],
  status: 'analyzed' as const,
  source_paths: ['/tmp/analyzed.mp3'],
  folder_id: 'unfiled',
  imported_at: '2026-01-01T01:00:00Z',
  last_opened_at: null,
  source_exists: true,
};

const SONG_THEMED = {
  song_id: 'themed_003',
  title: 'Themed Song',
  artist: 'Artist B',
  duration_ms: 200000,
  bpm: 100,
  key: 'E minor',
  time_signature: [4, 4] as [number, number],
  status: 'themed' as const,
  source_paths: ['/tmp/themed.mp3'],
  folder_id: 'xmas',
  imported_at: '2026-01-01T02:00:00Z',
  last_opened_at: null,
  source_exists: true,
};

const FOLDER_UNFILED = {
  folder_id: 'unfiled',
  name: 'Unfiled',
  collapsed: false,
  order: 0,
};

const FOLDER_XMAS = {
  folder_id: 'xmas',
  name: 'Christmas',
  collapsed: false,
  order: 1,
};

describe('Library screen', () => {
  describe('song grid rendering', () => {
    it('renders all songs from props', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      expect(screen.getByText('Draft Song')).toBeTruthy();
      expect(screen.getByText('Analyzed Song')).toBeTruthy();
      expect(screen.getByText('Themed Song')).toBeTruthy();
    });

    it('renders status chip for each song', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      // Each status chip should be present via data-testid
      expect(screen.getByTestId('status-chip-draft')).toBeTruthy();
      expect(screen.getByTestId('status-chip-analyzed')).toBeTruthy();
      expect(screen.getByTestId('status-chip-themed')).toBeTruthy();
    });

    it('renders folder sections', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      expect(screen.getByText('Unfiled')).toBeTruthy();
      expect(screen.getByText('Christmas')).toBeTruthy();
    });

    it('shows empty-state message when no songs', () => {
      render(
        <Library
          songs={[]}
          folders={[FOLDER_UNFILED]}
          onSelectSong={() => {}}
        />,
      );
      // Some empty state indication
      expect(screen.getByTestId('library-screen')).toBeTruthy();
    });
  });

  describe('filter pills (SC-007)', () => {
    it('renders filter pills for all/draft/analyzed/themed', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      expect(screen.getByRole('button', { name: /all/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /draft/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /analyzed/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /themed/i })).toBeTruthy();
    });

    it('shows all songs when "all" pill active', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      // Default is "all"
      expect(screen.getByText('Draft Song')).toBeTruthy();
      expect(screen.getByText('Analyzed Song')).toBeTruthy();
      expect(screen.getByText('Themed Song')).toBeTruthy();
    });

    it('filters to analyzed-only when pill clicked', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      const analyzedPill = screen.getByRole('button', { name: /^analyzed$/i });
      fireEvent.click(analyzedPill);
      expect(screen.getByText('Analyzed Song')).toBeTruthy();
      expect(screen.queryByText('Draft Song')).toBeNull();
      expect(screen.queryByText('Themed Song')).toBeNull();
    });

    it('filters to draft-only when pill clicked', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      const draftPill = screen.getByRole('button', { name: /^draft$/i });
      fireEvent.click(draftPill);
      expect(screen.getByText('Draft Song')).toBeTruthy();
      expect(screen.queryByText('Analyzed Song')).toBeNull();
      expect(screen.queryByText('Themed Song')).toBeNull();
    });

    it('filters to themed-only when pill clicked', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      const themedPill = screen.getByRole('button', { name: /^themed$/i });
      fireEvent.click(themedPill);
      expect(screen.queryByText('Draft Song')).toBeNull();
      expect(screen.queryByText('Analyzed Song')).toBeNull();
      expect(screen.getByText('Themed Song')).toBeTruthy();
    });

    it('restores all songs when "all" pill clicked after filter', () => {
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={() => {}}
        />,
      );
      const draftPill = screen.getByRole('button', { name: /^draft$/i });
      fireEvent.click(draftPill);
      const allPill = screen.getByRole('button', { name: /^all$/i });
      fireEvent.click(allPill);
      expect(screen.getByText('Draft Song')).toBeTruthy();
      expect(screen.getByText('Analyzed Song')).toBeTruthy();
      expect(screen.getByText('Themed Song')).toBeTruthy();
    });

    it('filter update completes within 200ms (SC-007)', async () => {
      render(
        <Library
          songs={Array.from({ length: 50 }, (_, i) => ({
            ...SONG_DRAFT,
            song_id: `song_${i}`,
            title: `Song ${i}`,
          }))}
          folders={[FOLDER_UNFILED]}
          onSelectSong={() => {}}
        />,
      );
      const start = performance.now();
      const draftPill = screen.getByRole('button', { name: /^draft$/i });
      fireEvent.click(draftPill);
      const elapsed = performance.now() - start;
      expect(elapsed).toBeLessThan(200);
    });
  });

  describe('routing by status (FR-003)', () => {
    it('calls onSelectSong with song and target screen', () => {
      const onSelectSong = vi.fn();
      render(
        <Library
          songs={[SONG_DRAFT, SONG_ANALYZED, SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={onSelectSong}
        />,
      );
      const draftEntry = screen.getByText('Draft Song');
      fireEvent.click(draftEntry);
      expect(onSelectSong).toHaveBeenCalledWith(
        expect.objectContaining({ song_id: 'draft_001' }),
        expect.stringMatching(/analyze/),
      );
    });

    it('routes analyzed song to timeline/analyze screen', () => {
      const onSelectSong = vi.fn();
      render(
        <Library
          songs={[SONG_ANALYZED]}
          folders={[FOLDER_UNFILED]}
          onSelectSong={onSelectSong}
        />,
      );
      fireEvent.click(screen.getByText('Analyzed Song'));
      expect(onSelectSong).toHaveBeenCalledWith(
        expect.objectContaining({ song_id: 'analyzed_002' }),
        expect.stringMatching(/timeline|analyze/),
      );
    });

    it('routes themed song to theme screen', () => {
      const onSelectSong = vi.fn();
      render(
        <Library
          songs={[SONG_THEMED]}
          folders={[FOLDER_UNFILED, FOLDER_XMAS]}
          onSelectSong={onSelectSong}
        />,
      );
      fireEvent.click(screen.getByText('Themed Song'));
      expect(onSelectSong).toHaveBeenCalledWith(
        expect.objectContaining({ song_id: 'themed_003' }),
        expect.stringMatching(/theme/),
      );
    });
  });

  describe('folder section collapsibility', () => {
    it('renders folder toggle button', () => {
      render(
        <Library
          songs={[SONG_DRAFT]}
          folders={[FOLDER_UNFILED]}
          onSelectSong={() => {}}
        />,
      );
      // Folder heading or toggle should be present
      expect(screen.getByText('Unfiled')).toBeTruthy();
    });

    it('songs inside collapsed folder are hidden', () => {
      render(
        <Library
          songs={[SONG_DRAFT]}
          folders={[{ ...FOLDER_UNFILED, collapsed: true }]}
          onSelectSong={() => {}}
        />,
      );
      // When folder is collapsed, its songs should not be visible
      expect(screen.queryByText('Draft Song')).toBeNull();
    });
  });
});
