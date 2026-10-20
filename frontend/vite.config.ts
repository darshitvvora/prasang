/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { profileMeta } from './vite-plugins/profileMeta.ts'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:3001'
  return {
    plugins: [react(), profileMeta(apiTarget)],
    server: {
      // Dev: /api goes to Mockoon (:3001) or the FastAPI backend (:8000) — set VITE_API_PROXY_TARGET.
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
      },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts', 'vite-plugins/**/*.test.ts'],
    },
  }
})
