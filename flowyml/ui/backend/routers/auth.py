"""Session authentication for the FlowyML UI.

FlowyML ships a single administrative identity. The credentials and the
session token are resolved from the environment on *every* request rather than
captured into module-level constants at import time, so that a process which
loads its ``.env`` after importing the app — or a test that patches the
environment — sees the current values instead of whatever happened to be set
when the module was first imported.
"""

from fastapi import APIRouter, HTTPException, status, Response, Request
from pydantic import BaseModel

from flowyml.ui.backend.security import (
    INSECURE_DEFAULT_PASSWORD,
    allow_insecure,
    constant_time_equals,
    get_admin_password,
    get_admin_user,
    get_api_token,
    is_production,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Models ---
class User(BaseModel):
    username: str
    role: str = "admin"


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str


# --- Routes ---


@router.post("/login", response_model=Token)
async def login(response: Response, login_data: LoginRequest):
    """Authenticate an operator and open a browser session.

    Sets an HttpOnly cookie for the UI and returns the same token for CLI and
    SDK use.
    """
    expected_user = get_admin_user()
    expected_password = get_admin_password()
    production = is_production()

    if expected_password is None:
        if production and not allow_insecure():
            # Never fall back to the documented default in production. Startup
            # validation normally prevents reaching this point at all; this
            # branch covers a host that imported ``app`` without running the
            # lifespan handler.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Server is misconfigured: FLOWYML_ADMIN_PASSWORD is not set, " "so no login can be authenticated."
                ),
            )
        expected_password = INSECURE_DEFAULT_PASSWORD

    # Compare both fields in constant time, and always compare both, so that
    # response latency reveals neither which field was wrong nor the length of
    # the configured password.
    user_ok = constant_time_equals(login_data.username, expected_user)
    password_ok = constant_time_equals(login_data.password, expected_password)

    if not (user_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = get_api_token()
    if token is None:
        if production and not allow_insecure():
            # The previous implementation issued the fixed string
            # "dev-token-placeholder" here, which any client could guess and
            # replay as a valid production session.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=("Server is misconfigured: FLOWYML_API_TOKEN is not set, so " "no session token can be issued."),
            )
        # Development only: the auth middleware is inactive here anyway, so
        # this value is a placeholder rather than a credential.
        token = "dev-token-placeholder"  # noqa: S105

    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=86400 * 7,  # 7 days
        secure=production,
        samesite="lax",
    )

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie."""
    # The attributes must match those used by set_cookie, otherwise the browser
    # keeps the original cookie and the session survives "logout".
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=is_production(),
        samesite="lax",
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=User)
async def get_current_user(request: Request):
    """Return the currently authenticated operator.

    Reaching this endpoint in production means ``AuthMiddleware`` already
    validated the caller's bearer token or session cookie.
    """
    if not is_production():
        # Local development runs without authentication by design.
        return {"username": "developer", "role": "admin"}

    return {"username": get_admin_user(), "role": "admin"}
