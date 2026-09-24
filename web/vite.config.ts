/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': new URL('./src', import.meta.url).pathname },
  },
  build: {
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('three') || id.includes('@react-three')) return 'webgl';
            if (id.includes('d3') || id.includes('recharts')) return 'charts';
            if (id.includes('framer-motion')) return 'motion';
            return 'vendor';
          }
        },
      },
    },
    // three.js is the only chunk over this, and it is lazy-loaded with the
    // globe rather than shipped on first paint.
    chunkSizeWarningLimit: 1000,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    coverage: { provider: 'v8', include: ['src/models/**'] },
  },
});
