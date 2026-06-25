"""Tests for FlowyML Auto-Tracking — automatic metrics and parameter collection."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Any

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAutoTrackerUnit(unittest.TestCase):
    """Unit tests for the AutoTracker class."""

    def setUp(self):
        """Fresh AutoTracker for each test."""
        from flowyml.tracking.auto_tracking import AutoTracker

        self.tracker = AutoTracker(enabled=True)

    # ------------------------------------------------------------------
    # Environment info
    # ------------------------------------------------------------------

    def test_collect_environment_info(self):
        """Should collect Python version, platform, and machine."""
        info = self.tracker.collect_environment_info()
        self.assertIn("python_version", info)
        self.assertIn("platform", info)
        self.assertIn("machine", info)
        self.assertIn("gpu_available", info)
        # Python version should be a valid string
        self.assertTrue(info["python_version"].count(".") == 2)

    # ------------------------------------------------------------------
    # Stack info
    # ------------------------------------------------------------------

    def test_collect_stack_info(self):
        """Should extract component type names from a Stack-like object."""
        mock_stack = MagicMock()
        mock_stack.name = "test_stack"
        mock_stack.executor = MagicMock()
        type(mock_stack.executor).__name__ = "LocalExecutor"
        mock_stack.artifact_store = MagicMock()
        type(mock_stack.artifact_store).__name__ = "LocalArtifactStore"
        mock_stack.metadata_store = MagicMock()
        type(mock_stack.metadata_store).__name__ = "SQLiteMetadataStore"
        mock_stack.orchestrator = None
        mock_stack.model_deployer = None
        mock_stack.container_registry = None

        info = self.tracker.collect_stack_info(mock_stack)
        self.assertEqual(info["name"], "test_stack")
        self.assertEqual(info["executor_type"], "LocalExecutor")
        self.assertEqual(info["artifact_store_type"], "LocalArtifactStore")
        self.assertEqual(info["metadata_store_type"], "SQLiteMetadataStore")

    def test_collect_stack_info_none_stack(self):
        """Should handle None/empty stack gracefully."""
        info = self.tracker.collect_stack_info(None)
        self.assertEqual(info, {})

    # ------------------------------------------------------------------
    # Metrics extraction from step outputs
    # ------------------------------------------------------------------

    def test_extract_metrics_from_dict_output(self):
        """Should extract numeric values from a plain dict output."""
        result = MagicMock()
        result.output = {"accuracy": 0.95, "loss": 0.05, "model_name": "bert"}
        result.duration_seconds = 12.5
        result.cached = False
        result.retries = 0

        extracted = self.tracker.extract_step_metrics("train_model", result)

        self.assertIn("train_model.accuracy", extracted)
        self.assertIn("train_model.loss", extracted)
        self.assertNotIn("train_model.model_name", extracted)  # string, not numeric
        self.assertEqual(extracted["train_model.accuracy"], 0.95)
        self.assertEqual(extracted["train_model.loss"], 0.05)
        self.assertIn("train_model.duration_seconds", extracted)

    def test_extract_metrics_from_eval_step(self):
        """Steps named 'evaluate' should get clean metric keys (no prefix)."""
        result = MagicMock()
        result.output = {"accuracy": 0.92, "f1_score": 0.89}
        result.duration_seconds = 5.0
        result.cached = False
        result.retries = 0

        extracted = self.tracker.extract_step_metrics("evaluate", result)

        # eval steps get clean keys
        self.assertIn("accuracy", extracted)
        self.assertIn("f1_score", extracted)
        self.assertNotIn("evaluate.accuracy", extracted)

    def test_extract_metrics_from_metrics_asset(self):
        """Should extract metrics from a Metrics asset output."""
        from flowyml.assets.metrics import Metrics

        metrics_asset = Metrics(
            name="eval_metrics",
            data={"accuracy": 0.95, "precision": 0.93, "recall": 0.91},
        )

        result = MagicMock()
        result.output = metrics_asset
        result.duration_seconds = 3.0
        result.cached = False
        result.retries = 0

        extracted = self.tracker.extract_step_metrics("compute_metrics", result)

        self.assertIn("compute_metrics.accuracy", extracted)
        self.assertIn("compute_metrics.precision", extracted)
        self.assertIn("compute_metrics.recall", extracted)

    def test_extract_metrics_from_scalar(self):
        """Should track scalar numeric output."""
        result = MagicMock()
        result.output = 42.0
        result.duration_seconds = 1.0
        result.cached = False
        result.retries = 0

        extracted = self.tracker.extract_step_metrics("count_items", result)
        self.assertIn("count_items.output", extracted)
        self.assertEqual(extracted["count_items.output"], 42.0)

    def test_extract_metrics_from_tuple(self):
        """Should extract numeric elements from tuple output."""
        result = MagicMock()
        result.output = (0.95, 0.87, "some_string")
        result.duration_seconds = 2.0
        result.cached = False
        result.retries = 0

        extracted = self.tracker.extract_step_metrics("multi_output", result)
        self.assertIn("multi_output.output_0", extracted)
        self.assertIn("multi_output.output_1", extracted)
        self.assertNotIn("multi_output.output_2", extracted)  # string

    def test_extract_metrics_cached_step(self):
        """Should record cached=1 for cached steps."""
        result = MagicMock()
        result.output = {"accuracy": 0.9}
        result.duration_seconds = 0.01
        result.cached = True
        result.retries = 0

        extracted = self.tracker.extract_step_metrics("cached_step", result)
        self.assertEqual(extracted["cached_step.cached"], 1)

    def test_extract_metrics_with_retries(self):
        """Should record retry count."""
        result = MagicMock()
        result.output = {"accuracy": 0.9}
        result.duration_seconds = 10.0
        result.cached = False
        result.retries = 3

        extracted = self.tracker.extract_step_metrics("flaky_step", result)
        self.assertEqual(extracted["flaky_step.retries"], 3)

    def test_extract_metrics_none_output(self):
        """Should handle None output gracefully."""
        result = MagicMock()
        result.output = None
        result.duration_seconds = 1.0
        result.cached = False
        result.retries = 0

        extracted = self.tracker.extract_step_metrics("void_step", result)
        # Should only have duration
        self.assertIn("void_step.duration_seconds", extracted)
        self.assertEqual(len(extracted), 1)

    # ------------------------------------------------------------------
    # Context parameter extraction
    # ------------------------------------------------------------------

    def test_extract_context_params(self):
        """Should extract all params from a Context object."""
        from flowyml.core.context import Context

        ctx = Context(learning_rate=0.001, epochs=10, batch_size=32, device="cuda")
        params = self.tracker._extract_context_params(ctx)

        self.assertEqual(params["learning_rate"], 0.001)
        self.assertEqual(params["epochs"], 10)
        self.assertEqual(params["batch_size"], 32)
        self.assertEqual(params["device"], "cuda")

    def test_extract_context_params_skips_private(self):
        """Should skip keys starting with underscore."""
        from flowyml.core.context import Context

        ctx = Context(learning_rate=0.001, _internal=True)
        params = self.tracker._extract_context_params(ctx)

        self.assertIn("learning_rate", params)
        self.assertNotIn("_internal", params)

    # ------------------------------------------------------------------
    # make_trackable
    # ------------------------------------------------------------------

    def test_make_trackable_truncates_strings(self):
        """Should truncate strings longer than 250 chars."""
        from flowyml.tracking.auto_tracking import AutoTracker

        params = {"long_string": "x" * 500, "short": "hello"}
        clean = AutoTracker._make_trackable(params)

        self.assertEqual(len(clean["long_string"]), 250)
        self.assertEqual(clean["short"], "hello")

    def test_make_trackable_converts_non_primitives(self):
        """Should convert non-primitive types to string."""
        from flowyml.tracking.auto_tracking import AutoTracker

        params = {"list_param": [1, 2, 3], "dict_param": {"nested": True}}
        clean = AutoTracker._make_trackable(params)

        self.assertIsInstance(clean["list_param"], str)
        self.assertIsInstance(clean["dict_param"], str)

    # ------------------------------------------------------------------
    # Metrics accumulation
    # ------------------------------------------------------------------

    def test_metrics_accumulate_across_steps(self):
        """Metrics from multiple steps should accumulate."""
        result1 = MagicMock()
        result1.output = {"accuracy": 0.8}
        result1.duration_seconds = 5.0
        result1.cached = False
        result1.retries = 0

        result2 = MagicMock()
        result2.output = {"accuracy": 0.9}
        result2.duration_seconds = 10.0
        result2.cached = False
        result2.retries = 0

        self.tracker.extract_step_metrics("step1", result1)
        self.tracker.extract_step_metrics("step2", result2)

        all_metrics = self.tracker.metrics
        self.assertIn("step1.accuracy", all_metrics)
        self.assertIn("step2.accuracy", all_metrics)

    # ------------------------------------------------------------------
    # Disabled tracker
    # ------------------------------------------------------------------

    def test_disabled_tracker_skips_collection(self):
        """When disabled, should return empty results."""
        from flowyml.tracking.auto_tracking import AutoTracker

        tracker = AutoTracker(enabled=False)

        result = MagicMock()
        result.output = {"accuracy": 0.95}
        result.duration_seconds = 5.0
        result.cached = False
        result.retries = 0

        extracted = tracker.extract_step_metrics("step1", result)
        self.assertEqual(extracted, {})

        params = tracker.collect_parameters(MagicMock())
        self.assertEqual(params, {})

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def test_reset_clears_all_data(self):
        """reset() should clear all collected data."""
        result = MagicMock()
        result.output = {"accuracy": 0.9}
        result.duration_seconds = 5.0
        result.cached = False
        result.retries = 0

        self.tracker.extract_step_metrics("step1", result)
        self.tracker._parameters["lr"] = 0.001
        self.tracker._tags["project"] = "test"

        self.tracker.reset()

        self.assertEqual(len(self.tracker.metrics), 0)
        self.assertEqual(len(self.tracker.parameters), 0)
        self.assertEqual(len(self.tracker.tags), 0)

    # ------------------------------------------------------------------
    # repr
    # ------------------------------------------------------------------

    def test_repr(self):
        """__repr__ should include counts."""
        repr_str = repr(self.tracker)
        self.assertIn("params=0", repr_str)
        self.assertIn("metrics=0", repr_str)


class TestAutoTrackerHooks(unittest.TestCase):
    """Test the new hook types for auto-tracking."""

    def setUp(self):
        """Reset hooks before each test."""
        from flowyml.core.hooks import get_global_hooks

        hooks = get_global_hooks()
        hooks.on_metrics_collected.clear()
        hooks.on_params_collected.clear()

    def tearDown(self):
        """Clean up hooks."""
        from flowyml.core.hooks import get_global_hooks

        hooks = get_global_hooks()
        hooks.on_metrics_collected.clear()
        hooks.on_params_collected.clear()

    def test_metrics_collected_hook_fires(self):
        """on_metrics_collected hooks should be called."""
        from flowyml.core.hooks import get_global_hooks

        hooks = get_global_hooks()
        collected = []

        def handler(step_name, metrics):
            collected.append((step_name, metrics))

        hooks.register_metrics_collected_hook(handler)
        hooks.run_metrics_collected_hooks("train", {"accuracy": 0.95})

        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0][0], "train")
        self.assertEqual(collected[0][1]["accuracy"], 0.95)

    def test_params_collected_hook_fires(self):
        """on_params_collected hooks should be called."""
        from flowyml.core.hooks import get_global_hooks

        hooks = get_global_hooks()
        collected = []

        def handler(params):
            collected.append(params)

        hooks.register_params_collected_hook(handler)
        hooks.run_params_collected_hooks({"lr": 0.001, "epochs": 10})

        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["lr"], 0.001)

    def test_metrics_hook_decorator(self):
        """@on_metrics_collected decorator should register hook."""
        from flowyml.core.hooks import on_metrics_collected, get_global_hooks

        collected = []

        @on_metrics_collected
        def my_handler(step_name, metrics):
            collected.append(step_name)

        hooks = get_global_hooks()
        hooks.run_metrics_collected_hooks("eval", {"loss": 0.1})

        self.assertEqual(collected, ["eval"])

    def test_params_hook_decorator(self):
        """@on_params_collected decorator should register hook."""
        from flowyml.core.hooks import on_params_collected, get_global_hooks

        collected = []

        @on_params_collected
        def my_handler(params):
            collected.append(len(params))

        hooks = get_global_hooks()
        hooks.run_params_collected_hooks({"a": 1, "b": 2})

        self.assertEqual(collected, [2])

    def test_hook_failure_doesnt_crash(self):
        """Hook that raises should not propagate exception."""
        from flowyml.core.hooks import get_global_hooks

        hooks = get_global_hooks()

        def bad_handler(step_name, metrics):
            raise ValueError("boom")

        hooks.register_metrics_collected_hook(bad_handler)
        # Should not raise
        hooks.run_metrics_collected_hooks("step", {"m": 1})


class TestContextTrackableParams(unittest.TestCase):
    """Test Context._trackable_params and mark_as_tracked."""

    def test_trackable_params_returns_all_by_default(self):
        """Without mark_as_tracked, all params should be included."""
        from flowyml.core.context import Context

        ctx = Context(lr=0.001, epochs=10, batch_size=32)
        params = ctx._trackable_params

        self.assertEqual(params["lr"], 0.001)
        self.assertEqual(params["epochs"], 10)
        self.assertEqual(params["batch_size"], 32)

    def test_trackable_params_filters_private(self):
        """Keys starting with _ should be excluded."""
        from flowyml.core.context import Context

        ctx = Context(lr=0.001, _internal=True)
        params = ctx._trackable_params

        self.assertIn("lr", params)
        self.assertNotIn("_internal", params)

    def test_mark_as_tracked_filters(self):
        """Only marked params should appear when mark_as_tracked is used."""
        from flowyml.core.context import Context

        ctx = Context(lr=0.001, epochs=10, batch_size=32, debug=True)
        ctx.mark_as_tracked("lr", "epochs")

        params = ctx._trackable_params
        self.assertIn("lr", params)
        self.assertIn("epochs", params)
        self.assertNotIn("batch_size", params)
        self.assertNotIn("debug", params)

    def test_mark_as_tracked_chaining(self):
        """mark_as_tracked should return self for chaining."""
        from flowyml.core.context import context

        ctx = context(lr=0.001, epochs=10).mark_as_tracked("lr")
        self.assertIn("lr", ctx._trackable_params)


class TestPipelineAutoTrackIntegration(unittest.TestCase):
    """Integration tests: Pipeline with auto_track."""

    def test_pipeline_creates_auto_tracker_by_default(self):
        """Pipeline should create an AutoTracker when auto_track is not explicitly False."""
        from flowyml.core.pipeline import Pipeline
        from flowyml.core.context import Context

        pipeline = Pipeline("test_pipeline", context=Context(lr=0.001))
        self.assertIsNotNone(pipeline._auto_tracker)
        self.assertTrue(pipeline.auto_track)

    def test_pipeline_no_tracker_when_disabled(self):
        """Pipeline should NOT create an AutoTracker when auto_track=False."""
        from flowyml.core.pipeline import Pipeline
        from flowyml.core.context import Context

        pipeline = Pipeline("test_pipeline", context=Context(lr=0.001), auto_track=False)
        self.assertIsNone(pipeline._auto_tracker)
        self.assertFalse(pipeline.auto_track)

    def test_auto_tracker_init_param(self):
        """auto_track param should control tracker creation."""
        from flowyml.core.pipeline import Pipeline
        from flowyml.core.context import Context

        # Explicitly True
        p1 = Pipeline("p1", context=Context(), auto_track=True)
        self.assertIsNotNone(p1._auto_tracker)

        # Explicitly False
        p2 = Pipeline("p2", context=Context(), auto_track=False)
        self.assertIsNone(p2._auto_tracker)


class TestPluginIntegrationAutoMetrics(unittest.TestCase):
    """Test PipelinePluginIntegration with auto_metrics parameter."""

    def test_on_step_end_with_auto_metrics(self):
        """on_step_end should forward auto_metrics to tracker."""
        from flowyml.plugins.integration import PipelinePluginIntegration

        mock_tracker = MagicMock()
        mock_tracker.set_tag = MagicMock()
        mock_tracker.log_metrics = MagicMock()

        integration = PipelinePluginIntegration(tracker=mock_tracker)
        integration._current_run = "test-run"

        auto_metrics = {"accuracy": 0.95, "loss": 0.05}
        integration.on_step_end(
            step_name="evaluate",
            duration=5.0,
            auto_metrics=auto_metrics,
        )

        # Check that log_metrics was called with the auto_metrics
        calls = mock_tracker.log_metrics.call_args_list
        # Should have 2 calls: one for duration, one for auto_metrics
        self.assertTrue(len(calls) >= 2)

    def test_on_step_end_without_auto_metrics(self):
        """on_step_end should still work without auto_metrics (backward compat)."""
        from flowyml.plugins.integration import PipelinePluginIntegration

        mock_tracker = MagicMock()
        mock_tracker.set_tag = MagicMock()
        mock_tracker.log_metrics = MagicMock()

        integration = PipelinePluginIntegration(tracker=mock_tracker)
        integration._current_run = "test-run"

        # No auto_metrics — should not crash
        integration.on_step_end(
            step_name="train",
            duration=10.0,
        )

        # Duration should still be logged
        mock_tracker.log_metrics.assert_called()


if __name__ == "__main__":
    unittest.main()
