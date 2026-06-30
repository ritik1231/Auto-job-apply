import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { crx, defineManifest } from '@crxjs/vite-plugin'
import { fileURLToPath } from 'url'

const manifest = defineManifest({
  manifest_version: 3,
  name: 'SmartApply',
  version: '0.1.0',
  description: 'Apply to LinkedIn hiring posts in under 10 seconds with AI.',
  permissions: ['activeTab', 'storage', 'identity'],
  host_permissions: [
    'https://www.linkedin.com/*',
    'https://smartapply-api.onrender.com/*',
  ],
  background: {
    service_worker: 'src/background/service-worker.ts',
    type: 'module',
  },
  content_scripts: [
    {
      matches: ['https://www.linkedin.com/*'],
      js: ['src/content/index.ts'],
    },
  ],
  action: {
    default_popup: 'src/popup/index.html',
    default_title: 'SmartApply',
  },
})

export default defineConfig({
  plugins: [react(), crx({ manifest })],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
