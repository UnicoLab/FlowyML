"""Tests for pipeline resource and docker configuration handling."""

from flowyml import Pipeline, step
from flowyml.core.context import Context
from flowyml.storage.artifacts import LocalArtifactStore
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.stacks.base import Stack
from flowyml.stacks.components import Orchestrator, ResourceConfig, DockerConfig
from tests.base import BaseTestCase


class DummyOrchestrator(Orchestrator):
    """Simple orchestrator that records submissions."""

    def __init__(self):
        super().__init__("dummy")
        self.last_payload = None

    def validate(self) -> bool:
        return True

    def run_pipeline(self, pipeline, resources=None, docker_config=None, **kwargs):
        self.last_payload = {
            "pipeline": pipeline.name,
            "resources": resources,
            "docker": docker_config,
            "kwargs": kwargs,
        }
        return "job-dummy"

    def get_run_status(self, run_id: str) -> str:
        return "SUBMITTED"

    def to_dict(self) -> dict:
        return {"name": self.name, "type": "dummy"}


class DummyRemoteStack(Stack):
    """Stack without an executor that relies on the orchestrator."""

    def __init__(self, base_path):
        orchestrator = DummyOrchestrator()
        artifact_store = LocalArtifactStore(str(base_path / "remote_artifacts"))
        metadata_store = SQLiteMetadataStore(str(base_path / "remote_metadata.db"))
        super().__init__(
            name="dummy-remote",
            executor=None,
            artifact_store=artifact_store,
            metadata_store=metadata_store,
            orchestrator=orchestrator,
        )
        self.orchestrator = orchestrator


class TestPipelineResourceHandling(BaseTestCase):
    """Validate pipeline control over resources and docker configs."""

    def test_remote_submission_records_configs(self):
        stack = DummyRemoteStack(self.test_path)

        @step
        def noop():
            return {}

        pipeline = Pipeline("remote-control", stack=stack, context=Context(project="demo"))
        pipeline.add_step(noop)

        res_cfg = ResourceConfig(cpu="8", memory="32Gi", gpu="nvidia-tesla-t4", gpu_count=1)
        docker_cfg = DockerConfig(image="gcr.io/demo/train:latest", env_vars={"ENV": "prod"})

        result = pipeline.run(resources=res_cfg, docker_config=docker_cfg)

        self.assertEqual(result.state, "submitted")
        self.assertEqual(result.remote_job_id, "job-dummy")
        self.assertEqual(result.resource_config, res_cfg)
        self.assertEqual(result.docker_config, docker_cfg)
        self.assertEqual(stack.orchestrator.last_payload["resources"], res_cfg)
        self.assertEqual(stack.orchestrator.last_payload["docker"], docker_cfg)

    def test_dict_inputs_are_coerced(self):
        stack = DummyRemoteStack(self.test_path)

        @step
        def noop():
            return {}

        pipeline = Pipeline("dict-control", stack=stack, context=Context(foo="bar"))
        pipeline.add_step(noop)

        result = pipeline.run(
            resources={"cpu": "10", "memory": "64Gi"},
            docker_config={"image": "gcr.io/demo/test:latest"},
        )

        self.assertEqual(result.resource_config.cpu, "10")
        self.assertEqual(result.resource_config.memory, "64Gi")
        self.assertEqual(result.docker_config.image, "gcr.io/demo/test:latest")
        self.assertEqual(stack.orchestrator.last_payload["resources"].cpu, "10")
        self.assertEqual(stack.orchestrator.last_payload["docker"].image, "gcr.io/demo/test:latest")
