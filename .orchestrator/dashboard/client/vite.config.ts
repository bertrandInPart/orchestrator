import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Dashboard API is served by the Express backend (server/index.js on
      // DASHBOARD_PORT, default 4000). Proxying here lets the client always
      // call same-origin "/api/..." during `npm run dev`.
      '/api': {
        target: `http://localhost:${process.env.DASHBOARD_PORT ?? 4000}`,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    css: false,
    setupFiles: ['./src/test-setup.ts'],
  },
})
