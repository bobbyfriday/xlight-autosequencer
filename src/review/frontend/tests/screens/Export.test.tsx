import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Export } from '../../src/screens/Export';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const song = {
  song_id: 'abc123',
  title: 'Test Song',
  status: 'themed',
  duration_ms: 60000,
};

describe('Export screen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows layout-required block when no layout', () => {
    render(<Export song={song} layoutId={null} />);
    expect(screen.getByTestId('layout-required')).toBeTruthy();
  });

  it('shows export form when layout is present', () => {
    render(<Export song={song} layoutId="layout_abc123" />);
    expect(screen.queryByTestId('layout-required')).toBeNull();
    expect(screen.getByTestId('export-form')).toBeTruthy();
  });

  it('render button triggers export API', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ export_id: 'exp_1', started_at: '2026-01-01T00:00:00Z' }),
    });

    render(<Export song={song} layoutId="layout_abc123" />);
    const btn = screen.getByRole('button', { name: /render/i });
    btn.click();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/export'),
        expect.any(Object),
      );
    });
  });

  it('shows incomplete_theming message when not themed', () => {
    render(<Export song={{ ...song, status: 'analyzed' }} layoutId="layout_abc123" />);
    expect(screen.getByTestId('incomplete-theming')).toBeTruthy();
  });
});
