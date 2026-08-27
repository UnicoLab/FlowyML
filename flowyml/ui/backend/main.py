from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
import os
import traceback
import uuid
from contextlib import asynccontextmanager

from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler

from flowyml import __version__
from flowyml.monitoring.alerts import alert_manager, AlertLevel
from flowyml.ui.backend.security import (
    allow_insecure,
    assert_production_security,
    constant_time_equals,
    get_api_token,
    get_cors_origins,
    is_production,
    is_public_path,
)

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
    templates,  # Pipeline Templates
    ai_context,  # AI Assistant Context
    evaluations,  # Evaluation Framework
    stacks,  # Stack Management
)

# Initialize OpenTelemetry
resource = Resource(
    attributes={
        SERVICE_NAME: "flowyml-backend",
    },
)

# Tracing - Use OTLP exporter in production, console in development
trace_provider = TracerProvider(resource=resource)
_otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if _otlp_endpoint:
    # Production: Use OTLP exporter (supports Jaeger, Honeycomb, Google Cloud Trace, etc.)
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        trace_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=_otlp_endpoint)),
        )
    except ImportError:
        # Fallback to console if OTLP exporter not installed
        trace_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
elif os.getenv("FLOWYML_OTEL_CONSOLE", "").strip().lower() in {"1", "true", "yes", "on"}:
    # Opt-in local debugging. The console exporter prints a multi-line JSON
    # document per span - four or more per HTTP request - so enabling it by
    # default drowned real log output and made `flowyml ui` unreadable in a
    # terminal. Tracing stays fully active either way; only the noisy stdout
    # sink is opt-in.
    trace_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(trace_provider)

# Metrics (Prometheus)
reader = PrometheusMetricReader()
meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meter_provider)

# Routers included above


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Validate the deployment before accepting the first request."""
    assert_production_security()
    yield


app = FastAPI(
    title="flowyml UI",
    description="Real-time UI for flowyml pipelines",
    version=__version__,
    lifespan=lifespan,
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Expose Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Configure CORS. Origins are resolved from the environment so that a
# wildcard is never paired with credentialed requests - see
# flowyml.ui.backend.security.get_cors_origins for why that pairing is unsafe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _unauthorized(message: str) -> JSONResponse:
    """Build a 401 that tells the client how to authenticate."""
    return JSONResponse(
        status_code=401,
        content={"error": "Unauthorized", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Require a bearer token for every non-public request in production.

    Development deliberately runs open so ``flowyml ui`` needs no setup. In
    production the middleware fails *closed*: an instance that declares
    ``FLOWYML_ENV=production`` without ``FLOWYML_API_TOKEN`` is rejected at
    startup by ``assert_production_security``, and this middleware refuses
    every request as a second line of defence in case startup validation was
    bypassed (for example by an ASGI host that imports ``app`` directly).
    """

    async def dispatch(self, request: Request, call_next):
        # Local development runs without authentication by design.
        if not is_production():
            return await call_next(request)

        # An operator fronting FlowyML with their own auth proxy opts out.
        if allow_insecure():
            return await call_next(request)

        path = request.url.path

        # CORS preflight carries no credentials by definition.
        if request.method == "OPTIONS" or is_public_path(path):
            return await call_next(request)

        api_token = get_api_token()
        if api_token is None:
            # Fail closed. Previously this branch let the request through,
            # which left the whole control plane - including remote pipeline
            # execution - open to anyone who could reach the port.
            #
            # The specifics go to the log, not to the caller: telling an
            # anonymous client which environment variable is missing confirms
            # for an attacker that the instance is unauthenticated.
            logger.error(
                "Refusing request: FLOWYML_ENV=production but FLOWYML_API_TOKEN is "
                "not set, so no request can be authenticated. Set FLOWYML_API_TOKEN, "
                "or set FLOWYML_ALLOW_INSECURE=1 if a proxy enforces authentication.",
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "message": "Server is misconfigured and cannot serve requests.",
                },
            )

        auth_header = request.headers.get("Authorization") or request.cookies.get("access_token")

        if not auth_header:
            return _unauthorized("Missing authentication token")

        # Accept "Bearer <token>" from either the header or the session cookie.
        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return _unauthorized("Invalid Authorization header format")

        if not constant_time_equals(token.strip(), api_token):
            return _unauthorized("Invalid authentication token")

        return await call_next(request)


