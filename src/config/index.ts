import dotenv from 'dotenv';

// Load environment variables from .env file
dotenv.config();

/**
 * Centralized configuration loaded from environment variables.
 * All values have sensible defaults for development.
 */
export const config = {
  // Server
  nodeEnv: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT || '3000', 10),
  host: process.env.HOST || '0.0.0.0',

  // API Keys (optional in Phase 0)
  apiBasketball: {
    key: process.env.API_BASKETBALL_KEY || '',
    host: process.env.API_BASKETBALL_HOST || 'api-basketball-v1.p.rapidapi.com',
  },
  oddsApi: {
    key: process.env.ODDS_API_KEY || '',
  },

  // Feature flags
  useExternalApis: process.env.USE_EXTERNAL_APIS === 'true',
  cacheTtlSeconds: parseInt(process.env.CACHE_TTL_SECONDS || '300', 10),

  // Logging
  logLevel: (process.env.LOG_LEVEL || 'info') as 'debug' | 'info' | 'warn' | 'error',
  logFormat: (process.env.LOG_FORMAT || 'json') as 'json' | 'pretty',
} as const;

/**
 * Validate required configuration for production.
 * In Phase 0, API keys are optional (we use fixtures).
 */
export const validateConfig = () => {
  if (config.nodeEnv === 'production' && config.useExternalApis) {
    const missing: string[] = [];

    if (!config.apiBasketball.key) missing.push('API_BASKETBALL_KEY');
    if (!config.oddsApi.key) missing.push('ODDS_API_KEY');

    if (missing.length > 0) {
      throw new Error(
        `Missing required environment variables for production: ${missing.join(', ')}`
      );
    }
  }
};

// Validate on import
validateConfig();
