import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    exclude: ['node_modules', 'dist', 'e2e/**'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: ['e2e/**'],
    },
    testTimeout: 20000,
  },
})
