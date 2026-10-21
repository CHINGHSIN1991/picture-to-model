import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      // `/` is the landing page (Step 10); `/viewer.html` keeps the Step 07–08 model check page.
      input: { index: 'index.html', viewer: 'viewer.html' },
    },
  },
})
