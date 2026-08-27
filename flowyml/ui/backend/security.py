"""Central security configuration for the FlowyML UI backend.

Every security decision the backend makes is resolved here, at *request* time
rather than import time, so that tests and embedding hosts can change the
environment without reimporting the application.

The guiding rule is **fail closed**: a deployment that declares itself
production but has not been given credentials refuses to serve rather than
silently exposing an unauthenticated control plane.  ``/api/execution/execute``
imports and runs arbitrary Python modules, so an open instance is remote code
execution, not merely an information leak.

Operators who terminate authentication in front of FlowyML (an ingress
controller, an OAuth2 proxy, a service mesh) can opt out of the built-in check
with ``FLOWYML_ALLOW_INSECURE=1``.
"""

from __future__ import annotations

import os
import secrets

# The historical default password. Shipping it means every deployment that
# forgets to set FLOWYML_ADMIN_PASSWORD shares one publicly documented
# credential, so it is rejected outright in production.
INSECURE_DEFAULT_PASSWORD = "flowyml"  # noqa: S105
DEFAULT_ADMIN_USER = "admin"

#: Paths that must stay reachable without authentication for the UI to be
#: usable at all: health probes, the login form itself, and the static bundle.
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/api/health",
        "/api/auth/login",
        "/api/auth/logout",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    },
)

#: Path *prefixes* that are public. Kept explicit (with the trailing slash for
#: directory-like prefixes) so that ``/assets`` cannot be widened into a match
#: for an unrelated route such as ``/assets-internal``.
PUBLIC_PATH_PREFIXES: tuple[str, ...] = ("/assets/", "/metrics")


def _env(name: str) -> str | None:
    """Read an environment variable, treating blank/whitespace as unset.

    ``docker-compose.yml`` and ``.env.example`` both ship
    ``FLOWYML_API_TOKEN=`` with an empty value, so an empty string must not be
    mistaken for a configured secret.
    """
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def is_production() -> bool:
    """True when the deployment declares itself production."""
    env = _env("FLOWYML_ENV")
    return env is not None and env.lower() == "production"


def allow_insecure() -> bool:
    """True when the operator has explicitly accepted running without auth."""
    value = _env("FLOWYML_ALLOW_INSECURE")
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def get_api_token() -> str | None:
    """The shared API token used for machine and session authentication."""
    return _env("FLOWYML_API_TOKEN")


def get_admin_user() -> str:
    """The username accepted by the UI login form."""
    return _env("FLOWYML_ADMIN_USER") or DEFAULT_ADMIN_USER


def get_admin_password() -> str | None:
    """The password accepted by the UI login form, if configured."""
    return _env("FLOWYML_ADMIN_PASSWORD")


def constant_time_equals(left: str | None, right: str | None) -> bool:
    """Compare two secrets without leaking their contents through timing.

    A plain ``==`` on strings short-circuits at the first differing byte, which
    lets an attacker recover a token one character at a time.  ``None`` never
    matches anything, so an unset secret cannot be satisfied by sending an
    empty value.
    """
    if left is None or right is None:
        return False
    return secrets.compare_digest(left, right)


def is_public_path(path: str) -> bool:
    """True when *path* is reachable without authentication."""
    if path in PUBLIC_PATHS:
        return True
    return path.startswith(PUBLIC_PATH_PREFIXES)


def security_misconfigurations() -> list[str]:
    """Describe every reason this deployment is unsafe to expose.

    Returns an empty list when the configuration is sound, or when the
    deployment is not production (local development intentionally runs open),
    or when the operator has set ``FLOWYML_ALLOW_INSECURE``.
    """
    if not is_production() or allow_insecure():
        return []

    problems: list[str] = []

    if get_api_token() is None:
        problems.append(
            "FLOWYML_API_TOKEN is not set. Without it the API accepts every "
            "request, including POST /api/execution/execute, which imports and "
            "runs arbitrary Python modules.",
        )

    password = get_admin_password()
    if password is None:
        problems.append(
            "FLOWYML_ADMIN_PASSWORD is not set. The UI login form would accept "
            f"the publicly documented default password '{INSECURE_DEFAULT_PASSWORD}'.",
        )
    elif password == INSECURE_DEFAULT_PASSWORD:
        problems.append(
            "FLOWYML_ADMIN_PASSWORD is still the publicly documented default "
            f"'{INSECURE_DEFAULT_PASSWORD}'. Choose a unique password.",
        )

    return problems


def assert_production_security() -> None:
    """Raise when a production deployment is missing its credentials.

    Called during application startup so the operator sees the problem
    immediately, instead of discovering months later that the control plane was
    world-writable.
    """
    problems = security_misconfigurations()
    if not problems:
        return

    bullet_list = "\n".join(f"  - {p}" for p in problems)
    raise RuntimeError(
        "FlowyML refuses to start: FLOWYML_ENV=production but the deployment "
        f"is not secured.\n{bullet_list}\n\n"
        "Set the variables above, or set FLOWYML_ALLOW_INSECURE=1 if "
        "authentication is enforced by a proxy in front of FlowyML.",
    )


def get_cors_origins() -> list[str]:
    """Resolve the allowed CORS origins for this deployment.

    ``FLOWYML_CORS_ORIGINS`` accepts a comma-separated list and overrides the
    defaults in either environment.

    The wildcard ``*`` is never combined with credentialed requests: browsers
    reject that pairing, and Starlette works around it by reflecting whatever
    ``Origin`` the caller sent, which would let any website on the internet
    issue credentialed requests to a developer's local instance and read the
    responses.
    """
    configured = _env("FLOWYML_CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]

    if is_production():
        return [
            "https://flowyml.unicolab.ai",
            "https://app.flowyml.io",
        ]

    # Development: the concrete origins a Vite/CRA dev server uses. Explicit
    # rather than "*" so credentialed cross-origin reads stay impossible.
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]
