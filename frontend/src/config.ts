/**
 * Extension configuration
 * API URL is configured via environment variable during build:
 * - Development: defaults to localhost:8000
 * - Production: set VITE_API_URL in .env.production
 */

export const config = {
  /**
   * Backend API URL
   * Set VITE_API_URL environment variable for production builds
   * Example: VITE_API_URL=https://your-function-app.azurewebsites.net
   */
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',

  /**
   * Request timeout in milliseconds
   */
  requestTimeout: 60000,

  /**
   * Maximum retries for failed requests
   */
  maxRetries: 2,
} as const;

export type Config = typeof config;

