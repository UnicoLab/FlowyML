# 🖥️ Flowy UI Guide

This guide explains how to use the Flowy UI to monitor and manage your ML pipelines in real-time.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Usage Modes](#usage-modes)
5. [Frontend Development](#frontend-development)
6. [Backend Architecture](#backend-architecture)
7. [Integration with Pipelines](#integration-with-pipelines)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Flowy UI provides a real-time dashboard for monitoring ML pipelines, viewing execution status, exploring artifacts, and comparing experiments. It consists of:

- **Backend**: FastAPI server (`flowy/ui/backend/`) that serves the API and static files
- **Frontend**: React application (`flowy/ui/frontend/`) with modern UI for visualization
- **CLI**: Command-line interface for starting/stopping the UI server

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Flowy UI Stack                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Frontend (React + Vite)                           │
│  ↓                                                  │
│  Backend (FastAPI + Uvicorn)                       │
│  ↓                                                  │
│  Core (Pipeline Execution + Storage)               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Installation

### Install Flowy with UI Support

```bash
# Option 1: Install from PyPI (when published)
pip install "flowy[ui]"

# Option 2: Install from source (development)
git clone https://github.com/flowy/flowy.git
cd flowy
pip install -e ".[ui]"  # Editable install - makes 'flowy' command available
```

**Important for Development**: If you're working with the source code and get `zsh: command not found: flowy`, you need to install the package in editable mode:

```bash
# Navigate to the repo root
cd /path/to/Flowy

# Install in editable mode
pip install -e ".[ui]"

# Now the 'flowy' command works!
flowy ui start
```

**Alternative** (without installation):
```bash
# Run CLI directly using Python module
python -m flowy.cli.main ui start
python -m flowy.cli.main ui status
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for complete development setup instructions.


### Build the Frontend (First Time Setup)

```bash
# Navigate to the frontend directory
cd flowy/ui/frontend

# Install Node.js dependencies
npm install

# Build the frontend production bundle
npm run build
```

The build artifacts will be placed in `flowy/ui/frontend/dist/`, and the backend will automatically serve them.

---

## Quick Start

### Start the UI Server

```bash
# Start the UI server on default port (8080)
flowy ui start

# Start on custom port
flowy ui start --port 3000

# Start with custom host
flowy ui start --host 0.0.0.0 --port 8080

# Start in development mode (auto-reload)
flowy ui start --dev
```

The UI will be available at: **http://localhost:8080**

### Run a Pipeline with UI Monitoring

When you run a pipeline, it automatically connects to the UI backend (if running):

```python
from flowy import Pipeline, step, context

ctx = context(
    learning_rate=0.001,
    epochs=10,
    batch_size=32
)

@step(outputs=["model/trained"])
def train_model(learning_rate: float, epochs: int, batch_size: int):
    print(f"Training with lr={learning_rate}")
    # Your training logic
    model = {"weights": "trained", "accuracy": 0.95}
    return model

# Create and run pipeline
pipeline = Pipeline("training_pipeline", context=ctx)
pipeline.add_step(train_model)

# Run the pipeline - UI will automatically track it!
result = pipeline.run(debug=True)

# The pipeline execution will be visible in the UI dashboard
print(f"✅ View your pipeline at: http://localhost:8080")
```

---

## Usage Modes

### Mode 1: On-Demand UI (Manual Start)

Start the UI server manually when you need it:

```bash
# Terminal 1: Start the UI server
flowy ui start

# Terminal 2: Run your pipelines
python my_pipeline.py
```

**Pros:**
- Full control over when the UI runs
- Can stop/start as needed
- Good for development

**Cons:**
- Need to remember to start it
- Requires separate terminal

---

### Mode 2: Background Server (Daemon-like)

Run the UI server in the background:

```bash
# Start UI server in background
nohup flowy ui start --port 8080 > flowy_ui.log 2>&1 &

# Check if running
ps aux | grep "flowy ui"

# View logs
tail -f flowy_ui.log

# Stop the server
pkill -f "flowy ui"
```

**Pros:**
- Always available
- No need to manually start
- Good for long-running development sessions

**Cons:**
- Consumes resources when not in use
- Requires manual background process management

---

### Mode 3: Auto-Start on Pipeline Run (Future Enhancement)

> **Note**: This is a planned feature similar to ZenML's approach.

Future versions will support automatic UI server startup:

```python
# Proposed API (not yet implemented)
from flowy import Pipeline, context

pipeline = Pipeline("my_pipeline", context=ctx)

# Auto-start UI if not running, and open browser
result = pipeline.run(
    ui=True,              # Start UI if not running
    open_browser=True     # Open browser automatically
)

# Returns URL to the running pipeline
print(f"View pipeline at: {result.ui_url}")
```

This would automatically:
1. Check if UI server is running
2. Start it in background if not
3. Register the pipeline run
4. Open browser to the pipeline view
5. Keep server running for future runs

---

## Frontend Development

### Development Mode (Hot Reload)

For frontend development with hot reload:

```bash
# Terminal 1: Start the backend
cd /path/to/Flowy
flowy ui start --port 8080

# Terminal 2: Start the frontend dev server
cd flowy/ui/frontend
npm run dev
```

The frontend dev server will run on `http://localhost:5173` and proxy API calls to the backend on `http://localhost:8080`.

### Build for Production

```bash
cd flowy/ui/frontend

# Build the production bundle
npm run build

# The backend will automatically serve from dist/
```

### Frontend Structure

```
flowy/ui/frontend/
├── src/
│   ├── components/      # React components
│   ├── pages/           # Page components
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   ├── styles/          # CSS/styling
│   └── App.tsx          # Main application
├── public/              # Static assets
├── dist/                # Production build (generated)
├── package.json         # Node dependencies
├── vite.config.ts       # Vite configuration
└── README.md            # Frontend-specific docs
```

---

## Backend Architecture

### FastAPI Application

The backend is located in `flowy/ui/backend/`:

```
flowy/ui/backend/
├── main.py              # FastAPI app entry point
├── routers/
│   ├── pipelines.py     # Pipeline endpoints
│   ├── runs.py          # Run tracking endpoints
│   └── assets.py        # Asset management endpoints
└── __init__.py
```

### API Endpoints

The backend exposes the following REST API:

#### Health Check
```
GET /api/health
```

#### Pipelines
```
GET /api/pipelines              # List all pipelines
GET /api/pipelines/{id}         # Get pipeline details
```

#### Runs
```
GET /api/runs                   # List all runs
GET /api/runs/{id}              # Get run details
GET /api/runs/{id}/logs         # Get run logs
GET /api/runs/{id}/metrics      # Get run metrics
```

#### Assets
```
GET /api/assets                 # List all assets
GET /api/assets/{id}            # Get asset details
GET /api/assets/{id}/lineage    # Get asset lineage
```

### WebSocket Support (Future)

For real-time pipeline updates:

```
WS /api/ws/runs/{run_id}        # Live run updates
WS /api/ws/metrics/{run_id}     # Live metrics streaming
```

---

## Integration with Pipelines

### Automatic UI Integration

Flowy pipelines automatically integrate with the UI when it's running:

```python
from flowy import Pipeline, step, context

# 1. No special code needed - just run your pipeline!
pipeline = Pipeline("my_pipeline", context=ctx)
pipeline.add_step(my_step)

# 2. Pipeline automatically registers with UI backend
result = pipeline.run()

# 3. All execution data flows to UI in real-time:
#    - Step status updates
#    - Metrics (if logged)
#    - Artifacts
#    - Execution logs
```

### Logging Metrics to UI

Use the step context to log metrics that appear in the UI:

```python
@step
def train_model(data, epochs: int):
    model = MyModel()
    
    for epoch in range(epochs):
        loss = train_epoch(model, data)
        
        # Option 1: Yield metrics (automatically sent to UI)
        yield {"epoch": epoch, "loss": loss}
        
        # Option 2: Use step context (if available)
        # step.log("loss", loss)
        # step.log("epoch", epoch)
    
    return model
```

### Accessing UI URL from Code

```python
from flowy.ui import get_ui_url, is_ui_running

# Check if UI is running
if is_ui_running():
    ui_url = get_ui_url()
    print(f"✅ View pipeline at: {ui_url}")
else:
    print("ℹ️  UI not running. Start with: flowy ui start")
```

---

## Troubleshooting

### Issue: UI Shows "Frontend not built"

**Solution**: Build the frontend first:

```bash
cd flowy/ui/frontend
npm install
npm run build
```

### Issue: Port Already in Use

**Error**: `Address already in use`

**Solution**: Use a different port or kill the existing process:

```bash
# Option 1: Use different port
flowy ui start --port 8081

# Option 2: Find and kill process on port 8080
lsof -ti:8080 | xargs kill -9
```

### Issue: UI Not Showing Pipeline Runs

**Check**:
1. Is the UI backend running? (`flowy ui start`)
2. Is the pipeline actually running?
3. Check backend logs for errors
4. Verify `.flowy` directory exists in your project

**Debug**:
```bash
# Check Flowy configuration
flowy config

# View backend logs (if running in background)
tail -f flowy_ui.log
```

### Issue: WebSocket Connection Failed

**Solution**: WebSocket support is still under development. For now, the UI uses polling to fetch updates.

### Issue: CORS Errors in Browser

**Cause**: Frontend dev server on different port than backend.

**Solution**: Configure proxy in `vite.config.ts` (already configured):

```typescript
// flowy/ui/frontend/vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8080'
    }
  }
})
```

---

## Advanced Configuration

### Custom UI Port in Configuration

Create a `.flowy/config.yaml` file:

```yaml
ui_port: 3000
ui_host: "0.0.0.0"
ui_dev_mode: false
```

Then start with:
```bash
flowy ui start  # Uses config file settings
```

### Running UI Behind Reverse Proxy

If deploying Flowy UI behind nginx or another reverse proxy:

```nginx
# nginx.conf
server {
    listen 80;
    server_name flowy.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8080/api/;
    }
}
```

### Environment Variables

```bash
# Set custom UI port
export FLOWY_UI_PORT=3000

# Set UI host
export FLOWY_UI_HOST=0.0.0.0

# Enable debug mode
export FLOWY_DEBUG=true

# Start UI
flowy ui start
```

---

## Future Enhancements

### Planned Features

1. **Auto-Start on Pipeline Run**
   - Automatic UI server startup when running pipelines
   - Similar to ZenML's approach
   - Command: `flowy init` to set up background server

2. **Daemon Mode**
   - Persistent background server
   - System service integration
   - Automatic restart on crashes

3. **WebSocket Real-Time Updates**
   - Live metric streaming
   - Real-time pipeline status
   - Live log tailing

4. **Multi-User Support**
   - Authentication and authorization
   - User workspaces
   - Shared pipelines

5. **Cloud Deployment**
   - Docker containerization
   - Kubernetes support
   - Cloud-native scaling

6. **GoLang Backend (Long-term)**
   - Single binary distribution
   - Smaller footprint
   - Better performance
   - Cross-platform compatibility

---

## Summary

### To Use Flowy UI:

1. **Install**: `pip install "flowy[ui]"`
2. **Build Frontend**: `cd flowy/ui/frontend && npm install && npm run build`
3. **Start Server**: `flowy ui start`
4. **Run Pipeline**: Execute your pipeline Python script
5. **View**: Open http://localhost:8080 in your browser

### Key Points:

- ✅ UI backend automatically serves frontend if built
- ✅ Pipelines automatically connect to UI when it's running
- ✅ No special code needed in your pipelines
- ✅ Real-time monitoring of pipeline execution
- ✅ Can run in background or foreground mode
- 🔜 Future: Auto-start and daemon mode coming soon

For more information, see:
- [Frontend README](flowy/ui/frontend/README.md)
- [Main README](README.md)
- [Design Document](DESIGN.md)
