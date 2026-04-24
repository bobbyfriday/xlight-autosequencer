/** Tests for the analyze-screen MetadataBanner:
 * - renders editable artist/title pre-filled from props
 * - PATCH on blur with the right body shape
 * - shows Genius match with link
 * - shows reject reason when Genius was rejected
 * - flags artist mismatch when Genius returned a different artist
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MetadataBanner } from '../../src/screens/MetadataBanner';

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('MetadataBanner', () => {
  it('pre-fills artist + title from props (override wins over ID3)', () => {
    render(
      <MetadataBanner
        songId="x"
        id3Artist="Wrong Artist"
        id3Title="The Title"
        overrideArtist="Correct Artist"
        overrideTitle={null}
        genius={null}
        onSaved={() => {}}
      />
    );
    expect((screen.getByTestId('metadata-artist') as HTMLInputElement).value).toBe('Correct Artist');
    // title falls back to ID3 since no override title was set
    expect((screen.getByTestId('metadata-title') as HTMLInputElement).value).toBe('The Title');
  });

  it('PATCHes /metadata on blur with only the changed field', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ song_id: 'x', override_artist: 'New', override_title: null }),
    });
    vi.stubGlobal('fetch', fetchSpy as unknown as typeof fetch);

    const onSaved = vi.fn();
    render(
      <MetadataBanner
        songId="song_abc"
        id3Artist="Old"
        id3Title="T"
        overrideArtist={null}
        overrideTitle={null}
        genius={null}
        onSaved={onSaved}
      />
    );
    const artistInput = screen.getByTestId('metadata-artist') as HTMLInputElement;
    fireEvent.change(artistInput, { target: { value: 'New' } });
    fireEvent.blur(artistInput);

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const [url, opts] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/songs/song_abc/metadata');
    expect(opts.method).toBe('PATCH');
    expect(JSON.parse(String(opts.body))).toEqual({ artist: 'New' });
    await waitFor(() =>
      expect(onSaved).toHaveBeenCalledWith({ override_artist: 'New', override_title: null })
    );
  });

  it('no PATCH when nothing changed', () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy as unknown as typeof fetch);
    render(
      <MetadataBanner
        songId="x"
        id3Artist="A"
        id3Title="T"
        overrideArtist={null}
        overrideTitle={null}
        genius={null}
        onSaved={() => {}}
      />
    );
    fireEvent.blur(screen.getByTestId('metadata-artist'));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('empty string blur clears the override (sends field:"")', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ song_id: 'x' }),
    });
    vi.stubGlobal('fetch', fetchSpy as unknown as typeof fetch);
    render(
      <MetadataBanner
        songId="x"
        id3Artist="A"
        id3Title="T"
        overrideArtist="Override"
        overrideTitle={null}
        genius={null}
        onSaved={() => {}}
      />
    );
    const artistInput = screen.getByTestId('metadata-artist') as HTMLInputElement;
    fireEvent.change(artistInput, { target: { value: '' } });
    fireEvent.blur(artistInput);
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const [, opts] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(opts.body))).toEqual({ artist: '' });
  });

  it('renders the Genius match with a link', () => {
    render(
      <MetadataBanner
        songId="x"
        id3Artist="Mariah Carey"
        id3Title="All I Want"
        overrideArtist={null}
        overrideTitle={null}
        genius={{
          section_source: 'genius',
          match: {
            url: 'https://genius.com/example',
            artist: 'Mariah Carey',
            title: 'All I Want for Christmas Is You',
          },
          reject_reason: null,
        }}
        onSaved={() => {}}
      />
    );
    const row = screen.getByTestId('genius-match-row');
    expect(row).toBeDefined();
    const link = row.querySelector('a')!;
    expect(link.getAttribute('href')).toBe('https://genius.com/example');
    expect(link.textContent).toContain('Mariah Carey');
  });

  it('shows the reject reason when Genius was rejected', () => {
    render(
      <MetadataBanner
        songId="x"
        id3Artist="Unknown"
        id3Title="Title"
        overrideArtist={null}
        overrideTitle={null}
        genius={{
          section_source: 'heuristic',
          match: {
            url: 'https://genius.com/wrong',
            artist: 'Wrong Artist',
            title: 'Wrong Title',
          },
          reject_reason: 'one section covers 75% of the song — likely a wrong-song match',
        }}
        onSaved={() => {}}
      />
    );
    const row = screen.getByTestId('genius-reject-reason');
    expect(row.textContent).toContain('75%');
    expect(row.textContent).toContain('wrong-song match');
  });

  it('flags artist mismatch when Genius returned a different artist', () => {
    render(
      <MetadataBanner
        songId="x"
        id3Artist="Mariah Carey"
        id3Title="All I Want"
        overrideArtist={null}
        overrideTitle={null}
        genius={{
          section_source: 'heuristic',
          match: {
            url: 'https://genius.com/catie',
            artist: 'Catie Curtis',
            title: 'All I Want for Christmas Is You',
          },
          reject_reason: 'only 2 sections for a 241s song',
        }}
        onSaved={() => {}}
      />
    );
    expect(screen.getByTestId('genius-match-mismatch')).toBeDefined();
  });
});
