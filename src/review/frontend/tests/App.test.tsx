import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import App from '../src/App';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Minimal mocks for child screens to keep tests fast
vi.mock('../src/screens/Drop', () => ({
  Drop: ({ onSongImported }: { onSongImported: (song: unknown) => void }) => (
    <div data-testid="drop-screen">
      <button
        onClick={() =>
          onSongImported({
            song_id: 'abc123',
            title: 'Test Song',
            status: 'imported',
            duration_ms: 60000,
            folder_id: 'f1',
            imported_at: '2026-01-01T00:00:00Z',
            source_paths: ['/tmp/test.mp3'],
          })
        }
      >
        Import
      </button>
    </div>
  ),
}));

vi.mock('../src/screens/Analyze', () => ({
  Analyze: ({ onComplete }: { onComplete: () => void }) => (
    <div data-testid="analyze-screen">
      <button onClick={onComplete}>Review Timeline →</button>
    </div>
  ),
}));

vi.mock('../src/screens/Timeline', () => ({
  Timeline: ({ onNavigateTheme }: { onNavigateTheme?: () => void }) => (
    <div data-testid="timeline-screen">
      {onNavigateTheme && <button onClick={onNavigateTheme}>Go to Theme →</button>}
    </div>
  ),
}));

vi.mock('../src/screens/Theme', () => ({
  Theme: ({ onThemed }: { onThemed: () => void }) => (
    <div data-testid="theme-screen">
      <button onClick={onThemed}>Accept All</button>
    </div>
  ),
}));

vi.mock('../src/screens/Export', () => ({
  Export: () => <div data-testid="export-screen" />,
}));

vi.mock('../src/components/Chrome/Chrome', () => ({
  Chrome: ({
    activeScreen,
    onNavigate,
    children,
  }: {
    activeScreen: string;
    onNavigate?: (s: string) => void;
    children: React.ReactNode;
  }) => (
    <div data-testid="chrome" data-active-screen={activeScreen}>
      <nav>
        {['library', 'drop', 'analyze', 'timeline', 'theme', 'export'].map((s) => (
          <button key={s} onClick={() => onNavigate?.(s as never)}>
            {s}
          </button>
        ))}
      </nav>
      {children}
    </div>
  ),
}));

import React from 'react';

const song = {
  song_id: 'abc123',
  title: 'Test Song',
  status: 'imported',
  duration_ms: 60000,
  folder_id: 'f1',
  imported_at: '2026-01-01T00:00:00Z',
  source_paths: ['/tmp/test.mp3'],
};

const analysis = {
  song_id: 'abc123',
  detected_sections: [{ index: 0, start_ms: 0, end_ms: 60000, kind: 'verse', label: 'Verse 1' }],
  peaks: [],
  beats: [],
  detectors: [],
  completed_at: '2026-01-01T00:01:00Z',
};

describe('App router (T086)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default fetch stubs for mount-time calls
    mockFetch.mockResolvedValue({
      ok: false,
      json: async () => ({}),
    });
  });

  it('renders Chrome wrapper with app-root', async () => {
    render(<App />);
    expect(screen.getByTestId('app-root')).toBeTruthy();
    expect(screen.getByTestId('chrome')).toBeTruthy();
  });

  it('starts on library screen', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('chrome').getAttribute('data-active-screen')).toBe('library');
    });
  });

  it('navigates to drop screen via nav', async () => {
    render(<App />);
    const dropBtn = screen.getByRole('button', { name: 'drop' });
    act(() => { dropBtn.click(); });
    await waitFor(() => {
      expect(screen.getByTestId('drop-screen')).toBeTruthy();
    });
  });
});

describe('App auto-advance (T087)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: false,
      json: async () => ({}),
    });
  });

  it('advances DROP → ANALYZE after successful import', async () => {
    render(<App />);

    // Navigate to drop
    act(() => { screen.getByRole('button', { name: 'drop' }).click(); });
    expect(screen.getByTestId('drop-screen')).toBeTruthy();

    // Simulate import success
    act(() => { screen.getByRole('button', { name: 'Import' }).click(); });

    await waitFor(() => {
      expect(screen.getByTestId('analyze-screen')).toBeTruthy();
    });
  });

  it('advances ANALYZE → TIMELINE after analysis complete', async () => {
    // Set up fetch to return analysis and assignments when Analyze calls onComplete
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/analysis')) {
        return Promise.resolve({ ok: true, json: async () => analysis });
      }
      if (url.includes('/assignments')) {
        return Promise.resolve({ ok: true, json: async () => ({ assignments: [] }) });
      }
      return Promise.resolve({ ok: false, json: async () => ({}) });
    });

    render(<App />);

    // Navigate to drop, import song
    act(() => { screen.getByRole('button', { name: 'drop' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Import' }).click(); });

    await waitFor(() => expect(screen.getByTestId('analyze-screen')).toBeTruthy());

    // Click "Review Timeline →"
    await act(async () => {
      screen.getByRole('button', { name: 'Review Timeline →' }).click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('timeline-screen')).toBeTruthy();
    });
  });

  it('navigates TIMELINE → THEME via Go to Theme button', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/analysis')) {
        return Promise.resolve({ ok: true, json: async () => analysis });
      }
      if (url.includes('/assignments')) {
        return Promise.resolve({ ok: true, json: async () => ({ assignments: [] }) });
      }
      return Promise.resolve({ ok: false, json: async () => ({}) });
    });

    render(<App />);

    // Fast path to timeline: drop → import → analyze complete
    act(() => { screen.getByRole('button', { name: 'drop' }).click(); });
    act(() => { screen.getByRole('button', { name: 'Import' }).click(); });
    await waitFor(() => expect(screen.getByTestId('analyze-screen')).toBeTruthy());

    await act(async () => {
      screen.getByRole('button', { name: 'Review Timeline →' }).click();
    });
    await waitFor(() => expect(screen.getByTestId('timeline-screen')).toBeTruthy());

    // Navigate to theme
    act(() => { screen.getByRole('button', { name: 'Go to Theme →' }).click(); });
    await waitFor(() => {
      expect(screen.getByTestId('theme-screen')).toBeTruthy();
    });
  });
});
