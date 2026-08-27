"""Authentication and authorization for flowyml API."""

import contextlib
import os
import secrets
import hashlib
import json
import tempfile
import threading
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from loguru import logger

security = HTTPBearer(auto_error=False)

#: Permissions the API recognises. Anything else is rejected at creation time
#: so a typo such as "admln" cannot silently produce a token that passes no
#: check but looks privileged in the UI.
VALID_PERMISSIONS = frozenset({"read", "write", "execute", "admin"})

#: How stale a token's ``last_used`` timestamp may become before it is
#: rewritten. Persisting on every request turned each authenticated API call
#: into a synchronous rewrite of the whole token file.
LAST_USED_WRITE_INTERVAL = timedelta(minutes=5)


class TokenManager:
    """Manage API tokens for authentication."""

    def __init__(self, tokens_file: str | None = None):
        if tokens_file is None:
            tokens_file = os.getenv("FLOWYML_TOKENS_FILE", ".flowyml/api_tokens.json")
        self.tokens_file = Path(tokens_file)
        self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
        # Token hashes are verifiers: guard the file against other local users.
        self._restrict_permissions(self.tokens_file.parent, 0o700)
        # Guards read-modify-write cycles against concurrent request handlers.
        self._lock = threading.Lock()
        # Last time each token's ``last_used`` timestamp was flushed to disk.
        self._last_persisted: dict[str, datetime] = {}
        self._load_tokens()

    @staticmethod
    def _restrict_permissions(path: Path, mode: int) -> None:
        """Best-effort tightening of filesystem permissions.

        Silently ignored on platforms without POSIX permissions (Windows) and
        on filesystems that reject chmod, since failing here would make the
        server unusable for a defence-in-depth measure.
        """
        try:
            if path.exists():
                path.chmod(mode)
        except (OSError, NotImplementedError):  # pragma: no cover - platform dependent
            pass

    def _load_tokens(self) -> None:
        """Load tokens from file."""
        if self.tokens_file.exists():
            try:
                with open(self.tokens_file) as f:
                    content = f.read().strip()
                    if not content:
                        self.tokens = {}
                        self._save_tokens()
                    else:
                        self.tokens = json.loads(content)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load tokens from {self.tokens_file}: {e}")
                self.tokens = {}
                self._save_tokens()
        else:
            self.tokens = {}
            self._save_tokens()

    def _save_tokens(self) -> None:
        """Persist tokens atomically.

        Writing in place truncates the file before the new content lands, so a
        crash or a concurrent reader during the write window would see an empty
        or half-written token store and lock every client out. Writing to a
        temporary file in the same directory and renaming it makes the
        replacement atomic on POSIX filesystems.
        """
        directory = self.tokens_file.parent
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(directory),
            prefix=self.tokens_file.name,
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(self.tokens, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, self.tokens_file)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

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
        requested = list(permissions) if permissions is not None else ["read", "write", "execute"]
        unknown = sorted(set(requested) - VALID_PERMISSIONS)
        if unknown:
            raise ValueError(
                f"Unknown permission(s): {unknown}. Valid permissions are "
                f"{sorted(VALID_PERMISSIONS)}.",
            )

        token = f"uf_{secrets.token_urlsafe(32)}"
        token_hash = self._hash_token(token)

        with self._lock:
            self.tokens[token_hash] = {
                "name": name,
                "project": project,
                "permissions": requested,
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

        if token_data is None:
            return None

        now = datetime.now()
        token_data["last_used"] = now.isoformat()

        # Persist the timestamp at most once per LAST_USED_WRITE_INTERVAL.
        # Rewriting the whole token store on every authenticated request made
        # each API call wait on a synchronous fsync, and concurrent requests
        # raced on the same file.
        if self._should_persist_last_used(token_hash, now):
            with self._lock:
                self._last_persisted[token_hash] = now
                self._save_tokens()

        return token_data

    def _should_persist_last_used(self, token_hash: str, now: datetime) -> bool:
        previous = self._last_persisted.get(token_hash)
        return previous is None or (now - previous) >= LAST_USED_WRITE_INTERVAL

    def revoke_token(self, token: str) -> bool:
        """Revoke a token.

        Args:
            token: The token to revoke

        Returns:
            True if revoked, False if not found
        """
        token_hash = self._hash_token(token)
        with self._lock:
            if token_hash in self.tokens:
                del self.tokens[token_hash]
                self._last_persisted.pop(token_hash, None)
                self._save_tokens()
                return True
        return False

    def revoke_token_by_id(self, token_id: str) -> bool:
        """Revoke the token with the given public identifier.

        ``list_tokens`` never reveals token values, so the UI cannot call
        :meth:`revoke_token`. The identifier is a truncated hash of the hashed
        token: enough to address a token, useless for reconstructing one.
        """
        with self._lock:
            for token_hash in list(self.tokens):
                if self._public_id(token_hash) == token_id:
                    del self.tokens[token_hash]
                    self._last_persisted.pop(token_hash, None)
                    self._save_tokens()
                    return True
        return False

    def revoke_tokens_by_name(self, name: str) -> int:
        """Revoke every token with the given name, returning how many were removed.

        Names are user-supplied labels and are not required to be unique, so
        this deliberately revokes all matches rather than picking one
        arbitrarily.
        """
        with self._lock:
            matching = [h for h, data in self.tokens.items() if data.get("name") == name]
            for token_hash in matching:
                del self.tokens[token_hash]
                self._last_persisted.pop(token_hash, None)
            if matching:
                self._save_tokens()
        return len(matching)

    @staticmethod
    def _public_id(token_hash: str) -> str:
        """Derive a stable, non-secret identifier from a stored token hash."""
        return hashlib.sha256(f"id:{token_hash}".encode()).hexdigest()[:16]

    def list_tokens(self) -> list:
        """List all tokens (without revealing the actual token values)."""
        return [
            {
                "id": self._public_id(token_hash),
                "name": data["name"],
                "project": data["project"],
                "permissions": data["permissions"],
                "created_at": data["created_at"],
                "last_used": data["last_used"],
            }
            for token_hash, data in self.tokens.items()
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
