import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite 配置：开发服务器代理 /api 与 /meme 到后端
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/roast': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
      '/github': 'http://localhost:8000',
      '/meme': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
