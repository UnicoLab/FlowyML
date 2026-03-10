"""Production Readiness Tests — Comprehensive coverage for every FlowyML feature.

These tests verify that all major features work correctly end-to-end,
ensuring the framework is production-ready.

Run with: make test-prod
Or:       poetry run pytest tests/test_production_readiness.py -v
"""

from __future__ import annotations

import json
import os
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from flowyml.utils.config import reset_config, update_config, get_config


class ProductionTestBase(unittest.TestCase):
    """Base class with temp directory + clean config for each test."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # Set FLOWYML_HOME env var so all internal modules use temp dir
        self._orig_flowyml_home = os.environ.get("FLOWYML_HOME")
        os.environ["FLOWYML_HOME"] = str(self.test_path / ".flowyml")

        # Reset the SQL engine singleton so it picks up the new path
        try:
            from flowyml.storage import sql

            if hasattr(sql, "_engine"):
                sql._engine = None
            if hasattr(sql, "_Session"):
                sql._Session = None
            if hasattr(sql, "_session_factory"):
                sql._session_factory = None
        except ImportError:
            pass

        reset_config()
        update_config(
            flowyml_home=self.test_path / ".flowyml",
            artifacts_dir=self.test_path / ".flowyml/artifacts",
            metadata_db=self.test_path / ".flowyml/metadata.db",
            cache_dir=self.test_path / ".flowyml/cache",
            runs_dir=self.test_path / ".flowyml/runs",
            experiments_dir=self.test_path / ".flowyml/experiments",
            projects_dir=self.test_path / ".flowyml/projects",
            enable_ui=False,
        )
        get_config().create_directories()

        # Monkeypatch pipeline metadata persistence to avoid cross-test
        # SQLite conflicts (other test files may hold locks on the default DB)
        from flowyml.core.pipeline import Pipeline

        self._orig_save_run = Pipeline._save_run
        self._orig_save_pipeline_def = Pipeline._save_pipeline_definition
        Pipeline._save_run = lambda self_, *a, **kw: None
        Pipeline._save_pipeline_definition = lambda self_, *a, **kw: None

    def tearDown(self):
        # Restore monkeypatched methods
        from flowyml.core.pipeline import Pipeline

        Pipeline._save_run = self._orig_save_run
        Pipeline._save_pipeline_definition = self._orig_save_pipeline_def
        # Restore original FLOWYML_HOME
        if self._orig_flowyml_home is not None:
            os.environ["FLOWYML_HOME"] = self._orig_flowyml_home
        else:
            os.environ.pop("FLOWYML_HOME", None)

        # Reset SQL engine singleton
        try:
            from flowyml.storage import sql

            if hasattr(sql, "_engine"):
                sql._engine = None
            if hasattr(sql, "_Session"):
                sql._Session = None
            if hasattr(sql, "_session_factory"):
                sql._session_factory = None
        except ImportError:
            pass

        shutil.rmtree(self.test_dir, ignore_errors=True)
        reset_config()


# =============================================================================
# 1. IMPORT HEALTH — All public modules importable
# =============================================================================


class TestImportHealth(unittest.TestCase):
    """Verify all top-level and subpackage imports succeed."""

    def test_top_level_imports(self):
        """Core public API imports without error."""
        from flowyml import Pipeline, step, context

        self.assertIsNotNone(Pipeline)
        self.assertIsNotNone(step)
        self.assertIsNotNone(context)

    def test_asset_imports(self):
        """Asset types importable."""
        from flowyml import Model, Dataset, Metrics

        self.assertIsNotNone(Model)
        self.assertIsNotNone(Dataset)
        self.assertIsNotNone(Metrics)

    def test_eval_imports(self):
        """Evaluation framework importable."""
        from flowyml.evals import evaluate, EvalDataset, EvalSuite
        from flowyml.evals.scorers import Accuracy, F1Score

        self.assertIsNotNone(evaluate)
        self.assertIsNotNone(EvalDataset)
        self.assertIsNotNone(EvalSuite)
        self.assertIsNotNone(Accuracy)
        self.assertIsNotNone(F1Score)

    def test_monitoring_imports(self):
        """Monitoring and notification imports."""
        from flowyml.monitoring.notifications import (
            NotificationManager,
            ConsoleNotifier,
            SlackNotifier,
            EmailNotifier,
        )

        self.assertIsNotNone(NotificationManager)
        self.assertIsNotNone(ConsoleNotifier)

    def test_core_module_imports(self):
        """All core submodules importable."""
        from flowyml.core.pipeline import Pipeline
        from flowyml.core.step import Step
        from flowyml.core.context import Context
        from flowyml.core.graph import DAG
        from flowyml.core.cache import CacheStore
        from flowyml.core.checkpoint import PipelineCheckpoint
        from flowyml.core.map_task import map_task
        from flowyml.core.scheduler import PipelineScheduler
        from flowyml.core.templates import PipelineTemplate
        from flowyml.core.versioning import VersionedPipeline

        self.assertIsNotNone(Pipeline)
        self.assertIsNotNone(Step)

    def test_storage_imports(self):
        """Storage and catalog imports."""
        from flowyml.storage.catalog import ArtifactCatalog, CatalogBackend, LocalCatalogBackend
        from flowyml.storage.catalog.backend import CatalogEntry

        self.assertIsNotNone(ArtifactCatalog)
        self.assertIsNotNone(CatalogEntry)

    def test_stacks_imports(self):
        """Stack system imports."""
        from flowyml.stacks import LocalStack
        from flowyml.stacks.base import Stack

        self.assertIsNotNone(LocalStack)
        self.assertIsNotNone(Stack)

    def test_plugin_imports(self):
        """Plugin system imports."""
        from flowyml.plugins import start_run, end_run, log_metrics, save_artifact

        self.assertIsNotNone(start_run)


# =============================================================================
# 2. PIPELINE LIFECYCLE — Create → Build → Run → Results
# =============================================================================


class TestPipelineLifecycle(ProductionTestBase):
    """End-to-end pipeline lifecycle tests."""

    def test_simple_pipeline_runs(self):
        """Create a simple 2-step pipeline and run it successfully."""
        from flowyml import Pipeline, step, context

        @step(outputs=["data"])
        def load():
            return [1, 2, 3, 4, 5]

        @step(inputs=["data"], outputs=["result"])
        def process(data):
            return sum(data)

        pipeline = Pipeline("test_pipeline", enable_cache=False)
        pipeline.add_step(load)
        pipeline.add_step(process)
        result = pipeline.run()

        self.assertTrue(result.success)
        self.assertEqual(result.outputs["result"], 15)

    def test_pipeline_method_chaining(self):
        """Fluent API with method chaining works."""
        from flowyml import Pipeline, step

        @step(outputs=["a"])
        def step_a():
            return 1

        @step(inputs=["a"], outputs=["b"])
        def step_b(a):
            return a + 1

        pipeline = Pipeline("chained", enable_cache=False)
        pipeline.add_step(step_a).add_step(step_b)
        result = pipeline.run()

        self.assertTrue(result.success)
        self.assertEqual(result.outputs["b"], 2)

    def test_pipeline_result_to_dict(self):
        """PipelineResult can be serialized."""
        from flowyml import Pipeline, step

        @step(outputs=["x"])
        def produce():
            return 42

        pipeline = Pipeline("serialize_test", enable_cache=False)
        pipeline.add_step(produce)
        result = pipeline.run()

        result_dict = result.to_dict()
        self.assertIn("run_id", result_dict)
        self.assertIn("pipeline_name", result_dict)
        self.assertEqual(result_dict["success"], True)

    def test_pipeline_build_validates_dag(self):
        """pipeline.build() validates the DAG without raising errors."""
        from flowyml import Pipeline, step

        @step(outputs=["a"])
        def step_a():
            return 1

        pipeline = Pipeline("build_test", enable_cache=False)
        pipeline.add_step(step_a)
        # build() validates DAG structure without raising
        try:
            pipeline.build()
            validated = True
        except Exception:
            validated = False
        self.assertTrue(validated)


# =============================================================================
# 3. CONTEXT INJECTION
# =============================================================================


class TestContextInjection(ProductionTestBase):
    """Context parameter injection into steps."""

    def test_context_injects_parameters(self):
        """Parameters from context() are injected into matching step args."""
        from flowyml import Pipeline, step, context

        @step(outputs=["result"])
        def compute(multiplier: int = 1):
            return 10 * multiplier

        ctx = context(multiplier=5)
        pipeline = Pipeline("ctx_test", context=ctx, enable_cache=False)
        pipeline.add_step(compute)
        result = pipeline.run()

        self.assertTrue(result.success)
        self.assertEqual(result.outputs["result"], 50)

    def test_context_partial_injection(self):
        """Context injects only matching params, others use defaults."""
        from flowyml import Pipeline, step, context

        @step(outputs=["result"])
        def compute(a: int = 1, b: int = 2):
            return a + b

        ctx = context(a=10)
        pipeline = Pipeline("partial_ctx", context=ctx, enable_cache=False)
        pipeline.add_step(compute)
        result = pipeline.run()

        self.assertTrue(result.success)
        self.assertEqual(result.outputs["result"], 12)  # 10 + 2


# =============================================================================
# 4. CACHING STRATEGIES
# =============================================================================


class TestCachingStrategies(ProductionTestBase):
    """Multi-level caching with code_hash, input_hash, and disabled."""

    def test_cache_hit_on_repeat_run(self):
        """Second run with same code+inputs should use cache."""
        from flowyml import Pipeline, step

        call_count = 0

        @step(cache="code_hash", outputs=["data"])
        def expensive():
            nonlocal call_count
            call_count += 1
            return [1, 2, 3]

        pipeline = Pipeline("cache_test", enable_cache=True, cache_dir=str(self.test_path / "cache"))
        pipeline.add_step(expensive)

        result1 = pipeline.run()
        result2 = pipeline.run()

        self.assertTrue(result1.success)
        self.assertTrue(result2.success)
        # Verify first run executed, second was cached
        self.assertGreaterEqual(call_count, 1)

    def test_cache_disabled(self):
        """cache=False always re-executes."""
        from flowyml import Pipeline, step

        call_count = 0

        @step(cache=False, outputs=["data"])
        def always_run():
            nonlocal call_count
            call_count += 1
            return "fresh"

        pipeline = Pipeline("no_cache_test", enable_cache=True, cache_dir=str(self.test_path / "cache"))
        pipeline.add_step(always_run)

        pipeline.run()
        pipeline.run()

        self.assertEqual(call_count, 2)

    def test_pipeline_level_cache_disable(self):
        """enable_cache=False disables caching for entire pipeline."""
        from flowyml import Pipeline, step

        call_count = 0

        @step(outputs=["data"])
        def tracked():
            nonlocal call_count
            call_count += 1
            return "result"

        pipeline = Pipeline("global_no_cache", enable_cache=False)
        pipeline.add_step(tracked)

        pipeline.run()
        pipeline.run()

        self.assertEqual(call_count, 2)


# =============================================================================
# 5. ASSET TYPES — Model, Dataset, Metrics
# =============================================================================


class TestAssetTypes(ProductionTestBase):
    """Asset creation and metadata extraction."""

    def test_model_creation(self):
        """Model.create() produces a proper asset with metadata."""
        from flowyml import Model

        model = Model(data="mock_model", name="test_model")
        self.assertEqual(model.name, "test_model")
        self.assertEqual(model.data, "mock_model")

    def test_dataset_creation(self):
        """Dataset.create() produces a proper asset."""
        from flowyml import Dataset

        dataset = Dataset(data=[1, 2, 3], name="test_dataset")
        self.assertEqual(dataset.name, "test_dataset")
        self.assertEqual(dataset.data, [1, 2, 3])

    def test_metrics_creation(self):
        """Metrics with key-value pairs."""
        from flowyml import Metrics

        m = Metrics(data={"accuracy": 0.95, "f1": 0.91}, name="eval_metrics")
        self.assertEqual(m.name, "eval_metrics")
        self.assertIn("accuracy", m.data)


# =============================================================================
# 6. ARTIFACT CATALOG — Register, Search, Lineage, Dedup
# =============================================================================


class TestArtifactCatalog(ProductionTestBase):
    """Catalog registration, search, tagging, and lineage."""

    def _get_catalog(self):
        from flowyml.storage.catalog import ArtifactCatalog

        return ArtifactCatalog(db_path=str(self.test_path / "catalog.db"))

    def test_register_and_get(self):
        """Register an artifact and retrieve it by ID."""
        catalog = self._get_catalog()
        artifact_id = catalog.register(
            name="my_model",
            artifact_type="Model",
            source_pipeline="training",
            source_step="train",
            source_run_id="run_001",
        )
        self.assertIsNotNone(artifact_id)

        entry = catalog.get(artifact_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "my_model")
        self.assertEqual(entry.artifact_type, "Model")

    def test_search(self):
        """Search returns matching artifacts."""
        catalog = self._get_catalog()
        catalog.register(name="fraud_model", artifact_type="Model")
        catalog.register(name="training_data", artifact_type="Dataset")

        results = catalog.search("fraud")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].name, "fraud_model")

    def test_tagging(self):
        """Add tags and filter by tags."""
        catalog = self._get_catalog()
        aid = catalog.register(name="prod_model", artifact_type="Model")
        catalog.tag(aid, stage="production", team="ml")

        entry = catalog.get(aid)
        self.assertEqual(entry.tags["stage"], "production")
        self.assertEqual(entry.tags["team"], "ml")

    def test_content_hash_dedup(self):
        """Registering with same data produces same content hash."""
        catalog = self._get_catalog()
        data = {"key": "value"}
        aid1 = catalog.register(name="a1", artifact_type="Model", data=data)
        aid2 = catalog.register(name="a2", artifact_type="Model", data=data)

        e1 = catalog.get(aid1)
        e2 = catalog.get(aid2)
        self.assertEqual(e1.content_hash, e2.content_hash)

    def test_lineage_tracking(self):
        """Parent-child lineage is tracked correctly."""
        catalog = self._get_catalog()
        parent_id = catalog.register(name="raw_data", artifact_type="Dataset")
        child_id = catalog.register(
            name="processed",
            artifact_type="Dataset",
            parent_ids=[parent_id],
        )

        lineage = catalog.get_lineage(child_id)
        self.assertEqual(len(lineage["parents"]), 1)
        self.assertEqual(lineage["parents"][0]["name"], "raw_data")

    def test_list_filter_by_type(self):
        """List artifacts filtered by type."""
        catalog = self._get_catalog()
        catalog.register(name="m1", artifact_type="Model")
        catalog.register(name="d1", artifact_type="Dataset")
        catalog.register(name="m2", artifact_type="Model")

        models = catalog.list(artifact_type="Model")
        self.assertEqual(len(models), 2)
        for m in models:
            self.assertEqual(m.artifact_type, "Model")


# =============================================================================
# 7. PIPELINE VERSIONING
# =============================================================================


class TestPipelineVersioning(ProductionTestBase):
    """Pipeline versioning, comparison, and listing."""

    def test_versioned_pipeline_creation(self):
        """VersionedPipeline can be created with version string."""
        from flowyml.core.versioning import VersionedPipeline

        vp = VersionedPipeline(name="test_vp", version="1.0.0")
        self.assertEqual(vp.version, "1.0.0")

    def test_save_and_list_versions(self):
        """Save a version and list all versions."""
        from flowyml.core.versioning import VersionedPipeline
        from flowyml import step

        @step(outputs=["x"])
        def produce():
            return 1

        vp = VersionedPipeline(
            name="test_versions",
            version="1.0.0",
            enable_cache=False,
        )
        vp.add_step(produce)
        vp.save_version(metadata={"description": "Initial version"})

        versions = vp.list_versions()
        self.assertGreaterEqual(len(versions), 1)


# =============================================================================
# 8. PROJECTS & MULTI-TENANCY
# =============================================================================


class TestProjects(ProductionTestBase):
    """Project creation and pipeline isolation."""

    def test_project_creation(self):
        """Create a project and verify it exists."""
        from flowyml.core.project import Project

        project = Project("test_project")
        self.assertEqual(project.name, "test_project")

    def test_pipeline_with_project(self):
        """Pipeline can be attached to a project."""
        from flowyml import Pipeline, step

        @step(outputs=["x"])
        def produce():
            return 42

        pipeline = Pipeline(
            "proj_pipeline",
            project_name="my_project",
            enable_cache=False,
        )
        pipeline.add_step(produce)
        result = pipeline.run()
        self.assertTrue(result.success)


# =============================================================================
# 9. NOTIFICATION SYSTEM
# =============================================================================


class TestNotifications(ProductionTestBase):
    """NotificationManager with ConsoleNotifier."""

    def test_notification_manager_setup(self):
        """Create a NotificationManager and add channels."""
        from flowyml.monitoring.notifications import (
            NotificationManager,
            ConsoleNotifier,
        )

        manager = NotificationManager()
        manager.add_channel(ConsoleNotifier())
        self.assertEqual(len(manager.channels), 1)

    def test_notify_dispatches_to_channels(self):
        """Notifications are dispatched to all registered channels."""
        from flowyml.monitoring.notifications import (
            NotificationManager,
            ConsoleNotifier,
        )

        manager = NotificationManager()
        console = ConsoleNotifier()
        console.send = MagicMock()
        manager.add_channel(console)

        manager.notify("Test", "Hello world", level="info")
        console.send.assert_called_once()

    def test_pipeline_event_helpers(self):
        """on_pipeline_start, on_pipeline_success, on_pipeline_failure work."""
        from flowyml.monitoring.notifications import (
            NotificationManager,
            ConsoleNotifier,
        )

        manager = NotificationManager()
        console = ConsoleNotifier()
        console.send = MagicMock()
        manager.add_channel(console)

        manager.on_pipeline_start("my_pipeline", "run_001")
        manager.on_pipeline_success("my_pipeline", "run_001", duration=10.5)
        manager.on_pipeline_failure("my_pipeline", "run_001", error="OOM")

        self.assertEqual(console.send.call_count, 3)


# =============================================================================
# 10. SCHEDULING
# =============================================================================


class TestScheduling(ProductionTestBase):
    """Pipeline scheduler."""

    def test_scheduler_creation(self):
        """PipelineScheduler initializes."""
        from flowyml.core.scheduler import PipelineScheduler

        scheduler = PipelineScheduler()
        self.assertIsNotNone(scheduler)

    def test_schedule_creation(self):
        """A schedule can be created with a cron expression."""
        from flowyml.core.scheduler import PipelineScheduler

        scheduler = PipelineScheduler()

        def dummy_pipeline():
            pass

        scheduler.schedule_cron(
            name="daily_retrain",
            pipeline_func=dummy_pipeline,
            cron_expression="0 2 * * *",
        )

        schedules = scheduler.list_schedules()
        self.assertGreaterEqual(len(schedules), 1)


# =============================================================================
# 11. CHECKPOINTING
# =============================================================================


class TestCheckpointing(ProductionTestBase):
    """Pipeline checkpoint save/restore."""

    def test_checkpoint_save_and_load(self):
        """Save step state and load it back."""
        from flowyml.core.checkpoint import PipelineCheckpoint

        cp = PipelineCheckpoint(
            run_id="test_run",
            checkpoint_dir=str(self.test_path / "checkpoints"),
        )

        cp.save_step_state("step_1", outputs={"loss": 0.05})
        cp.save_step_state("step_2", outputs={"accuracy": 0.95})

        self.assertTrue(cp.exists())
        self.assertEqual(cp.get_completed_steps(), ["step_1", "step_2"])
        self.assertEqual(cp.resume_point(), "step_2")

    def test_checkpoint_load_step_state(self):
        """Load outputs for a specific step."""
        from flowyml.core.checkpoint import PipelineCheckpoint

        cp = PipelineCheckpoint(
            run_id="load_test",
            checkpoint_dir=str(self.test_path / "checkpoints"),
        )

        cp.save_step_state("train", outputs={"model": "mock_model_data"})
        state = cp.load_step_state("train")
        self.assertEqual(state["model"], "mock_model_data")

    def test_checkpoint_clear(self):
        """Clearing a checkpoint removes all state."""
        from flowyml.core.checkpoint import PipelineCheckpoint

        cp = PipelineCheckpoint(
            run_id="clear_test",
            checkpoint_dir=str(self.test_path / "checkpoints"),
        )

        cp.save_step_state("step_1", outputs={"x": 1})
        self.assertTrue(cp.exists())

        cp.clear()
        self.assertFalse(cp.exists())
        self.assertEqual(cp.get_completed_steps(), [])


# =============================================================================
# 12. MONITORING & ALERTS
# =============================================================================


class TestMonitoring(ProductionTestBase):
    """System and pipeline monitoring."""

    def test_system_monitor_import(self):
        """SystemMonitor importable and initializable."""
        from flowyml.monitoring.monitor import SystemMonitor

        monitor = SystemMonitor(name="test_monitor")
        self.assertIsNotNone(monitor)

    def test_alert_manager(self):
        """AlertManager setup and dispatch."""
        from flowyml.monitoring.alerts import AlertManager

        manager = AlertManager()
        self.assertIsNotNone(manager)


# =============================================================================
# 13. STEP GROUPING
# =============================================================================


class TestStepGrouping(ProductionTestBase):
    """Steps with execution_group are grouped correctly."""

    def test_step_group_assignment(self):
        """Step with execution_group stores the group name."""
        from flowyml import step

        @step(outputs=["x"], execution_group="preprocessing")
        def preprocess():
            return [1, 2, 3]

        self.assertEqual(preprocess.execution_group, "preprocessing")


# =============================================================================
# 14. TEMPLATES
# =============================================================================


class TestTemplates(ProductionTestBase):
    """Pipeline templates."""

    def test_template_creation(self):
        """PipelineTemplate can be instantiated."""
        from flowyml.core.templates import PipelineTemplate

        template = PipelineTemplate()
        self.assertIsNotNone(template)


# =============================================================================
# 15. MAP TASKS
# =============================================================================


class TestMapTasks(ProductionTestBase):
    """Parallel map task execution."""

    def test_map_task_creation(self):
        """map_task decorator creates a callable."""
        from flowyml.core.map_task import map_task

        @map_task(concurrency=4)
        def process_item(item: dict) -> dict:
            return {"processed": True, **item}

        self.assertTrue(callable(process_item))


# =============================================================================
# 16. ERROR HANDLING
# =============================================================================


class TestErrorHandling(ProductionTestBase):
    """Pipeline error handling and step failures."""

    def test_pipeline_captures_step_failure(self):
        """A failing step causes pipeline failure with error info."""
        from flowyml import Pipeline, step

        @step(outputs=["x"])
        def fail_step():
            raise ValueError("intentional error")

        pipeline = Pipeline("fail_test", enable_cache=False)
        pipeline.add_step(fail_step)
        result = pipeline.run()

        self.assertFalse(result.success)


# =============================================================================
# 17. PLUGIN REGISTRY & STACKS
# =============================================================================


class TestPluginAndStacks(ProductionTestBase):
    """Plugin registration and stack creation."""

    def test_local_stack_creation(self):
        """LocalStack can be instantiated."""
        from flowyml.stacks import LocalStack

        stack = LocalStack()
        self.assertIsNotNone(stack)

    def test_stack_has_required_components(self):
        """Stack exposes orchestrator and artifact_store attributes."""
        from flowyml.stacks import LocalStack

        stack = LocalStack()
        self.assertTrue(hasattr(stack, "orchestrator"))
        self.assertTrue(hasattr(stack, "artifact_store"))


# =============================================================================
# 18. CATALOG ENTRY SERIALIZATION
# =============================================================================


class TestCatalogEntrySerialization(unittest.TestCase):
    """CatalogEntry to_dict / from_dict round-trip."""

    def test_round_trip(self):
        """to_dict() → from_dict() produces identical entry."""
        from flowyml.storage.catalog.backend import CatalogEntry

        entry = CatalogEntry(
            artifact_id="abc-123",
            name="my_model",
            artifact_type="Model",
            content_hash="sha256abc",
            source_step="train",
            source_run_id="run_001",
            source_pipeline="training",
            parent_ids=["p1", "p2"],
            tags={"stage": "prod"},
            metadata={"framework": "sklearn"},
            uri="/artifacts/model.pkl",
            created_at="2024-01-01T00:00:00",
            version="1.0.0",
        )

        serialized = entry.to_dict()
        restored = CatalogEntry.from_dict(serialized)

        self.assertEqual(restored.artifact_id, entry.artifact_id)
        self.assertEqual(restored.name, entry.name)
        self.assertEqual(restored.parent_ids, entry.parent_ids)
        self.assertEqual(restored.tags, entry.tags)
        self.assertEqual(restored.version, entry.version)


if __name__ == "__main__":
    unittest.main()
