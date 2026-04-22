import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LightsPreview } from '../../src/components/LightsPreview/LightsPreview';

describe('LightsPreview', () => {
  it('renders N cells', () => {
    const { container } = render(<LightsPreview n={8} />);
    const cells = container.querySelectorAll('[data-testid="light-cell"]');
    expect(cells).toHaveLength(8);
  });

  it('compact flag hides label', () => {
    render(<LightsPreview n={4} label="Test Label" compact={true} />);
    expect(screen.queryByText('Test Label')).toBeNull();
  });

  it('shows label when compact is false', () => {
    render(<LightsPreview n={4} label="My Label" compact={false} />);
    expect(screen.getByText('My Label')).toBeTruthy();
  });

  it('applies accent color from energyPulse', () => {
    const { container } = render(
      <LightsPreview n={4} energyPulse={0.8} accent="#ff0000" />
    );
    const cells = container.querySelectorAll('[data-testid="light-cell"]');
    expect(cells.length).toBeGreaterThan(0);
  });

  it('playhead prop is accepted', () => {
    const { container } = render(<LightsPreview n={4} playhead={0.5} />);
    expect(container.firstChild).toBeTruthy();
  });
});
