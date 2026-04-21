import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Chrome } from 'src/components/Chrome/Chrome';

describe('Chrome', () => {
  it('renders the wordmark', () => {
    render(<Chrome activeScreen="library"><div /></Chrome>);
    expect(screen.getByText(/xonset/i)).toBeTruthy();
  });

  it('tool strip highlights active tab with accent underline', () => {
    render(<Chrome activeScreen="timeline"><div /></Chrome>);
    const tab = screen.getByRole('tab', { name: /timeline/i });
    expect(tab).toHaveAttribute('data-active', 'true');
  });

  it('renders children inside content area', () => {
    render(
      <Chrome activeScreen="library">
        <div data-testid="child-content">child</div>
      </Chrome>,
    );
    expect(screen.getByTestId('child-content')).toBeTruthy();
  });
});
