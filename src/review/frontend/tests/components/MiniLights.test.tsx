import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { MiniLights } from '../../src/components/MiniLights/MiniLights';

describe('MiniLights', () => {
  it('renders without crashing', () => {
    const { container } = render(<MiniLights themeId="peak-flash" kind="chorus" />);
    expect(container.firstChild).toBeTruthy();
  });

  it('renders cells keyed on themeId + kind', () => {
    const { container: c1 } = render(<MiniLights themeId="peak-flash" kind="chorus" />);
    const { container: c2 } = render(<MiniLights themeId="shimmer-wash" kind="intro" />);
    // Both render cells but different themes may have different colors
    const cells1 = c1.querySelectorAll('[data-testid="mini-light"]');
    const cells2 = c2.querySelectorAll('[data-testid="mini-light"]');
    expect(cells1.length).toBeGreaterThan(0);
    expect(cells2.length).toBeGreaterThan(0);
  });

  it('same themeId + kind produces same output', () => {
    const { container: c1 } = render(<MiniLights themeId="driving-pulse" kind="verse" />);
    const { container: c2 } = render(<MiniLights themeId="driving-pulse" kind="verse" />);
    expect(c1.innerHTML).toBe(c2.innerHTML);
  });

  it('accepts swatches prop', () => {
    const { container } = render(
      <MiniLights themeId="test" kind="unknown" swatches={['#ff0000', '#00ff00', '#0000ff', '#ffffff']} />
    );
    expect(container.firstChild).toBeTruthy();
  });
});
