/**
 * Extension configuration
 * API URL can be overridden via environment variable during build
 */

export const config = {
  /**
   * Backend API URL - defaults to localhost for development
   * Set VITE_API_URL environment variable for production builds
   */
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  
  /**
   * Request timeout in milliseconds
   */
  requestTimeout: 30000,
  
  /**
   * Maximum retries for failed requests
   */
  maxRetries: 2,
} as const;

export type Config = typeof config;
