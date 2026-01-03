/**
 * Shared TypeScript types for Hercule
 *
 * IMPORTANT: These types must stay in sync with backend/models.py
 * Any changes here should be reflected in the Pydantic models.
 *
 * @see backend/models.py for the Python equivalents
 */

/**
 * Priority levels for action items
 * Maps to: backend/models.py ActionItem.priority field pattern
 */
export type Priority = 'high' | 'medium' | 'low';

/**
 * Represents a recommended action for the user
 * Maps to: backend/models.py ActionItem class
 */
export interface ActionItem {
  /** Description of the recommended action */
  text: string;
  /** Optional URL for more information or to take action */
  url?: string;
  /** Priority level: high (urgent), medium (recommended), low (optional) */
  priority: Priority;
}

/**
 * Complete analysis result from the backend
 * Maps to: backend/models.py AnalysisResult class
 */
export interface AnalysisResult {
  /** Privacy score from 0-100 (0-49: Red, 50-79: Yellow, 80-100: Green) */
  score: number;
  /** Plain-language summary of the privacy policy */
  summary: string;
  /** List of concerning practices found in the policy */
  red_flags: string[];
  /** Recommended actions for the user */
  user_action_items: ActionItem[];
  /** ISO timestamp when analysis was performed */
  timestamp: string;
  /** URL of the analyzed privacy policy */
  url: string;
}

/**
 * Request payload for the /analyze endpoint
 * Maps to: backend/main.py AnalyzeRequest class
 */
export interface AnalyzeRequest {
  /** The privacy policy text to analyze (required, non-empty) */
  policy_text: string;
  /** URL of the privacy policy page (optional) */
  url?: string;
}

/**
 * Health check response from the backend
 * Maps to: backend/main.py HealthResponse class
 */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  cache_size: number;
  test_mode: boolean;
}
