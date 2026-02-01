"""Verification tests for MLOps lifecycle equality components."""
import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock external libs
sys.modules["deepchecks"] = MagicMock()
mock_tabular = MagicMock()


class MockDataset:
    pass


mock_tabular.Dataset = MockDataset
# We need to satisfy 'from deepchecks.tabular import suites' and 'Dataset'
# The import logic in the plugin does: from deepchecks.tabular import Dataset, Suite; from deepchecks.tabular import suites
# So sys.modules["deepchecks.tabular"] must have these attributes.
sys.modules["deepchecks.tabular"] = mock_tabular
sys.modules["mlflow"] = MagicMock()
sys.modules["mlflow.tracking"] = MagicMock()

from flowyml.plugins.alerters.slack import SlackAlerter
from flowyml.plugins.validators.deepchecks import DeepchecksValidator
from flowyml.plugins.model_registries.mlflow import MLflowModelRegistry
from flowyml.plugins.base import PluginType


def test_slack_alerter():
    """Verify Slack Alerter initialization and validation."""
    # Test valid init with webhook
    alerter = SlackAlerter(webhook_url="https://hooks.slack.com/services/...")
    assert alerter.plugin_type == PluginType.ALERTER
    assert alerter.validate() is True

    # Test valid init with token
    alerter_token = SlackAlerter(token="xoxb-...", default_channel="#general")
    assert alerter_token.validate() is True

    # Test invalid init
    with pytest.raises(ValueError):
        SlackAlerter().validate()

    with pytest.raises(ValueError):
        SlackAlerter(token="xoxb-...").validate()  # Missing channel

    # Mock urllib to test send
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        success = alerter.send_alert("Test", "Message")
        assert success is True


def test_deepchecks_validator():
    """Verify Deepchecks Validator initialization."""
    validator = DeepchecksValidator(suite="integrity")
    assert validator.plugin_type == PluginType.DATA_VALIDATOR

    # Mock deepchecks internals to test validate() run path
    validator._dc_suites = MagicMock()
    # No need to manually set _dc_dataset here, initialize() will pick up the class from sys.modules

    # Mock suite run
    mock_suite = MagicMock()
    mock_result = MagicMock()
    mock_result.passed.return_value = True
    mock_result.to_json.return_value = "{}"
    mock_suite.run.return_value = mock_result

    # Setup suite factory ON THE SYS MODULES MOCK because initialize() reloads it
    mock_tabular.suites.integrity.return_value = mock_suite

    # Run validate
    # Pass a specific expectation string to avoid default logic issues in test
    data = MockDataset()
    res = validator.validate(data=data, expectations="integrity")

    assert res["passed"] is True
    assert res["suite_name"] == "integrity"


def test_mlflow_registry():
    """Verify MLflow Registry structure."""
    registry = MLflowModelRegistry(registry_uri="sqlite:///mlflow.db")
    assert registry.plugin_type == PluginType.MODEL_REGISTRY

    # Mock client
    registry._client = MagicMock()

    # Test register model flow
    registry.initialize()  # Should setup client
    registry.register_model("model_name", "runs:/123/model")

    # Verify client calls
    registry._client.create_model_version.assert_called_once()
