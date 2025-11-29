"""Simple integration tests for auth that don't require TestClient."""

import pytest
from pathlib import Path
from flowyml.ui.backend.auth import TokenManager


def test_token_creation_and_verification(tmp_path):
    """Test creating and verifying tokens."""
    tokens_file = str(tmp_path / "tokens.json")
    manager = TokenManager(tokens_file=tokens_file)

    # Create token
    token = manager.create_token(
        name="Test Token",
        permissions=["read", "write"],
    )

    assert token.startswith("uf_")

    # Verify token
    data = manager.verify_token(token)
    assert data is not None
    assert data["name"] == "Test Token"
    assert "read" in data["permissions"]
    assert "write" in data["permissions"]


def test_token_revocation(tmp_path):
    """Test revoking tokens."""
    tokens_file = str(tmp_path / "tokens.json")
    manager = TokenManager(tokens_file=tokens_file)

    token = manager.create_token(name="Revoke Me")

    # Verify exists
    assert manager.verify_token(token) is not None

    # Revoke
    assert manager.revoke_token(token) is True

    # Verify gone
    assert manager.verify_token(token) is None


def test_project_scoped_tokens(tmp_path):
    """Test project-scoped tokens."""
    tokens_file = str(tmp_path / "tokens.json")
    manager = TokenManager(tokens_file=tokens_file)

    # Create project-scoped token
    token = manager.create_token(
        name="Project Token",
        project="ml_project",
        permissions=["execute"],
    )

    data = manager.verify_token(token)
    assert data["project"] == "ml_project"
    assert "execute" in data["permissions"]


def test_list_tokens_hides_values(tmp_path):
    """Test that listing tokens doesn't expose actual token values."""
    tokens_file = str(tmp_path / "tokens.json")
    manager = TokenManager(tokens_file=tokens_file)

    token1 = manager.create_token(name="MyToken1")
    token2 = manager.create_token(name="MyToken2")

    tokens_list = manager.list_tokens()
    assert len(tokens_list) == 2

    # Check no actual tokens in the list (tokens start with "uf_")
    for token_info in tokens_list:
        values = [v for v in token_info.values() if isinstance(v, str)]
        # The actual secret tokens start with "uf_" - make sure none are in the list
        assert not any(v.startswith("uf_") for v in values)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
