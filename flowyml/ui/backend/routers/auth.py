from fastapi import APIRouter, HTTPException, status, Response, Request
from pydantic import BaseModel
import os

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


# --- Config ---
# For simplicity in this iteration, we use single-user admin auth
ADMIN_USER = os.getenv("FLOWYML_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("FLOWYML_ADMIN_PASSWORD", "flowyml")
# In production, this token is also a long-lived secret or signed JWT.
# For simplicity, we reuse the API Token logic or generate a session token.
# Here, we'll implement a simple session token mechanism or reuse API token.
API_TOKEN = os.getenv("FLOWYML_API_TOKEN")

# --- Routes ---


@router.post("/login", response_model=Token)
async def login(response: Response, login_data: LoginRequest):
    """
    Login with username and password.
    Sets HttpOnly cookie for browser sessions.
    Returns token for CLI/API use.
    """
    if login_data.username != ADMIN_USER or login_data.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use the API token as the session token for simplicity in this unified auth model
    # Ensure API_TOKEN is set in production!
    if not API_TOKEN:
        # Fallback for dev if not set (though middleware skips auth in dev usually)
        token = "dev-token-placeholder"  # noqa: S105
    else:
        token = API_TOKEN

    # Set HttpOnly cookie
    # accessible only by server, secure in prod
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=86400 * 7,  # 7 days
        secure=os.getenv("FLOWYML_ENV") == "production",
        samesite="lax",
    )

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=User)
async def get_current_user(request: Request):
    """
    Get current logged in user.
    Used by frontend to verify session.
    """
    # If middleware let us through, we are authenticated.
    # In 'production' mode, unauth requests are blocked by middleware.
    # In 'development' mode, middleware skips, so we check env.

    if os.getenv("FLOWYML_ENV") != "production":
        # Local dev: always return default admin
        return {"username": "developer", "role": "admin"}

    # In production, if we reached here, AuthMiddleware validated us.
    # We can inspect headers/cookies to determine *who* it is
    # (if we had multi-user), but for now it's just Admin.
    return {"username": ADMIN_USER, "role": "admin"}
