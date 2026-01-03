/**
 * Component tests for RedFlags
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RedFlags from '../../popup/components/RedFlags';

describe('RedFlags', () => {
  describe('No Red Flags', () => {
    it('should show positive message when no red flags', () => {
      render(<RedFlags redFlags={[]} />);
      expect(screen.getByText('✓ No major concerns identified')).toBeInTheDocument();
    });

    it('should have green styling when no red flags', () => {
      const { container } = render(<RedFlags redFlags={[]} />);
      expect(container.querySelector('.bg-green-50')).toBeInTheDocument();
    });
  });

  describe('With Red Flags', () => {
    const sampleFlags = ['Flag 1', 'Flag 2', 'Flag 3'];

    it('should display all red flags', () => {
      render(<RedFlags redFlags={sampleFlags} />);
      expect(screen.getByText(/Flag 1/)).toBeInTheDocument();
      expect(screen.getByText(/Flag 2/)).toBeInTheDocument();
      expect(screen.getByText(/Flag 3/)).toBeInTheDocument();
    });

    it('should show warning icons', () => {
      render(<RedFlags redFlags={sampleFlags} />);
      const warnings = screen.getAllByText(/⚠️/);
      expect(warnings).toHaveLength(3);
    });

    it('should have red styling when flags exist', () => {
      const { container } = render(<RedFlags redFlags={sampleFlags} />);
      expect(container.querySelector('.bg-red-50')).toBeInTheDocument();
    });
  });

  describe('Expansion Behavior', () => {
    const manyFlags = Array.from({ length: 8 }, (_, i) => `Red Flag ${i + 1}`);

    it('should show only first 5 flags initially', () => {
      render(<RedFlags redFlags={manyFlags} />);
      expect(screen.getByText(/Red Flag 1/)).toBeInTheDocument();
      expect(screen.getByText(/Red Flag 5/)).toBeInTheDocument();
      expect(screen.queryByText(/Red Flag 6/)).not.toBeInTheDocument();
    });

    it('should show "Show More" button when more than 5 flags', () => {
      render(<RedFlags redFlags={manyFlags} />);
      expect(screen.getByText('Show More (3 more)')).toBeInTheDocument();
    });

    it('should expand to show all flags when button clicked', () => {
      render(<RedFlags redFlags={manyFlags} />);

      fireEvent.click(screen.getByText('Show More (3 more)'));

      expect(screen.getByText(/Red Flag 6/)).toBeInTheDocument();
      expect(screen.getByText(/Red Flag 8/)).toBeInTheDocument();
    });

    it('should show "Show Less" after expansion', () => {
      render(<RedFlags redFlags={manyFlags} />);

      fireEvent.click(screen.getByText('Show More (3 more)'));

      expect(screen.getByText('Show Less')).toBeInTheDocument();
    });

    it('should collapse when "Show Less" is clicked', () => {
      render(<RedFlags redFlags={manyFlags} />);

      fireEvent.click(screen.getByText('Show More (3 more)'));
      fireEvent.click(screen.getByText('Show Less'));

      expect(screen.queryByText(/Red Flag 6/)).not.toBeInTheDocument();
    });

    it('should not show expansion button for 5 or fewer flags', () => {
      const fiveFlags = Array.from({ length: 5 }, (_, i) => `Flag ${i + 1}`);
      render(<RedFlags redFlags={fiveFlags} />);

      expect(screen.queryByText(/Show More/)).not.toBeInTheDocument();
    });
  });
});