app.add_middleware(AuthMiddleware)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": __version__}


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
app.include_router(templates.router, tags=["templates"])
app.include_router(ai_context.router, tags=["ai"])  # AI Context for assistant
app.include_router(evaluations.router, prefix="/api", tags=["evaluations"])  # Evaluation Framework
app.include_router(stacks.router, prefix="/api/stacks", tags=["stacks"])  # Stack Management


# Static file serving for frontend
# Path to frontend build
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(frontend_dist):
    # Mount static assets
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(frontend_dist, "assets")),
        name="assets",
    )

    # Serve index.html for root and other non-API routes
    # Use a specific route for root
    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    # For SPA routing, we need to serve index.html for common frontend routes
    # But we can't use a catch-all because it interferes with API routes
    # Instead, mount a StaticFiles handler for the root, but do it AFTER API routes
    # Actually, let's try a different approach - use a custom middleware or exceptions

    # Client-side routes are served by the 404 handler below rather than a
    # catch-all route. A catch-all would match *before* Starlette's
    # redirect_slashes logic, turning every `/api/stats` (declared as
    # `/api/stats/`) into a 404 instead of a redirect.
    _frontend_index = os.path.join(frontend_dist, "index.html")

else:
    _frontend_index = None

    @app.get("/")
    async def root():
        return {
            "message": "flowyml API is running.",
            "detail": "Frontend not built. Run 'npm run build' in flowyml/ui/frontend to enable the UI.",
        }


def _error_reference() -> str:
    """A short id tying a client's error response to a server log entry."""
    return uuid.uuid4().hex[:12]


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler_with_redaction(request, exc):
    """Serve the SPA for unknown page routes; redact 5xx details in production.

    A single handler covers both concerns because Starlette allows only one
    handler per exception type.

    Unknown ``/api`` and ``/ws`` paths deliberately keep their JSON 404: a typo
    in a fetch URL must not come back as the HTML shell, which the caller would
    then fail to parse with a confusing error far from the cause.

    Handlers across the API raise ``HTTPException(500, detail=str(e))``. In
    production that text reaches the client verbatim, and for SQLAlchemy errors
    it carries the failing SQL statement and connection details, while file
    errors carry absolute server paths. The real message is always logged; only
    what crosses the wire is reduced.
    """
    if exc.status_code == 404 and _frontend_index is not None and not request.url.path.startswith(("/api", "/ws")):
        return FileResponse(_frontend_index)

    if exc.status_code >= 500:
        reference = _error_reference()
        logger.error(
            f"[{reference}] {request.method} {request.url.path} -> {exc.status_code}: " f"{exc.detail}",
        )
        if is_production():
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": "Internal Server Error",
                    "message": "The server failed to handle this request.",
                    "reference": reference,
                },
                headers=getattr(exc, "headers", None) or {},
            )

    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    error_msg = str(exc)
    stack_trace = traceback.format_exc()
    reference = _error_reference()

    # Always record the full failure server-side, whatever we return.
    logger.error(
        f"[{reference}] Unhandled exception in {request.method} {request.url.path}: " f"{error_msg}\n{stack_trace}",
    )

    alert_manager.send_alert(
        title="Backend API Error",
        message=f"Unhandled exception in {request.method} {request.url.path}: {error_msg}",
        level=AlertLevel.ERROR,
        metadata={"traceback": stack_trace, "path": request.url.path, "reference": reference},
    )

    content = {
        "error": "Internal Server Error",
        "message": "Something went wrong on our end. We've been notified.",
        "reference": reference,
    }
    # Exception text can carry SQL, credentials and server paths, so it is only
    # echoed outside production where the operator is the developer.
    if not is_production():
        content["detail"] = error_msg

    return JSONResponse(status_code=500, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": exc.errors()},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "flowyml.ui.backend.main:app",
        host="0.0.0.0",  # noqa: S104
        port=port,
        reload=False,
    )
