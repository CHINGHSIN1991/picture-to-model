import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // GitHub Pages serves the site under /picture-to-model/; local dev and tests stay at /.
  base: process.env.VITE_BASE_PATH ?? '/',
  plugins: [vue()],
  build: {
    rollupOptions: {
      // `/` is the landing page (Step 10); `/viewer.html` keeps the Step 07–08 model check page.
      input: { index: 'index.html', viewer: 'viewer.html' },
    },
  },
})
