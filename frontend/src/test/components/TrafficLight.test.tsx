/**
 * Component tests for TrafficLight
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TrafficLight from '../../popup/components/TrafficLight';

describe('TrafficLight', () => {
  describe('Score Display', () => {
    it('should display the score value', () => {
      render(<TrafficLight score={75} />);
      expect(screen.getAllByText('75')).toHaveLength(2); // Shows in circle and text
    });

    it('should display "out of 100" label', () => {
      render(<TrafficLight score={50} />);
      expect(screen.getByText('out of 100')).toBeInTheDocument();
    });
  });

  describe('Color Thresholds', () => {
    it('should show green for scores >= 80', () => {
      const { container } = render(<TrafficLight score={80} />);
      const indicator = container.querySelector('.bg-green-500');
      expect(indicator).toBeInTheDocument();
    });

    it('should show green for score 100', () => {
      const { container } = render(<TrafficLight score={100} />);
      const indicator = container.querySelector('.bg-green-500');
      expect(indicator).toBeInTheDocument();
    });

    it('should show yellow for scores 50-79', () => {
      const { container } = render(<TrafficLight score={65} />);
      const indicator = container.querySelector('.bg-yellow-400');
      expect(indicator).toBeInTheDocument();
    });

    it('should show yellow at boundary (score 50)', () => {
      const { container } = render(<TrafficLight score={50} />);
      const indicator = container.querySelector('.bg-yellow-400');
      expect(indicator).toBeInTheDocument();
    });

    it('should show yellow at upper boundary (score 79)', () => {
      const { container } = render(<TrafficLight score={79} />);
      const indicator = container.querySelector('.bg-yellow-400');
      expect(indicator).toBeInTheDocument();
    });

    it('should show red for scores < 50', () => {
      const { container } = render(<TrafficLight score={30} />);
      const indicator = container.querySelector('.bg-red-500');
      expect(indicator).toBeInTheDocument();
    });

    it('should show red for score 0', () => {
      const { container } = render(<TrafficLight score={0} />);
      const indicator = container.querySelector('.bg-red-500');
      expect(indicator).toBeInTheDocument();
    });

    it('should show red at boundary (score 49)', () => {
      const { container } = render(<TrafficLight score={49} />);
      const indicator = container.querySelector('.bg-red-500');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label with score information', () => {
      render(<TrafficLight score={85} />);
      const indicator = screen.getByLabelText('Privacy score: 85 out of 100');
      expect(indicator).toBeInTheDocument();
    });
  });
});
