import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split the heavy, rarely-changing libraries into their own chunks so
        // they cache independently of application code and are only fetched by
        // the pages that use them. Without this the whole app - charts, graph
        // rendering, syntax highlighting and the in-browser LLM runtime -
        // shipped as one 7.9 MB file on first paint.
        // Only React itself is pinned: every page needs it, so a stable
        // chunk maximises cache reuse across deploys. Charting, graph
        // rendering, markdown and the LLM runtime are deliberately left to
        // Rollup, which attaches them to the lazy route chunks that actually
        // use them. Naming them here would force each into one shared chunk
        // that the entry preloads even when no initial route needs it.
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
    // The in-browser LLM runtime is a legitimately large lazy chunk; warn only
    // above a threshold that would indicate a genuine regression.
    chunkSizeWarningLimit: 1500,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      // Live step logs stream over /ws. Without a proxy entry the dev server
      // answered the upgrade itself, the socket errored, and the run detail
      // page silently fell back to polling only when running `npm run dev`.
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
