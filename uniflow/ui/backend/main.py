from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="UniFlow UI",
    description="Real-time UI for UniFlow pipelines",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

# Include API routers
from uniflow.ui.backend.routers import pipelines, runs, assets, experiments, traces

app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
app.include_router(traces.router, prefix="/api/traces", tags=["traces"])

# Stats endpoint for dashboard
@app.get("/api/stats")
async def get_stats():
    """Get overall statistics for the dashboard."""
    try:
        from uniflow.storage.metadata import SQLiteMetadataStore
        store = SQLiteMetadataStore()
        
        # Get base stats
        stats = store.get_statistics()
        
        # Get run status counts (not in get_statistics yet)
        # We can add this to get_statistics later, but for now let's query efficiently
        import sqlite3
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'completed'")
        completed_runs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'failed'")
        failed_runs = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(duration) FROM runs WHERE duration IS NOT NULL")
        avg_duration = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "runs": stats.get('total_runs', 0),
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "pipelines": stats.get('total_pipelines', 0),
            "artifacts": stats.get('total_artifacts', 0),
            "avg_duration": avg_duration
        }
    except Exception as e:
        # Return default stats if there's an error
        return {
            "runs": 0,
            "completed_runs": 0,
            "failed_runs": 0,
            "pipelines": 0,
            "artifacts": 0,
            "avg_duration": 0,
            "error": str(e)
        }

# Static file serving for frontend
# Path to frontend build
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(frontend_dist):
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Serve index.html for root and other non-API routes
    # Use a specific route for root
    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))
    
    # For SPA routing, we need to serve index.html for common frontend routes
    # But we can't use a catch-all because it interferes with API routes
    # Instead, mount a StaticFiles handler for the root, but do it AFTER API routes
    # Actually, let's try a different approach - use a custom middleware or exceptions
    
    # The trick is to let FastAPI handle routes first, then catch 404s
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from fastapi.exception_handlers import http_exception_handler
    
    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request, exc):
        # If it's a 404 and not an API route, serve the SPA
        if exc.status_code == 404 and not request.url.path.startswith("/api"):
            return FileResponse(os.path.join(frontend_dist, "index.html"))
        # Otherwise, use the default handler
        return await http_exception_handler(request, exc)
else:
    @app.get("/")
    async def root():
        return {
            "message": "UniFlow API is running.",
            "detail": "Frontend not built. Run 'npm run build' in uniflow/ui/frontend to enable the UI."
        }
