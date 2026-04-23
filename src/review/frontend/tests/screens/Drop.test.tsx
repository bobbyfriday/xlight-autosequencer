import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Drop } from '../../src/screens/Drop';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('Drop screen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a drop target', () => {
    render(<Drop onSongImported={() => {}} />);
    expect(screen.getByTestId('drop-target')).toBeTruthy();
  });

  it('rejects unsupported extensions pre-flight', async () => {
    render(<Drop onSongImported={() => {}} />);
    const input = screen.getByTestId('file-input') as HTMLInputElement;

    const file = new File(['fake'], 'song.txt', { type: 'text/plain' });
    Object.defineProperty(input, 'files', { value: [file], configurable: true });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeTruthy();
    });
    // fetch not called for unsupported type
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('calls import API on valid file', async () => {
    const songData = {
      song_id: 'abc123',
      title: 'Test',
      status: 'draft',
      duration_ms: 60000,
      folder_id: 'unfiled',
      imported_at: '2026-01-01T00:00:00Z',
      source_paths: [],
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ created: true, song: songData }),
    });

    const onImported = vi.fn();
    render(<Drop onSongImported={onImported} />);
    const input = screen.getByTestId('file-input') as HTMLInputElement;

    const file = new File(['fake'], 'song.mp3', { type: 'audio/mpeg' });
    Object.defineProperty(input, 'files', { value: [file], configurable: true });
    fireEvent.change(input);

    await waitFor(() => {
      // New signature: onSongImported(song, created). Asserting both args
      // here so future callers keep passing `created` through from the
      // server response.
      expect(onImported).toHaveBeenCalledWith(
        expect.objectContaining({ song_id: 'abc123' }),
        true,
      );
    });
  });
});
