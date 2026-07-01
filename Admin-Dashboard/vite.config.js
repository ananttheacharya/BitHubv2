import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3002, // Different from Frontend (3000) and Backend (3001)
    proxy: {
      '/api': 'http://localhost:3001'
    }
  }
})
