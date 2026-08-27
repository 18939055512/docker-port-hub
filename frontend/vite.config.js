import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // 开发环境代理到后端
      '/api': {
        target: 'http://localhost:38082',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    // 后端 Flask 直接托管静态文件
    assetsDir: 'assets',
    sourcemap: false
  }
})