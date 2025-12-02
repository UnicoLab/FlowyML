import pytest
from unittest.mock import MagicMock, patch
from flowyml.storage.remote import RemoteMetadataStore


@pytest.fixture
def mock_requests():
    with patch("flowyml.storage.remote.requests") as mock:
        yield mock


def test_save_trace_event(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")
    event = {
        "event_id": "evt_1",
        "trace_id": "trace_1",
        "event_type": "llm",
        "name": "completion",
        "start_time": 100.0,
    }

    store.save_trace_event(event)

    mock_requests.Session.return_value.post.assert_called()
    args, kwargs = mock_requests.Session.return_value.post.call_args
    assert "traces/" in args[0]
    assert kwargs["json"]["event_id"] == "evt_1"


def test_save_pipeline_definition(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")
    definition = {"steps": ["step1", "step2"]}

    store.save_pipeline_definition("pipeline_1", definition)

    mock_requests.Session.return_value.post.assert_called()
    args, kwargs = mock_requests.Session.return_value.post.call_args
    assert "pipelines/" in args[0]
    assert kwargs["json"]["pipeline_name"] == "pipeline_1"
    assert kwargs["json"]["definition"] == definition


def test_update_pipeline_project(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")

    store.update_pipeline_project("pipeline_1", "new_project")

    mock_requests.Session.return_value.put.assert_called()
    args, kwargs = mock_requests.Session.return_value.put.call_args
    assert "pipelines/pipeline_1/project" in args[0]
    assert kwargs["json"]["project_name"] == "new_project"


def test_get_statistics(mock_requests):
    store = RemoteMetadataStore(api_url="http://test-server/api")
    mock_response = MagicMock()
    mock_response.json.return_value = {"total_runs": 10}
    mock_response.status_code = 200
    mock_requests.Session.return_value.get.return_value = mock_response

    stats = store.get_statistics()

    mock_requests.Session.return_value.get.assert_called()
    args, _ = mock_requests.Session.return_value.get.call_args
    assert "stats/" in args[0]
    assert stats["total_runs"] == 10
