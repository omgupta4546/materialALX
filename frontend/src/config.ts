/**
 * Frontend Configuration Module
 * 
 * Centralized configuration loader for the React SPA.
 * Uses Vite's import.meta.env to inject environment variables at build time.
 */

export const config = {
  /** 
   * Base URL for the backend API.
   * Maps to API_BASE_URL via Vite config or VITE_ prefix.
   */
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  
  /** Current environment (development, production, test) */
  environment: import.meta.env.MODE || 'development',
  
  /** Storage backend strategy */
  storageBackend: import.meta.env.VITE_STORAGE_BACKEND || 'local',
};

// Developer warnings for misconfiguration
if (!config.apiBaseUrl) {
  console.warn('Configuration Warning: API_BASE_URL is not set. API calls will likely fail.');
}
