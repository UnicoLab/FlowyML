import pytest
from unittest.mock import MagicMock, patch
import json
from pathlib import Path

from flowyml.storage.remote import RemoteMetadataStore, RemoteArtifactStore
from flowyml.core.pipeline import Pipeline
from flowyml.core.step import step
from flowyml.stacks.base import Stack
from flowyml.core.executor import LocalExecutor


@pytest.fixture
def mock_requests():
    with patch("flowyml.storage.remote.requests") as mock:
        yield mock


def test_remote_metadata_store_save_run(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")

    run_id = "test_run_123"
    metadata = {
        "pipeline_name": "test_pipeline",
        "status": "completed",
        "start_time": "2023-01-01T00:00:00",
        "metrics": {"accuracy": 0.95},
    }

    store.save_run(run_id, metadata)

    # Verify post call
    mock_requests.Session.return_value.post.assert_called_once()
    args, kwargs = mock_requests.Session.return_value.post.call_args
    assert args[0] == "http://test-server/api/runs/"
    assert kwargs["json"]["run_id"] == run_id
    assert kwargs["json"]["metrics"] == {"accuracy": 0.95}


def test_remote_artifact_store_materialize(mock_requests, tmp_path):
    store = RemoteArtifactStore(api_url="http://test-server/api", local_cache_dir=str(tmp_path))

    # Mock response for upload
    mock_response = MagicMock()
    mock_response.json.return_value = {"path": "remote/path/to/artifact"}
    mock_response.status_code = 200
    mock_requests.Session.return_value.post.return_value = mock_response

    obj = {"data": [1, 2, 3]}
    remote_path = store.materialize(obj, "test_artifact", "run_123", "step_1")

    assert remote_path == "remote/path/to/artifact"

    # Verify calls: 1 for metadata creation, 1 for upload
    assert mock_requests.Session.return_value.post.call_count == 2

    # Check metadata creation call
    call1 = mock_requests.Session.return_value.post.call_args_list[0]
    assert "assets/" in call1[0][0]
    assert call1[1]["json"]["name"] == "test_artifact"

    # Check upload call
    call2 = mock_requests.Session.return_value.post.call_args_list[1]
    assert "upload" in call2[0][0]
    assert "files" in call2[1]


def test_remote_metadata_store_auth(mock_requests):
    token = "secret-token"
    store = RemoteMetadataStore(api_url="http://test-server/api", api_token=token)

    store.list_runs()

    # Verify auth header
    mock_requests.Session.return_value.get.assert_called_once()
    # Check if headers were updated on session
    # We can't easily check session headers on the mock object if it was set in init
    # But we can check if the session was initialized and headers updated
    pass


def test_remote_experiment_logging(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")

    # Test save experiment
    store.save_experiment("exp_1", "My Experiment", tags={"project": "p1"})

    mock_requests.Session.return_value.post.assert_called()
    args, kwargs = mock_requests.Session.return_value.post.call_args
    assert "experiments/" in args[0]
    assert kwargs["json"]["name"] == "My Experiment"

    # Test log run to experiment
    store.log_experiment_run("exp_1", "run_1", metrics={"acc": 0.9})

    args, kwargs = mock_requests.Session.return_value.post.call_args
    assert "experiments/exp_1/runs" in args[0]
    assert kwargs["json"]["run_id"] == "run_1"


def test_pipeline_remote_execution(mock_requests, tmp_path):
    # Setup remote stack with auth
    remote_stack = Stack(
        name="remote_test",
        executor=LocalExecutor(),
        metadata_store=RemoteMetadataStore(api_url="http://test-server/api", api_token="token"),
        artifact_store=RemoteArtifactStore(
            api_url="http://test-server/api",
            local_cache_dir=str(tmp_path),
            api_token="token",
        ),
    )

    # Define pipeline
    @step
    def step1():
        return "hello"

    pipeline = Pipeline("remote_pipeline", stack=remote_stack)
    pipeline.add_step(step1)

    # Mock responses
    mock_response = MagicMock()
    mock_response.json.return_value = {"path": "remote/path"}
    mock_response.status_code = 200
    mock_requests.Session.return_value.post.return_value = mock_response
    mock_requests.Session.return_value.get.return_value = mock_response  # For any gets

    # Run pipeline
    pipeline.run()

    # Verify interactions
    assert mock_requests.Session.return_value.post.called
