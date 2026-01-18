/**
 * Extension configuration
 * API URL is configured via environment variable during build:
 * - Development: set VITE_API_URL=http://localhost:8000 in .env.development
 * - Production: defaults to Render deployment
 */

export const config = {
  /**
   * Backend API URL
   * Set VITE_API_URL environment variable to override
   * Production: https://hercule.onrender.com
   * Development: http://localhost:8000
   */
  apiUrl: import.meta.env.VITE_API_URL || 'https://hercule.onrender.com',

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

