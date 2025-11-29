from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Include API routers
from flowyml.ui.backend.routers import (
    pipelines,
    runs,
    assets,
    experiments,
    traces,
    projects,
    schedules,
    notifications,
    leaderboard,
    execution,
    plugins,
)

app = FastAPI(
    title="flowyml UI",
    description="Real-time UI for flowyml pipelines",
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


@app.get("/api/config")
async def get_public_config():
    """Get public configuration."""
    from flowyml.utils.config import get_config

    config = get_config()
    return {
        "execution_mode": config.execution_mode,
        "remote_server_url": config.remote_server_url,
        "remote_ui_url": config.remote_ui_url,
        "enable_ui": config.enable_ui,
    }


app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
app.include_router(traces.router, prefix="/api/traces", tags=["traces"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(schedules.router, prefix="/api/schedules", tags=["schedules"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["leaderboard"])
app.include_router(execution.router, prefix="/api/execution", tags=["execution"])
app.include_router(plugins.router, prefix="/api", tags=["plugins"])


# Stats endpoint for dashboard
@app.get("/api/stats")
async def get_stats(project: str = None):
    """Get overall statistics for the dashboard, optionally filtered by project."""
    try:
        from flowyml.storage.metadata import SQLiteMetadataStore

        store = SQLiteMetadataStore()

        # Get base stats
        stats = store.get_statistics()

        # Get run status counts (not in get_statistics yet)
        # We can add this to get_statistics later, but for now let's query efficiently
        import sqlite3

        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()

        if project:
            cursor.execute(
                "SELECT COUNT(*) FROM runs WHERE project = ? AND status = 'completed'",
                [project],
            )
            completed_runs = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM runs WHERE project = ? AND status = 'failed'",
                [project],
            )
            failed_runs = cursor.fetchone()[0]

            cursor.execute(
                "SELECT AVG(duration) FROM runs WHERE project = ? AND duration IS NOT NULL",
                [project],
            )
            avg_duration = cursor.fetchone()[0] or 0

            cursor.execute(
                "SELECT COUNT(*) FROM runs WHERE project = ?",
                [project],
            )
            total_runs = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'completed'")
            completed_runs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'failed'")
            failed_runs = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(duration) FROM runs WHERE duration IS NOT NULL")
            avg_duration = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM runs")
            total_runs = cursor.fetchone()[0]

        conn.close()

        return {
            "runs": total_runs if project else stats.get("total_runs", 0),
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "pipelines": stats.get("total_pipelines", 0),  # TODO: filter by project
            "artifacts": stats.get("total_artifacts", 0),  # TODO: filter by project
            "avg_duration": avg_duration,
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
            "error": str(e),
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
            "message": "flowyml API is running.",
            "detail": "Frontend not built. Run 'npm run build' in flowyml/ui/frontend to enable the UI.",
        }
