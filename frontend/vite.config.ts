import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ command }) => ({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,
    strictPort: true,
    // Vite dev server — only proxy when needed for non-Tauri web dev
    proxy: {
      // Uncomment to proxy API calls in web-only mode:
      // '/api': { target: 'http://localhost:8000', changeOrigin: true },
      // '/ws':  { target: 'ws://localhost:8000',  ws: true, changeOrigin: true },
    },
  },

  build: {
    outDir: 'dist',
    sourcemap: command === 'serve',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'query-vendor': ['@tanstack/react-query'],
          'motion-vendor': ['framer-motion'],
          'editor-vendor': ['@monaco-editor/react'],
          'zustand-vendor': ['zustand'],
        },
      },
    },
  },

  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },

  // Tauri expects a fixed port
  envPrefix: ['VITE_', 'TAURI_'],
}));
