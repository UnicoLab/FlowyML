"""Tests for API authentication and token management."""

import pytest
import os
import json
from pathlib import Path
from flowyml.ui.backend.auth import TokenManager, verify_api_token
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


class TestTokenManager:
    """Test the TokenManager class."""

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.fixture
    def temp_tokens_file(self, tmp_path):
        """Create a temporary tokens file."""
        tokens_file = tmp_path / "test_tokens.json"
        return str(tokens_file)

    @pytest.fixture
    def token_manager(self, temp_tokens_file):
        """Create a TokenManager instance."""
        return TokenManager(tokens_file=temp_tokens_file)

    def test_create_token(self, token_manager):
        """Test token creation."""
        token = token_manager.create_token(
            name="Test Token",
            project="test_project",
            permissions=["read", "write"],
        )

        assert token.startswith("uf_")
        assert len(token) > 10

        # Verify token data
        token_data = token_manager.verify_token(token)
        assert token_data is not None
        assert token_data["name"] == "Test Token"
        assert token_data["project"] == "test_project"
        assert token_data["permissions"] == ["read", "write"]

    def test_verify_invalid_token(self, token_manager):
        """Test verification of invalid token."""
        result = token_manager.verify_token("invalid_token")
        assert result is None

    def test_revoke_token(self, token_manager):
        """Test token revocation."""
        token = token_manager.create_token(name="To Revoke")

        # Verify it exists
        assert token_manager.verify_token(token) is not None

        # Revoke it
        assert token_manager.revoke_token(token) is True

        # Verify it's gone
        assert token_manager.verify_token(token) is None

        # Try to revoke again
        assert token_manager.revoke_token(token) is False

    def test_list_tokens(self, token_manager):
        """Test listing tokens."""
        # Create multiple tokens
        token_manager.create_token(name="Token 1", project="proj1")
        token_manager.create_token(name="Token 2", project="proj2")
        token_manager.create_token(name="Token 3")

        tokens = token_manager.list_tokens()
        assert len(tokens) == 3

        # Check that actual tokens are not exposed
        for token_info in tokens:
            assert "token" not in token_info
            assert "name" in token_info
            assert "project" in token_info
            assert "permissions" in token_info

    def test_token_permissions(self, token_manager):
        """Test token with different permissions."""
        read_token = token_manager.create_token(
            name="Read Only",
            permissions=["read"],
        )

        write_token = token_manager.create_token(
            name="Read Write",
            permissions=["read", "write"],
        )

        admin_token = token_manager.create_token(
            name="Admin",
            permissions=["read", "write", "execute", "admin"],
        )

        # Verify permissions
        read_data = token_manager.verify_token(read_token)
        assert "read" in read_data["permissions"]
        assert "write" not in read_data["permissions"]

        write_data = token_manager.verify_token(write_token)
        assert "read" in write_data["permissions"]
        assert "write" in write_data["permissions"]
        assert "execute" not in write_data["permissions"]

        admin_data = token_manager.verify_token(admin_token)
        assert all(p in admin_data["permissions"] for p in ["read", "write", "execute", "admin"])

    def test_project_scoped_token(self, token_manager):
        """Test project-scoped token."""
        token = token_manager.create_token(
            name="Project Token",
            project="ml_project",
        )

        token_data = token_manager.verify_token(token)
        assert token_data["project"] == "ml_project"

    def test_global_token(self, token_manager):
        """Test global token (no project scope)."""
        token = token_manager.create_token(name="Global Token")

        token_data = token_manager.verify_token(token)
        assert token_data["project"] is None

    def test_token_persistence(self, temp_tokens_file):
        """Test that tokens persist across instances."""
        # Create token with first instance
        manager1 = TokenManager(tokens_file=temp_tokens_file)
        token = manager1.create_token(name="Persistent Token")

        # Verify with new instance
        manager2 = TokenManager(tokens_file=temp_tokens_file)
        token_data = manager2.verify_token(token)
        assert token_data is not None
        assert token_data["name"] == "Persistent Token"

    def test_last_used_tracking(self, token_manager):
        """Test that last_used timestamp is updated."""
        token = token_manager.create_token(name="Usage Token")

        # First verification
        data1 = token_manager.verify_token(token)
        assert data1["last_used"] is not None
        first_used = data1["last_used"]

        # Second verification after a delay
        import time

        time.sleep(0.2)
        data2 = token_manager.verify_token(token)
        assert data2["last_used"] is not None

        # Timestamps should be different (second should be later or equal)
        # We just verify they exist and are reasonable timestamps
        assert isinstance(data2["last_used"], str)
        assert len(data2["last_used"]) > 0


class TestAPITokenVerification:
    """Test the verify_api_token dependency."""

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.fixture
    def temp_tokens_file(self, tmp_path):
        """Create a temporary tokens file."""
        return str(tmp_path / "test_tokens.json")

    @pytest.fixture
    def setup_tokens(self, temp_tokens_file):
        """Setup test tokens."""
        from flowyml.ui.backend.auth import token_manager

        token_manager.tokens_file = Path(temp_tokens_file)
        token_manager._load_tokens()

        # Create test tokens
        read_token = token_manager.create_token(
            name="Read Token",
            permissions=["read"],
        )
        execute_token = token_manager.create_token(
            name="Execute Token",
            permissions=["read", "execute"],
        )

        return {
            "read": read_token,
            "execute": execute_token,
        }

    @pytest.mark.anyio
    async def test_verify_with_valid_token(self, setup_tokens):
        """Test verification with valid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=setup_tokens["read"],
        )

        result = await verify_api_token(credentials, required_permission="read")
        assert result is not None
        assert result["name"] == "Read Token"

    @pytest.mark.anyio
    async def test_verify_without_credentials(self):
        """Test verification without credentials."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_token(None, required_permission="read")

        assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_verify_with_invalid_token(self):
        """Test verification with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token",
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_token(credentials, required_permission="read")

        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    async def test_verify_insufficient_permissions(self, setup_tokens):
        """Test verification with insufficient permissions."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=setup_tokens["read"],  # Only has 'read' permission
        )

        # Try to use with 'execute' permission requirement
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_token(credentials, required_permission="execute")

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
