import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Test environment
    environment: 'node',

    // Coverage
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'dist/**',
        'tests/fixtures/**',
        '**/*.config.{js,ts}',
        '**/types/**',
      ],
      all: true,
      lines: 80,
      functions: 80,
      branches: 80,
      statements: 80,
    },

    // File patterns
    include: ['tests/**/*.test.ts'],
    exclude: ['node_modules', 'dist'],

    // Globals (optional - can use import { describe, it } instead)
    globals: true,

    // Timeouts
    testTimeout: 10000,
    hookTimeout: 10000,
  },
});
