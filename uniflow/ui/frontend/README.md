# UniFlow UI Frontend

Modern React-based frontend for the UniFlow ML pipeline orchestration framework.

## 🚀 Quick Start

### Prerequisites

- **Node.js**: >= 16.x (recommended: 18.x or 20.x)
- **npm**: >= 8.x (comes with Node.js)

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start development server with hot reload
npm run dev
```

This will start the Vite dev server on `http://localhost:5173`. The dev server will:
- Hot reload on file changes
- Proxy API requests to `http://localhost:8080` (backend)
- Provide fast HMR (Hot Module Replacement)

**Note**: Make sure the backend is running before starting the frontend:

```bash
# In another terminal, start the backend
cd ../../..  # Back to repo root
uniflow ui start --port 8080
```

### Production Build

```bash
# Build for production
npm run build
```

Production artifacts will be in the `dist/` directory. The UniFlow Python backend automatically serves these files when available.

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/           # Page-level components
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   ├── api/             # API client functions
│   ├── types/           # TypeScript type definitions
│   ├── styles/          # Global styles and themes
│   ├── App.tsx          # Main app component
│   └── main.tsx         # Application entry point
├── public/              # Static assets
├── dist/                # Production build output (generated)
├── index.html           # HTML entry point
├── package.json         # Dependencies and scripts
├── vite.config.ts       # Vite configuration
├── tsconfig.json        # TypeScript configuration
└── README.md            # This file
```

## 🛠️ Available Scripts

### `npm run dev`

Starts the development server with hot reload.

- **URL**: http://localhost:5173
- **Features**: HMR, fast refresh, TypeScript checking
- **API Proxy**: Proxies `/api/*` to backend at `localhost:8080`

### `npm run build`

Builds the app for production to the `dist/` folder.

- Optimized for performance
- Minified and bundled
- TypeScript type checking
- Ready to be served by the Python backend

### `npm run preview`

Preview the production build locally:

```bash
npm run build
npm run preview
```

Serves the production build at `http://localhost:4173`.

### `npm run lint`

Run ESLint to check code quality:

```bash
npm run lint
```

### `npm run type-check`

Run TypeScript type checking without building:

```bash
npm run type-check
```

## 🎨 Tech Stack

- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: CSS Modules / Tailwind CSS (if configured)
- **State Management**: React Context / Zustand (if needed)
- **Routing**: React Router (if multi-page)
- **API Client**: Fetch API / Axios

## 🔌 API Integration

The frontend communicates with the UniFlow backend via REST API:

### Development Mode

In development, Vite proxies API requests to avoid CORS issues:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
```

### Production Mode

In production, the frontend is served by the Python backend from the `dist/` folder, so all API requests naturally go to the same origin.

### Example API Usage

```typescript
// src/api/pipelines.ts
export async function getPipelines() {
  const response = await fetch('/api/pipelines');
  return response.json();
}

export async function getPipeline(id: string) {
  const response = await fetch(`/api/pipelines/${id}`);
  return response.json();
}
```

## 🏗️ Development Workflow

### 1. Setup (First Time)

```bash
# Clone the repo and navigate to frontend
cd uniflow/ui/frontend

# Install dependencies
npm install
```

### 2. Development

```bash
# Terminal 1: Start backend
cd ../../..
uniflow ui start --dev

# Terminal 2: Start frontend
cd uniflow/ui/frontend
npm run dev
```

### 3. Making Changes

1. Edit files in `src/`
2. Hot reload will update the browser automatically
3. Check console for errors
4. Test API integration with backend running

### 4. Building for Production

```bash
# Build frontend
npm run build

# Test the backend serves it correctly
cd ../../..
uniflow ui start
# Visit http://localhost:8080
```

## 🐛 Troubleshooting

### Issue: `npm install` fails

**Solution**: Make sure you have Node.js 16+ installed:

```bash
node --version  # Should be >= 16.x
npm --version   # Should be >= 8.x
```

### Issue: API calls return 404

**Problem**: Backend not running or wrong port.

**Solution**:
1. Start the backend: `uniflow ui start --port 8080`
2. Check proxy config in `vite.config.ts`
3. Verify backend is on `http://localhost:8080/api/health`

### Issue: Hot reload not working

**Solution**:
1. Make sure you're running `npm run dev` (not `npm run build`)
2. Check for errors in the terminal
3. Try clearing Vite cache: `rm -rf node_modules/.vite`

### Issue: Build succeeds but backend shows "Frontend not built"

**Cause**: Backend looking in wrong directory.

**Solution**: Ensure the `dist/` folder exists in `uniflow/ui/frontend/dist/`

```bash
# Check if dist exists
ls -la dist/

# If not, rebuild
npm run build
```

## 🎯 Key Features to Implement

The frontend should provide:

1. **Dashboard**
   - Overview of recent pipeline runs
   - Active/running pipelines
   - Quick stats (success rate, avg duration)

2. **Pipeline List**
   - All registered pipelines
   - Search and filter
   - Click to view details

3. **Pipeline Details**
   - DAG visualization
   - Step-by-step execution status
   - Logs per step
   - Artifacts produced

4. **Run History**
   - List of all runs
   - Filter by pipeline, status, date
   - Compare runs side-by-side

5. **Asset Explorer**
   - Browse datasets, models, metrics
   - View lineage graph
   - Download artifacts

6. **Experiment Tracking**
   - Compare experiments
   - Metrics visualization (charts)
   - Parameter comparison

7. **Real-Time Updates** (Future)
   - WebSocket connection for live updates
   - Live metric streaming
   - Real-time log tailing

## 📚 Resources

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [UniFlow UI Guide](../../../UI_GUIDE.md)

## 🤝 Contributing

When contributing to the frontend:

1. Follow the existing code style
2. Use TypeScript for type safety
3. Write meaningful component names
4. Add comments for complex logic
5. Test API integration thoroughly
6. Ensure production build works

## 📝 Notes

- The Python backend serves the built frontend from `dist/`
- In production, there's no separate frontend server
- All state is fetched from the backend API
- WebSocket support is planned for future releases
