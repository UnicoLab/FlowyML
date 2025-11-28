"""Tests for pipeline execution API."""

import pytest
from starlette.testclient import TestClient
from uniflow.ui.backend.main import app
from uniflow.ui.backend.auth import TokenManager
from pathlib import Path


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_tokens_file(tmp_path):
    """Create temporary tokens file."""
    return str(tmp_path / "test_tokens.json")


@pytest.fixture
def admin_token(temp_tokens_file):
    """Create admin token for testing."""
    from uniflow.ui.backend.auth import token_manager

    token_manager.tokens_file = Path(temp_tokens_file)
    token_manager._load_tokens()

    return token_manager.create_token(
        name="Test Admin",
        permissions=["read", "write", "execute", "admin"],
    )


@pytest.fixture
def execute_token(temp_tokens_file):
    """Create execute token for testing."""
    from uniflow.ui.backend.auth import token_manager

    token_manager.tokens_file = Path(temp_tokens_file)
    token_manager._load_tokens()

    return token_manager.create_token(
        name="Test Execute",
        permissions=["read", "execute"],
    )


@pytest.fixture
def project_token(temp_tokens_file):
    """Create project-scoped token."""
    from uniflow.ui.backend.auth import token_manager

    token_manager.tokens_file = Path(temp_tokens_file)
    token_manager._load_tokens()

    return token_manager.create_token(
        name="Project Token",
        project="test_project",
        permissions=["read", "execute"],
    )


class TestTokenInitialization:
    """Test token initialization endpoint."""

    def test_create_initial_token(self, client, temp_tokens_file, monkeypatch):
        """Test creating the first admin token."""
        # Mock the token manager to use temp file
        from uniflow.ui.backend.auth import token_manager

        monkeypatch.setattr(token_manager, "tokens_file", Path(temp_tokens_file))
        monkeypatch.setattr(token_manager, "tokens", {})

        response = client.post("/api/execution/tokens/init")

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token"].startswith("uf_")
        assert "message" in data

    def test_cannot_create_second_initial_token(self, client, admin_token):
        """Test that initial token can only be created once."""
        response = client.post("/api/execution/tokens/init")

        assert response.status_code == 403
        assert "already exist" in response.json()["detail"]


