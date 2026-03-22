"""Tests for Prompt and Checkpoint asset types, and StackConfig hydration.

Covers:
- Prompt: creation, rendering, chat-style, variables, model config, lineage
- Checkpoint: creation, metrics, epoch/step, serialisation metadata
- StackConfig.to_stack(): local/GCP/AWS hydration, routing, context manager
- ComponentType enum expansion
"""

from __future__ import annotations

import os
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest


# ===========================================================================
# Prompt Asset Tests
# ===========================================================================


class TestPromptCreation:
    """Test Prompt asset instantiation."""

    def test_basic_text_prompt(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(name="hello", template="Hello {name}!")
        assert p.name == "hello"
        assert p.template == "Hello {name}!"
        assert p.prompt_format == "text"
        assert p.variables == ["name"]

    def test_chat_prompt(self):
        from flowyml.assets.prompt import Prompt

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Explain {topic}."},
        ]
        p = Prompt(name="chat", template=messages)
        assert p.prompt_format == "chat"
        assert p.metadata.properties["num_messages"] == 2
        assert p.metadata.properties["roles"] == ["system", "user"]

    def test_prompt_with_model_config(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(
            name="gpt4",
            template="Summarize: {text}",
            model="gpt-4",
            temperature=0.7,
            max_tokens=500,
        )
        assert p.model == "gpt-4"
        assert p.temperature == 0.7
        assert p.max_tokens == 500
        assert p.model_config == {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 500,
        }

    def test_create_factory(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt.create(
            template="Classify: {review}",
            name="classifier",
            model="gpt-3.5-turbo",
        )
        assert p.name == "classifier"
        assert p.model == "gpt-3.5-turbo"

    def test_create_auto_name(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt.create(template="Hello!")
        assert p.name.startswith("prompt_")

    def test_prompt_no_template(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(name="empty")
        assert p.template is None
        assert p.prompt_format == "text"  # default

    def test_prompt_repr(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(name="test", template="Hello {x}!", model="gpt-4")
        r = repr(p)
        assert "Prompt" in r
        assert "gpt-4" in r
        assert "test" in r

    def test_prompt_to_dict(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(name="td", template="Hi {user}!", model="gpt-4")
        d = p.to_dict()
        assert d["template"] == "Hi {user}!"
        assert d["model_config"]["model"] == "gpt-4"


class TestPromptRendering:
    """Test Prompt template rendering."""

    def test_render_text_template(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(name="r", template="Hello {name}! You are {age}.")
        result = p.render(name="Alice", age=30)
        assert result == "Hello Alice! You are 30."

    def test_render_chat_template(self):
        from flowyml.assets.prompt import Prompt

        messages = [
            {"role": "system", "content": "Help with {topic}."},
            {"role": "user", "content": "Tell me about {topic}."},
        ]
        p = Prompt(name="r", template=messages)
        result = p.render(topic="Python")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["content"] == "Help with Python."
        assert result[1]["content"] == "Tell me about Python."

    def test_render_no_template_raises(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(name="empty")
        with pytest.raises(ValueError, match="template"):
            p.render()


class TestPromptLineage:
    """Test Prompt lineage tracking."""

    def test_prompt_parent_child(self):
        from flowyml.assets.prompt import Prompt

        parent = Prompt(name="v1", template="Hello {x}!")
        child = Prompt(name="v2", template="Hi {x}!", parent=parent)

        assert parent in child.parents
        assert child in parent.children

    def test_prompt_version(self):
        from flowyml.assets.prompt import Prompt

        p = Prompt(name="test", template="Hi!", version="v2.0.0")
        assert p.version == "v2.0.0"


# ===========================================================================
# Checkpoint Asset Tests
# ===========================================================================


class TestCheckpointCreation:
    """Test Checkpoint asset instantiation."""

    def test_basic_checkpoint(self):
        from flowyml.assets.checkpoint import Checkpoint

        state = {"layer1.weight": [1, 2, 3], "layer1.bias": [0.1]}
        ckpt = Checkpoint(
            name="ckpt_1",
            data=state,
            epoch=5,
            step=2500,
        )
        assert ckpt.name == "ckpt_1"
        assert ckpt.epoch == 5
        assert ckpt.step == 2500
        assert ckpt.data == state
        assert ckpt.metadata.properties["num_tensors"] == 2

    def test_checkpoint_with_metrics(self):
        from flowyml.assets.checkpoint import Checkpoint

        ckpt = Checkpoint(
            name="best",
            data={"w": [1]},
            epoch=10,
            metrics={"loss": 0.05, "accuracy": 0.98},
            is_best=True,
        )
        assert ckpt.checkpoint_metrics == {"loss": 0.05, "accuracy": 0.98}
        assert ckpt.is_best is True
        assert ckpt.metadata.properties["is_best"] is True

    def test_create_factory(self):
        from flowyml.assets.checkpoint import Checkpoint

        ckpt = Checkpoint.create(
            data={"w": [1, 2]},
            name="factory_ckpt",
            epoch=3,
            step=1500,
        )
        assert ckpt.name == "factory_ckpt"
        assert ckpt.epoch == 3

    def test_create_auto_name(self):
        from flowyml.assets.checkpoint import Checkpoint

        ckpt = Checkpoint.create(data={"w": [1]}, epoch=7)
        assert "epoch7" in ckpt.name
        assert "checkpoint" in ckpt.name

    def test_checkpoint_state_keys_tracked(self):
        from flowyml.assets.checkpoint import Checkpoint

        state = {f"layer{i}.weight": [i] for i in range(5)}
        ckpt = Checkpoint(name="keys", data=state)
        assert "state_keys" in ckpt.metadata.properties
        assert len(ckpt.metadata.properties["state_keys"]) == 5

    def test_checkpoint_save(self, tmp_path):
        from flowyml.assets.checkpoint import Checkpoint

        ckpt = Checkpoint(
            name="save_test",
            data={"weights": [1, 2, 3]},
            epoch=1,
        )
        save_path = ckpt.save(tmp_path / "test.ckpt")
        assert save_path.exists()
        assert ckpt.file_path == str(save_path)

    def test_checkpoint_repr(self):
        from flowyml.assets.checkpoint import Checkpoint

        ckpt = Checkpoint(name="r", data={}, epoch=5, step=100, is_best=True)
        r = repr(ckpt)
        assert "epoch=5" in r
        assert "step=100" in r
        assert "best=True" in r

    def test_checkpoint_lineage(self):
        from flowyml.assets.checkpoint import Checkpoint
        from flowyml.assets.model import Model

        model_asset = Model(name="my_model", data=None, auto_extract=False)
        ckpt = Checkpoint(name="ckpt", data={"w": [1]}, parent=model_asset)

        assert model_asset in ckpt.parents


# ===========================================================================
# Package Export Tests
# ===========================================================================


class TestPackageExports:
    """Verify all assets are properly exported."""

    def test_assets_package_exports(self):
        from flowyml.assets import (
            Asset,
            AssetMetadata,
            Dataset,
            Model,
            Metrics,
            Artifact,
            FeatureSet,
            Report,
            Prompt,
            Checkpoint,
            AssetRegistry,
        )

        # just ensure all imports resolve
        assert all(
            [
                Asset,
                AssetMetadata,
                Dataset,
                Model,
                Metrics,
                Artifact,
                FeatureSet,
                Report,
                Prompt,
                Checkpoint,
                AssetRegistry,
            ],
        )

    def test_top_level_exports(self):
        from flowyml import Prompt, Checkpoint

        assert Prompt is not None
        assert Checkpoint is not None

    def test_component_type_enum(self):
        from flowyml.stacks.components import ComponentType

        assert ComponentType.MODEL_REGISTRY.value == "model_registry"
        assert ComponentType.EXPERIMENT_TRACKER.value == "experiment_tracker"


# ===========================================================================
# StackConfig Hydration Tests
# ===========================================================================


SAMPLE_YAML = textwrap.dedent(
    """\
    stacks:
      local:
        orchestrator: { type: local }
        artifact_store: { type: local, path: "./artifacts" }

      gcp-prod:
        orchestrator: { type: vertex_ai, project: my-gcp-project }
        artifact_store: { type: gcs, bucket: ml-artifacts }
        model_registry: { type: vertex_model_registry }
        model_deployer: { type: vertex_endpoint }
        experiment_tracker: { type: mlflow }
        artifact_routing:
          Model:   { store: gcs, register: true, deploy: true }
          Dataset: { store: gcs, path: "{run_id}/data/{step_name}" }
          Metrics: { log_to_tracker: true }

      aws-staging:
        orchestrator: { type: sagemaker, region: us-east-1 }
        artifact_store: { type: s3, bucket: staging-ml }
        model_registry: { type: sagemaker_model_registry }

    active_stack: local
""",
)


@pytest.fixture
def yaml_path(tmp_path):
    """Write sample YAML and return the file path."""
    p = tmp_path / "flowyml.yaml"
    p.write_text(SAMPLE_YAML)
    return str(p)


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons between tests."""
    import sys
    from flowyml.plugins.stack_config import StackManager

    StackManager.reset()

    # Also reset the global component registry so that @register_component
    # decorators in GCP/AWS modules fire again on next import.
    import flowyml.stacks.plugins as _plugins_mod

    _plugins_mod._global_component_registry = None

    # Remove cached provider modules so _ensure_providers_loaded() re-imports
    # them and their @register_component decorators fire on the fresh registry.
    for mod_name in list(sys.modules):
        if mod_name.startswith(("flowyml.stacks.gcp", "flowyml.stacks.aws", "flowyml.stacks.azure")):
            del sys.modules[mod_name]

    yield

    StackManager.reset()
    _plugins_mod._global_component_registry = None
    for mod_name in list(sys.modules):
        if mod_name.startswith(("flowyml.stacks.gcp", "flowyml.stacks.aws", "flowyml.stacks.azure")):
            del sys.modules[mod_name]


class TestStackYAMLParsing:
    """Ensure the YAML structure is correctly parsed into StackConfig objects."""

    def test_loads_all_stacks(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        assert set(manager.list_stacks()) == {"local", "gcp-prod", "aws-staging"}

    def test_active_stack(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        assert manager.active_stack_name == "local"

    def test_gcp_fields(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        gcp = manager.get_stack("gcp-prod")

        assert gcp.orchestrator["type"] == "vertex_ai"
        assert gcp.artifact_store["bucket"] == "ml-artifacts"
        assert gcp.model_registry == {"type": "vertex_model_registry"}
        assert gcp.experiment_tracker == {"type": "mlflow"}


class TestArtifactRouting:
    """Verify artifact_routing is parsed correctly."""

    def test_model_routing(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        gcp = manager.get_stack("gcp-prod")

        model_rule = gcp.get_routing_for_type("Model")
        assert model_rule is not None
        assert model_rule.store == "gcs"
        assert model_rule.register is True
        assert model_rule.deploy is True

    def test_no_routing_for_local(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        local = manager.get_stack("local")
        assert local.get_routing_for_type("Model") is None


class TestStackHydration:
    """Verify StackConfig.to_stack() produces live Stack objects."""

    def test_local_hydration(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager
        from flowyml.core.orchestrator import LocalOrchestrator

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        local_cfg = manager.get_stack("local")
        live = local_cfg.to_stack()

        assert live.name == "local"
        assert isinstance(live.orchestrator, LocalOrchestrator)
        assert live.artifact_store is not None
        assert live.metadata_store is not None

    def test_gcp_hydration(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager
        from flowyml.stacks.gcp import VertexAIOrchestrator, GCSArtifactStore

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        gcp_cfg = manager.get_stack("gcp-prod")
        live = gcp_cfg.to_stack()

        assert isinstance(live.orchestrator, VertexAIOrchestrator)
        assert live.orchestrator.project_id == "my-gcp-project"
        assert isinstance(live.artifact_store, GCSArtifactStore)
        assert live.artifact_store.bucket_name == "ml-artifacts"

    def test_aws_hydration(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager
        from flowyml.stacks.aws import SageMakerOrchestrator, S3ArtifactStore

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        aws_cfg = manager.get_stack("aws-staging")
        live = aws_cfg.to_stack()

        assert isinstance(live.orchestrator, SageMakerOrchestrator)
        assert live.orchestrator.region == "us-east-1"
        assert isinstance(live.artifact_store, S3ArtifactStore)
        assert live.artifact_store.bucket_name == "staging-ml"

    def test_routing_attached(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        gcp_cfg = manager.get_stack("gcp-prod")
        live = gcp_cfg.to_stack()

        assert live._artifact_routing is not None
        assert "Model" in live._artifact_routing.rules
        assert live._model_registry_config == {"type": "vertex_model_registry"}
        assert live._experiment_tracker_config == {"type": "mlflow"}


class TestStackSwitching:
    """Verify use_stack() context manager."""

    def test_context_manager(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)

        assert manager.active_stack_name == "local"
        with manager.use_stack("gcp-prod"):
            assert manager.active_stack_name == "gcp-prod"
        assert manager.active_stack_name == "local"

    def test_set_invalid_stack(self, yaml_path):
        from flowyml.plugins.config import PluginConfig
        from flowyml.plugins.stack_config import StackManager

        config = PluginConfig(yaml_path)
        manager = StackManager(config)
        assert not manager.set_active_stack("nonexistent")
