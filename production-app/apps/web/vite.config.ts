import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  return {
    // The hosted demo lives below /pimascor/demo/. Keeping this configurable
    // also lets the same source build later for /pimascor/ without rewrites.
    base: env.VITE_BASE_PATH ?? '/',
    plugins: [react()],
    build: {
      // The checked build remains deterministic in environments that cannot load
      // native Lightning CSS. Functional CSS output is still generated.
      cssMinify: false,
    },
    server: {
      port: 5173,
      strictPort: true,
    },
    preview: {
      port: 5173,
      strictPort: true,
    },
  }
})
