import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from flowyml.storage.remote import RemoteArtifactStore, RemoteMetadataStore


@pytest.fixture
def mock_requests():
    with patch("flowyml.storage.remote.requests") as mock:
        yield mock


@pytest.fixture
def mock_tempfile():
    with patch("flowyml.storage.remote.tempfile") as mock:
        yield mock


def test_remote_artifact_store_materialize(mock_requests):
    store = RemoteArtifactStore(api_url="http://test-server/api")
    obj = {"data": "test"}

    # Mock API responses
    mock_requests.Session.return_value.post.return_value.json.return_value = {"path": "remote/path"}
    mock_requests.Session.return_value.post.return_value.status_code = 200

    remote_path = store.materialize(obj, "test_artifact", "run_1", "step_1")

    assert remote_path == "remote/path"
    # Verify metadata creation
    args, kwargs = mock_requests.Session.return_value.post.call_args_list[0]
    assert "assets/" in args[0]
    assert kwargs["json"]["name"] == "test_artifact"

    # Verify upload
    args, kwargs = mock_requests.Session.return_value.post.call_args_list[1]
    assert "upload" in args[0]
    assert "file" in kwargs["files"]


def test_remote_artifact_store_load(mock_requests):
    store = RemoteArtifactStore(api_url="http://test-server/api", local_cache_dir="/tmp/cache")

    # Mock download response
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"content"]
    mock_response.headers = {"content-disposition": 'filename="test.pkl"'}
    mock_response.status_code = 200
    mock_requests.Session.return_value.get.return_value = mock_response

    # Mock pickle load
    with patch("builtins.open", MagicMock()), patch("pickle.load", return_value={"data": "loaded"}), patch(
        "pathlib.Path.mkdir",
    ):
        result = store.load("project/run/id/file")
        assert result == {"data": "loaded"}


def test_remote_artifact_store_delete(mock_requests):
    store = RemoteArtifactStore(api_url="http://test-server/api")

    # Mock metadata lookup
    mock_requests.Session.return_value.get.return_value.json.return_value = {"artifact_id": "art_1"}
    mock_requests.Session.return_value.get.return_value.status_code = 200

    store.delete("project/run/art_1/file")

    mock_requests.Session.return_value.delete.assert_called()
    args, _ = mock_requests.Session.return_value.delete.call_args
    assert "assets/art_1" in args[0]


def test_remote_metadata_list_pipelines(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")

    # Mock responses: 1. Pipelines endpoint (404), 2. Runs endpoint (200)
    response_404 = MagicMock()
    response_404.status_code = 404

    response_runs = MagicMock()
    response_runs.status_code = 200
    response_runs.json.return_value = {
        "runs": [
            {"pipeline_name": "p1"},
            {"pipeline_name": "p2"},
            {"pipeline_name": "p1"},
        ],
    }

    mock_requests.Session.return_value.get.side_effect = [response_404, response_runs]

    pipelines = store.list_pipelines()
    assert pipelines == ["p1", "p2"]


def test_remote_artifact_store_save_creates_metadata(mock_requests):
    store = RemoteArtifactStore(api_url="http://test-server/api")
    obj = {"data": "test"}

    # Mock metadata check returning None (not found)
    mock_requests.Session.return_value.get.return_value.status_code = 404

    # Mock upload response
    mock_requests.Session.return_value.post.return_value.json.return_value = {"path": "remote/path"}
    mock_requests.Session.return_value.post.return_value.status_code = 200

    store.save(obj, "path/to/artifact", metadata={"name": "test", "artifact_id": "art_1"})

    # Verify metadata creation was called
    calls = mock_requests.Session.return_value.post.call_args_list
    # First call should be metadata creation
    assert "assets/" in calls[0][0][0]
    assert calls[0][1]["json"]["artifact_id"] == "art_1"

    # Second call should be upload
    assert "upload" in calls[1][0][0]


def test_remote_artifact_store_load_uses_materializer(mock_requests):
    store = RemoteArtifactStore(api_url="http://test-server/api", local_cache_dir="/tmp/cache")

    # Mock metadata response with type info
    metadata_response = MagicMock(
        status_code=200,
        json=lambda: {
            "artifact_id": "art_1",
            "metadata": {
                "type_module": "builtins",
                "type_name": "dict",
            },
        },
    )

    download_response = MagicMock(
        status_code=200,
        iter_content=lambda chunk_size: [b"content"],
        headers={"content-disposition": 'filename="test.json"'},
    )

    mock_requests.Session.return_value.get.side_effect = [
        metadata_response,  # 1. Initial check
        metadata_response,  # 2. Metadata load
        download_response,  # 3. Download
    ]

    # Mock file operations and materializer
    with patch("builtins.open", MagicMock()), patch("pathlib.Path.mkdir"), patch(
        "flowyml.storage.materializers.base.get_materializer_by_type_name",
    ) as mock_get_mat:
        # Setup mock materializer
        mock_mat_instance = MagicMock()
        mock_mat_instance.load.return_value = {"loaded": "data"}
        mock_get_mat.return_value = mock_mat_instance

        result = store.load("art_1")

        assert result == {"loaded": "data"}
        mock_get_mat.assert_called_with("builtins.dict")
        mock_mat_instance.load.assert_called()


def test_remote_metadata_list_runs_filtering(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")

    mock_requests.Session.return_value.get.return_value.json.return_value = {"runs": []}
    mock_requests.Session.return_value.get.return_value.status_code = 200

    store.list_runs(pipeline_name="p1", status="completed")

    args, kwargs = mock_requests.Session.return_value.get.call_args
    assert kwargs["params"]["pipeline_name"] == "p1"
    assert kwargs["params"]["status"] == "completed"


def test_remote_metadata_list_pipelines_endpoint(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")

    # Clear any previous side effects
    mock_requests.Session.return_value.get.side_effect = None

    mock_requests.Session.return_value.get.return_value.json.return_value = {
        "pipelines": [{"name": "p1"}, {"name": "p2"}],
    }
    mock_requests.Session.return_value.get.return_value.status_code = 200

    pipelines = store.list_pipelines()

    assert pipelines == ["p1", "p2"]
    args, _ = mock_requests.Session.return_value.get.call_args
    assert "pipelines/" in args[0]
