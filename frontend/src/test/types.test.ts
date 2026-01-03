/**
 * Type validation tests for shared types
 * Ensures type contracts are correct and type guards work properly
 */
import { describe, it, expect } from 'vitest';
import type { 
  ActionItem, 
  AnalysisResult, 
  AnalyzeRequest, 
  HealthResponse, 
  Priority 
} from '../../../shared/types';

// Type guard functions for runtime validation
function isValidPriority(value: unknown): value is Priority {
  return typeof value === 'string' && ['high', 'medium', 'low'].includes(value);
}

function isValidActionItem(obj: unknown): obj is ActionItem {
  if (typeof obj !== 'object' || obj === null) return false;
  const item = obj as Record<string, unknown>;
  return (
    typeof item.text === 'string' &&
    (item.url === undefined || typeof item.url === 'string') &&
    isValidPriority(item.priority)
  );
}

function isValidAnalysisResult(obj: unknown): obj is AnalysisResult {
  if (typeof obj !== 'object' || obj === null) return false;
  const result = obj as Record<string, unknown>;
  return (
    typeof result.score === 'number' &&
    result.score >= 0 &&
    result.score <= 100 &&
    typeof result.summary === 'string' &&
    Array.isArray(result.red_flags) &&
    result.red_flags.every((flag: unknown) => typeof flag === 'string') &&
    Array.isArray(result.user_action_items) &&
    result.user_action_items.every(isValidActionItem) &&
    typeof result.timestamp === 'string' &&
    typeof result.url === 'string'
  );
}

function isValidAnalyzeRequest(obj: unknown): obj is AnalyzeRequest {
  if (typeof obj !== 'object' || obj === null) return false;
  const request = obj as Record<string, unknown>;
  return (
    typeof request.policy_text === 'string' &&
    request.policy_text.trim().length > 0 &&
    (request.url === undefined || typeof request.url === 'string')
  );
}

function isValidHealthResponse(obj: unknown): obj is HealthResponse {
  if (typeof obj !== 'object' || obj === null) return false;
  const response = obj as Record<string, unknown>;
  return (
    (response.status === 'healthy' || response.status === 'unhealthy') &&
    typeof response.timestamp === 'string' &&
    typeof response.cache_size === 'number' &&
    typeof response.test_mode === 'boolean'
  );
}

describe('Type Guards', () => {
  describe('isValidPriority', () => {
    it('should accept valid priorities', () => {
      expect(isValidPriority('high')).toBe(true);
      expect(isValidPriority('medium')).toBe(true);
      expect(isValidPriority('low')).toBe(true);
    });

    it('should reject invalid priorities', () => {
      expect(isValidPriority('invalid')).toBe(false);
      expect(isValidPriority('')).toBe(false);
      expect(isValidPriority(null)).toBe(false);
      expect(isValidPriority(undefined)).toBe(false);
      expect(isValidPriority(123)).toBe(false);
    });
  });

  describe('isValidActionItem', () => {
    it('should accept valid action items', () => {
      const validItem: ActionItem = {
        text: 'Review settings',
        priority: 'high',
      };
      expect(isValidActionItem(validItem)).toBe(true);
    });

    it('should accept action items with optional url', () => {
      const itemWithUrl: ActionItem = {
        text: 'Review settings',
        url: 'https://example.com',
        priority: 'medium',
      };
      expect(isValidActionItem(itemWithUrl)).toBe(true);
    });

    it('should reject invalid action items', () => {
      expect(isValidActionItem(null)).toBe(false);
      expect(isValidActionItem({})).toBe(false);
      expect(isValidActionItem({ text: 'Test' })).toBe(false); // missing priority
      expect(isValidActionItem({ text: 123, priority: 'high' })).toBe(false);
    });
  });

  describe('isValidAnalysisResult', () => {
    it('should accept valid analysis results', () => {
      const validResult: AnalysisResult = {
        score: 75,
        summary: 'Test summary',
        red_flags: ['Flag 1', 'Flag 2'],
        user_action_items: [
          { text: 'Action 1', priority: 'high' },
        ],
        timestamp: '2026-01-01T00:00:00Z',
        url: 'https://example.com/privacy',
      };
      expect(isValidAnalysisResult(validResult)).toBe(true);
    });

    it('should reject invalid scores', () => {
      const invalidScore = {
        score: 150, // out of range
        summary: 'Test',
        red_flags: [],
        user_action_items: [],
        timestamp: '2026-01-01T00:00:00Z',
        url: '',
      };
      expect(isValidAnalysisResult(invalidScore)).toBe(false);
    });

    it('should reject negative scores', () => {
      const negativeScore = {
        score: -10,
        summary: 'Test',
        red_flags: [],
        user_action_items: [],
        timestamp: '2026-01-01T00:00:00Z',
        url: '',
      };
      expect(isValidAnalysisResult(negativeScore)).toBe(false);
    });
  });

  describe('isValidAnalyzeRequest', () => {
    it('should accept valid requests', () => {
      const validRequest: AnalyzeRequest = {
        policy_text: 'This is a privacy policy...',
        url: 'https://example.com',
      };
      expect(isValidAnalyzeRequest(validRequest)).toBe(true);
    });

    it('should accept requests without url', () => {
      const requestWithoutUrl: AnalyzeRequest = {
        policy_text: 'This is a privacy policy...',
      };
      expect(isValidAnalyzeRequest(requestWithoutUrl)).toBe(true);
    });

    it('should reject empty policy_text', () => {
      expect(isValidAnalyzeRequest({ policy_text: '' })).toBe(false);
      expect(isValidAnalyzeRequest({ policy_text: '   ' })).toBe(false);
    });
  });

  describe('isValidHealthResponse', () => {
    it('should accept valid health responses', () => {
      const validResponse: HealthResponse = {
        status: 'healthy',
        timestamp: '2026-01-01T00:00:00Z',
        cache_size: 10,
        test_mode: false,
      };
      expect(isValidHealthResponse(validResponse)).toBe(true);
    });

    it('should reject invalid status', () => {
      const invalidStatus = {
        status: 'unknown',
        timestamp: '2026-01-01T00:00:00Z',
        cache_size: 0,
        test_mode: true,
      };
      expect(isValidHealthResponse(invalidStatus)).toBe(false);
    });
  });
});

// Export type guards for use in application
export {
  isValidPriority,
  isValidActionItem,
  isValidAnalysisResult,
  isValidAnalyzeRequest,
  isValidHealthResponse,
};
