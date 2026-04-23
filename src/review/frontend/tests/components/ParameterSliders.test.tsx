import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ParameterSliders } from '../../src/components/ParameterSliders/ParameterSliders';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const defaultOverrides = {
  brightness: 1.0,
  hit_strength: 1.0,
  dwell_time: 1.0,
  color_shift: 0.0,
};

describe('ParameterSliders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders four labeled sliders', () => {
    render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={defaultOverrides}
        onOverridesChange={() => {}}
      />
    );
    expect(screen.getByText('Brightness')).toBeTruthy();
    expect(screen.getByText('Hit Strength')).toBeTruthy();
    expect(screen.getByText('Dwell Time')).toBeTruthy();
    expect(screen.getByText('Color Shift')).toBeTruthy();
  });

  it('renders sliders with correct initial values', () => {
    render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={{ brightness: 0.5, hit_strength: 1.2, dwell_time: 1.0, color_shift: 0.3 }}
        onOverridesChange={() => {}}
      />
    );
    const sliders = screen.getAllByRole('slider');
    expect(sliders).toHaveLength(4);
    // jsdom returns slider value as string
    expect((sliders[0] as HTMLInputElement).value).toBe('0.5');   // brightness
    expect((sliders[1] as HTMLInputElement).value).toBe('1.2');   // hit_strength
    expect((sliders[2] as HTMLInputElement).value).toBe('1');     // dwell_time (1.0 → '1')
    expect((sliders[3] as HTMLInputElement).value).toBe('0.3');   // color_shift
  });

  it('brightness slider has range 0..2', () => {
    render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={defaultOverrides}
        onOverridesChange={() => {}}
      />
    );
    const sliders = screen.getAllByRole('slider');
    expect(sliders[0]).toHaveAttribute('min', '0');
    expect(sliders[0]).toHaveAttribute('max', '2');
  });

  it('color_shift slider has range 0..1', () => {
    render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={defaultOverrides}
        onOverridesChange={() => {}}
      />
    );
    const sliders = screen.getAllByRole('slider');
    expect(sliders[3]).toHaveAttribute('min', '0');
    expect(sliders[3]).toHaveAttribute('max', '1');
  });

  it('calls onOverridesChange immediately when slider changes', () => {
    const onOverridesChange = vi.fn();
    render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={defaultOverrides}
        onOverridesChange={onOverridesChange}
      />
    );
    const sliders = screen.getAllByRole('slider');
    fireEvent.change(sliders[0], { target: { value: '0.5' } });
    expect(onOverridesChange).toHaveBeenCalledWith(
      expect.objectContaining({ brightness: 0.5 })
    );
  });

  it('fires debounced PUT after 300ms on slider change', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ assignment: { section_index: 0, theme_id: 'shimmer-wash', overrides: { brightness: 0.5, hit_strength: 1.0, dwell_time: 1.0, color_shift: 0.0 }, user_confirmed: true } }),
    });

    render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={defaultOverrides}
        onOverridesChange={() => {}}
      />
    );

    const sliders = screen.getAllByRole('slider');
    fireEvent.change(sliders[0], { target: { value: '0.5' } });

    // Before debounce fires — no fetch yet
    expect(mockFetch).not.toHaveBeenCalled();

    // Advance timers past debounce
    act(() => {
      vi.advanceTimersByTime(350);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/songs/song1/assignments/0',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );

    // Verify the body includes the updated override
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.overrides.brightness).toBe(0.5);
  });

  it('resets to defaults when themeId prop changes', async () => {
    const onOverridesChange = vi.fn();
    const { rerender } = render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={{ brightness: 0.3, hit_strength: 0.5, dwell_time: 1.5, color_shift: 0.8 }}
        onOverridesChange={onOverridesChange}
      />
    );

    // Change theme — parent passes new themeId + default overrides (as per FR-032a backend reset)
    rerender(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="peak-flash"
        overrides={{ brightness: 1.0, hit_strength: 1.0, dwell_time: 1.0, color_shift: 0.0 }}
        onOverridesChange={onOverridesChange}
      />
    );

    const sliders = screen.getAllByRole('slider');
    expect((sliders[0] as HTMLInputElement).value).toBe('1');  // brightness reset
    expect((sliders[1] as HTMLInputElement).value).toBe('1');  // hit_strength reset
    expect((sliders[2] as HTMLInputElement).value).toBe('1');  // dwell_time reset
    expect((sliders[3] as HTMLInputElement).value).toBe('0');  // color_shift reset
  });

  it('shows numeric value next to each slider', () => {
    render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={{ brightness: 0.75, hit_strength: 1.0, dwell_time: 1.0, color_shift: 0.0 }}
        onOverridesChange={() => {}}
      />
    );
    expect(screen.getByText('0.75')).toBeTruthy();
  });

  it('does not fire PUT when themeId changes (FR-032a — server handles reset)', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ assignment: {} }),
    });

    const { rerender } = render(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="shimmer-wash"
        overrides={defaultOverrides}
        onOverridesChange={() => {}}
      />
    );

    rerender(
      <ParameterSliders
        songId="song1"
        sectionIdx={0}
        themeId="peak-flash"
        overrides={{ brightness: 1.0, hit_strength: 1.0, dwell_time: 1.0, color_shift: 0.0 }}
        onOverridesChange={() => {}}
      />
    );

    act(() => {
      vi.advanceTimersByTime(500);
    });

    // No PUT should fire just because themeId changed
    expect(mockFetch).not.toHaveBeenCalled();
  });
});
