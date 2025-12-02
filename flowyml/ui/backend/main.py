from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
import os
import traceback

from flowyml.monitoring.alerts import alert_manager, AlertLevel

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
    metrics,
    client,
    stats,
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
        "remote_services": config.remote_services,
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
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(plugins.router, prefix="/api", tags=["plugins"])
app.include_router(client.router, prefix="/api/client", tags=["client"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


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


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    error_msg = str(exc)
    stack_trace = traceback.format_exc()

    # Log and alert
    alert_manager.send_alert(
        title="Backend API Error",
        message=f"Unhandled exception in {request.method} {request.url.path}: {error_msg}",
        level=AlertLevel.ERROR,
        metadata={"traceback": stack_trace, "path": request.url.path},
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Something went wrong on our end. We've been notified.",
            "detail": error_msg,  # In prod maybe hide this, but for now it's useful
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": exc.errors()},
    )