class TestTokenManagement:
    """Test token management endpoints."""

    def test_create_token_with_admin(self, client, admin_token):
        """Test creating a new token with admin permissions."""
        response = client.post(
            "/api/execution/tokens",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New Token",
                "project": "my_project",
                "permissions": ["read", "write"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["name"] == "New Token"
        assert data["project"] == "my_project"

    def test_create_token_without_auth(self, client):
        """Test that creating token without auth fails."""
        response = client.post(
            "/api/execution/tokens",
            json={"name": "Test Token"},
        )

        assert response.status_code == 401

    def test_list_tokens_with_admin(self, client, admin_token):
        """Test listing tokens with admin permission."""
        response = client.get(
            "/api/execution/tokens",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert isinstance(data["tokens"], list)

    def test_list_tokens_without_admin(self, client, execute_token):
        """Test that listing tokens works without admin (changed for UI support)."""
        response = client.get(
            "/api/execution/tokens",
            headers={"Authorization": f"Bearer {execute_token}"},
        )

        # Changed: Now allows listing tokens without admin for UI to check if tokens exist
        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert isinstance(data["tokens"], list)


class TestPipelineExecution:
    """Test pipeline execution endpoint."""

    def test_execute_pipeline_dry_run(self, client, execute_token):
        """Test pipeline execution in dry-run mode."""
        response = client.post(
            "/api/execution/execute",
            headers={"Authorization": f"Bearer {execute_token}"},
            json={
                "pipeline_module": "test.pipeline",
                "pipeline_name": "test_pipeline",
                "parameters": {"epochs": 10},
                "dry_run": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "validated"
        assert data["pipeline"] == "test_pipeline"

    def test_execute_pipeline_without_auth(self, client):
        """Test that execution without auth fails."""
        response = client.post(
            "/api/execution/execute",
            json={
                "pipeline_module": "test.pipeline",
                "pipeline_name": "test_pipeline",
            },
        )

        assert response.status_code == 401

    def test_execute_pipeline_without_execute_permission(self, client):
        """Test that execution without execute permission fails."""
        from uniflow.ui.backend.auth import token_manager

        read_only_token = token_manager.create_token(
            name="Read Only",
            permissions=["read"],
        )

        response = client.post(
            "/api/execution/execute",
            headers={"Authorization": f"Bearer {read_only_token}"},
            json={
                "pipeline_module": "test.pipeline",
                "pipeline_name": "test_pipeline",
            },
        )

        assert response.status_code == 403

    def test_execute_with_wrong_project_scope(self, client, project_token):
        """Test that project-scoped token cannot execute in different project."""
        response = client.post(
            "/api/execution/execute",
            headers={"Authorization": f"Bearer {project_token}"},
            json={
                "pipeline_module": "test.pipeline",
                "pipeline_name": "test_pipeline",
                "project": "different_project",  # Token is scoped to test_project
            },
        )

        assert response.status_code == 403
        assert "scoped to project" in response.json()["detail"]

    def test_execute_with_correct_project_scope(self, client, project_token):
        """Test execution with matching project scope."""
        response = client.post(
            "/api/execution/execute",
            headers={"Authorization": f"Bearer {project_token}"},
            json={
                "pipeline_module": "test.pipeline",
                "pipeline_name": "test_pipeline",
                "project": "test_project",
                "dry_run": True,
            },
        )

        assert response.status_code == 200

    def test_execute_invalid_module(self, client, execute_token):
        """Test execution with invalid module."""
        response = client.post(
            "/api/execution/execute",
            headers={"Authorization": f"Bearer {execute_token}"},
            json={
                "pipeline_module": "nonexistent.module",
                "pipeline_name": "test_pipeline",
                "dry_run": False,
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestSecurityFeatures:
    """Test security features of the API."""

    def test_token_not_exposed_in_list(self, client, admin_token):
        """Test that actual tokens are never exposed in listings."""
        # Create a token
        client.post(
            "/api/execution/tokens",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Secret Token"},
        )

        # List tokens
        response = client.get(
            "/api/execution/tokens",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        data = response.json()
        for token_info in data["tokens"]:
            # Ensure no actual token value is present
            assert "token" not in token_info
            assert not any(val.startswith("uf_") for val in token_info.values() if isinstance(val, str))

    def test_token_hash_storage(self, temp_tokens_file):
        """Test that tokens are stored as hashes, not plaintext."""
        from uniflow.ui.backend.auth import TokenManager
        import json

        manager = TokenManager(tokens_file=temp_tokens_file)
        token = manager.create_token(name="Test")

        # Read the file directly
        with open(temp_tokens_file, "r") as f:
            stored_data = json.load(f)

        # Check that the actual token is not in the file
        file_content = json.dumps(stored_data)
        assert token not in file_content

        # But we should have a hash
        assert len(stored_data) > 0


class TestAPIIntegration:
    """Integration tests for the complete API flow."""

    def test_complete_workflow(self, client, temp_tokens_file, monkeypatch):
        """Test complete workflow: init -> create token -> execute."""
        from uniflow.ui.backend.auth import token_manager

        monkeypatch.setattr(token_manager, "tokens_file", Path(temp_tokens_file))
        monkeypatch.setattr(token_manager, "tokens", {})

        # 1. Initialize first token
        init_response = client.post("/api/execution/tokens/init")
        assert init_response.status_code == 200
        admin_token = init_response.json()["token"]

        # 2. Create execute token
        create_response = client.post(
            "/api/execution/tokens",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Execute Token",
                "permissions": ["read", "execute"],
            },
        )
        assert create_response.status_code == 200
        exec_token = create_response.json()["token"]

        # 3. Execute pipeline (dry run)
        exec_response = client.post(
            "/api/execution/execute",
            headers={"Authorization": f"Bearer {exec_token}"},
            json={
                "pipeline_module": "test.module",
                "pipeline_name": "test_pipeline",
                "dry_run": True,
            },
        )
        assert exec_response.status_code == 200
        assert exec_response.json()["status"] == "validated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
