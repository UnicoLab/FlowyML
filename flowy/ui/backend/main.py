from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="Flowy UI",
    description="Real-time UI for Flowy pipelines",
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
from flowy.ui.backend.routers import pipelines, runs, assets, experiments

app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])

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
            "message": "Flowy API is running.",
            "detail": "Frontend not built. Run 'npm run build' in flowy/ui/frontend to enable the UI."
        }
