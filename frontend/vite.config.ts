import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/claims': 'http://localhost:8000',
      '/policy': 'http://localhost:8000',
      '/members': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/test-cases': 'http://localhost:8000',
    },
  },
})
