"""Authentication and authorization for UniFlow API."""

import secrets
import hashlib
import json
from pathlib import Path
from typing import Any
from datetime import datetime
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


class TokenManager:
    """Manage API tokens for authentication."""

    def __init__(self, tokens_file: str = ".uniflow/api_tokens.json"):
        self.tokens_file = Path(tokens_file)
        self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_tokens()

    def _load_tokens(self) -> None:
        """Load tokens from file."""
        if self.tokens_file.exists():
            with open(self.tokens_file) as f:
                self.tokens = json.load(f)
        else:
            self.tokens = {}
            self._save_tokens()

    def _save_tokens(self) -> None:
        """Save tokens to file."""
        with open(self.tokens_file, "w") as f:
            json.dump(self.tokens, f, indent=2)

    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def create_token(
        self,
        name: str,
        project: str | None = None,
        permissions: list = None,
    ) -> str:
        """Create a new API token.

        Args:
            name: Token name/description
            project: Optional project scope
            permissions: List of permissions

        Returns:
            The generated token
        """
        token = f"uf_{secrets.token_urlsafe(32)}"
        token_hash = self._hash_token(token)

        self.tokens[token_hash] = {
            "name": name,
            "project": project,
            "permissions": permissions or ["read", "write", "execute"],
            "created_at": datetime.now().isoformat(),
            "last_used": None,
        }

        self._save_tokens()
        return token

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify a token and return its metadata.

        Args:
            token: The token to verify

        Returns:
            Token metadata if valid, None otherwise
        """
        token_hash = self._hash_token(token)
        token_data = self.tokens.get(token_hash)

        if token_data:
            # Update last used timestamp
            token_data["last_used"] = datetime.now().isoformat()
            self.tokens[token_hash] = token_data
            self._save_tokens()

        return token_data

    def revoke_token(self, token: str) -> bool:
        """Revoke a token.

        Args:
            token: The token to revoke

        Returns:
            True if revoked, False if not found
        """
        token_hash = self._hash_token(token)
        if token_hash in self.tokens:
            del self.tokens[token_hash]
            self._save_tokens()
            return True
        return False

    def list_tokens(self) -> list:
        """List all tokens (without revealing the actual token values)."""
        return [
            {
                "name": data["name"],
                "project": data["project"],
                "permissions": data["permissions"],
                "created_at": data["created_at"],
                "last_used": data["last_used"],
            }
            for data in self.tokens.values()
        ]


# Global token manager instance
token_manager = TokenManager()


async def verify_api_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    required_permission: str = "read",
) -> dict[str, Any]:
    """Verify API token from Authorization header.

    Args:
        credentials: HTTP authorization credentials
        required_permission: Required permission level

    Returns:
        Token metadata

    Raises:
        HTTPException: If token is invalid or insufficient permissions
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Provide an API token in the Authorization header.",
        )

    token = credentials.credentials
    token_data = token_manager.verify_token(token)

    if not token_data:
        raise HTTPException(
            status_code=403,
            detail="Invalid API token",
        )

    # Check permissions
    if required_permission not in token_data["permissions"]:
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient permissions. Required: {required_permission}",
        )

    return token_data
