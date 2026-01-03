/**
 * Component tests for Summary
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Summary from '../../popup/components/Summary';

describe('Summary', () => {
  describe('Short Summary', () => {
    it('should display the full summary text', () => {
      const shortSummary = 'This is a short privacy policy summary.';
      render(<Summary summary={shortSummary} />);
      expect(screen.getByText(shortSummary)).toBeInTheDocument();
    });

    it('should not show "Read More" button for short text', () => {
      const shortSummary = 'Short summary text.';
      render(<Summary summary={shortSummary} />);
      expect(screen.queryByText('Read More')).not.toBeInTheDocument();
    });
  });

  describe('Long Summary', () => {
    const longSummary = 'A'.repeat(600); // 600 characters

    it('should truncate long summaries', () => {
      render(<Summary summary={longSummary} />);
      // Should show truncated text with ellipsis
      const displayedText = screen.getByText(/A+\.\.\./);
      expect(displayedText).toBeInTheDocument();
    });

    it('should show "Read More" button for long text', () => {
      render(<Summary summary={longSummary} />);
      expect(screen.getByText('Read More')).toBeInTheDocument();
    });

    it('should expand when "Read More" is clicked', () => {
      render(<Summary summary={longSummary} />);
      
      fireEvent.click(screen.getByText('Read More'));
      
      // Full text should be shown (no ellipsis)
      expect(screen.getByText(longSummary)).toBeInTheDocument();
    });

    it('should show "Show Less" after expansion', () => {
      render(<Summary summary={longSummary} />);
      
      fireEvent.click(screen.getByText('Read More'));
      
      expect(screen.getByText('Show Less')).toBeInTheDocument();
    });

    it('should collapse when "Show Less" is clicked', () => {
      render(<Summary summary={longSummary} />);
      
      fireEvent.click(screen.getByText('Read More'));
      fireEvent.click(screen.getByText('Show Less'));
      
      expect(screen.getByText('Read More')).toBeInTheDocument();
    });
  });

  describe('Boundary Cases', () => {
    it('should not truncate exactly 500 character summary', () => {
      const exactSummary = 'A'.repeat(500);
      render(<Summary summary={exactSummary} />);
      expect(screen.queryByText('Read More')).not.toBeInTheDocument();
    });

    it('should truncate 501 character summary', () => {
      const justOverSummary = 'A'.repeat(501);
      render(<Summary summary={justOverSummary} />);
      expect(screen.getByText('Read More')).toBeInTheDocument();
    });

    it('should handle empty summary', () => {
      render(<Summary summary="" />);
      expect(screen.getByText('Summary')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should have proper heading', () => {
      render(<Summary summary="Test" />);
      expect(screen.getByText('Summary')).toHaveClass('text-lg', 'font-semibold');
    });
  });
});
