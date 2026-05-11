import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig(({ command }) => ({
  plugins: [react()],

  resolve: {
    alias: {
      '@': resolve(process.cwd(), './src'),
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
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor';
            }
            if (id.includes('@tanstack')) {
              return 'query-vendor';
            }
            if (id.includes('framer-motion')) {
              return 'motion-vendor';
            }
            if (id.includes('monaco-editor')) {
              return 'editor-vendor';
            }
            if (id.includes('zustand')) {
              return 'zustand-vendor';
            }
            return 'vendor';
          }
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
