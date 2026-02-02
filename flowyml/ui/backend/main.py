from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
import os
import traceback

from flowyml.monitoring.alerts import alert_manager, AlertLevel

# OpenTelemetry Imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from prometheus_client import make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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
    metrics as metrics_router,
    client,
    stats,
    websocket,
    deployments,
    model_explorer,
    auth,  # New Auth Router
)

# Initialize OpenTelemetry
resource = Resource(
    attributes={
        SERVICE_NAME: "flowyml-backend",
    },
)

# Tracing
trace_provider = TracerProvider(resource=resource)
# For now, just console export or no-op if no collector.
# In production, we'd add OTLPSpanExporter
trace_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(trace_provider)

# Metrics (Prometheus)
reader = PrometheusMetricReader()
meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meter_provider)

# Routers included above

app = FastAPI(
    title="flowyml UI",
    description="Real-time UI for flowyml pipelines",
    version="0.1.0",
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Expose Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 0. Skip if not in production to allow easy local development
        if os.getenv("FLOWYML_ENV") != "production":
            return await call_next(request)

        # 1. Check if token auth is enabled via env var
        api_token = os.getenv("FLOWYML_API_TOKEN")
        if not api_token:
            return await call_next(request)

        # 2. Define public paths
        path = request.url.path
        if (
            path in ["/api/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
            or path.startswith(("/assets", "/api/auth/login", "/api/auth/logout"))  # Allow login endpoints
            or path == "/"
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        # 3. Check Auth Header OR Cookie
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            # Check for cookie
            cookie_token = request.cookies.get("access_token")
            if cookie_token:
                auth_header = cookie_token  # Reuse validation logic below
            else:
                token_param = request.query_params.get("token")
                if token_param == api_token:
                    return await call_next(request)

                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized", "message": "Missing authentication token"},
                )

        # 4. Validate Token
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer" or token != api_token:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized", "message": "Invalid authentication token"},
                )
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Invalid Authorization header format"},
            )

        return await call_next(request)


app.add_middleware(AuthMiddleware)


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
app.include_router(metrics_router.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(plugins.router, prefix="/api", tags=["plugins"])
app.include_router(client.router, prefix="/api/client", tags=["client"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(deployments.router, prefix="/api", tags=["deployments"])
app.include_router(model_explorer.router, prefix="/api", tags=["model-explorer"])
app.include_router(auth.router, prefix="/api", tags=["auth"])


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


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("flowyml.ui.backend.main:app", host="0.0.0.0", port=port, reload=False)  # noqa: S104
