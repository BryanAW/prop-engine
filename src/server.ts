import Fastify from 'fastify';
import cors from '@fastify/cors';
import { config } from './config/index.js';

const fastify = Fastify({
  logger:
    config.nodeEnv === 'development'
      ? {
          level: config.logLevel,
          transport: {
            target: 'pino-pretty',
            options: {
              translateTime: 'HH:MM:ss Z',
              ignore: 'pid,hostname',
            },
          },
        }
      : {
          level: config.logLevel,
        },
});

// Health check endpoint
fastify.get('/health', () => {
  return {
    status: 'healthy',
    version: '0.1.0',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  };
});

// Root endpoint
fastify.get('/', () => {
  return {
    name: 'Prop Engine API',
    version: '0.1.0',
    phase: 'Phase 0 - Transparent Baseline',
    docs: 'See README.md for API documentation',
    endpoints: {
      health: 'GET /health',
      markets: 'GET /v1/markets (coming soon)',
      suggest: 'GET /v1/suggest/props (coming soon)',
      batch: 'POST /v1/suggest/batch (coming soon)',
    },
  };
});

// Start server
const start = async () => {
  try {
    // Register plugins
    await fastify.register(cors, {
      origin: true, // Allow all origins for development
    });

    await fastify.listen({
      port: config.port,
      host: config.host,
    });
    fastify.log.info(`🚀 Server running at http://${config.host}:${config.port}`);
    fastify.log.info(`📊 Health check: http://${config.host}:${config.port}/health`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

// Graceful shutdown
const gracefulShutdown = async (signal: string) => {
  fastify.log.info(`\n${signal} received, shutting down gracefully...`);
  await fastify.close();
  process.exit(0);
};

process.on('SIGTERM', () => {
  void gracefulShutdown('SIGTERM');
});
process.on('SIGINT', () => {
  void gracefulShutdown('SIGINT');
});

void start();
