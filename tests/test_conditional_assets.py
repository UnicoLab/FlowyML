"""Tests for conditional execution with Asset objects (Metrics, Model, Dataset, FeatureSet)."""

import pytest
from flowyml import Pipeline, step, If, Metrics, Model, Dataset, FeatureSet


class TestConditionalWithAssets:
    """Test conditional execution with various Asset types."""

    def test_metrics_create_with_dict(self):
        """Test Metrics.create() with metrics dict parameter (user's example)."""

        @step(inputs=["model/trained"], outputs=["metrics/evaluation"])
        def evaluate_model(model):
            """Evaluate the trained model."""
            metrics = {"test_accuracy": 0.93, "test_loss": 0.07}
            return Metrics.create(
                name="example_metrics",
                metrics=metrics,
                metadata={"source": "example"},
            )

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        @step(outputs=["model/trained"])
        def train_model():
            return "model_data"

        pipeline = Pipeline("test_metrics_dict")
        pipeline.add_step(train_model)
        pipeline.add_step(evaluate_model)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate_model"].outputs["metrics/evaluation"].metrics["test_accuracy"]
                > 0.9,
                then_step=deploy_model,
                else_step=retrain_model,
            ),
        )

        result = pipeline.run()

        assert result.success
        assert "evaluate_model" in result.step_results
        assert "deploy_model" in result.step_results
        assert result.step_results["deploy_model"].success

    def test_metrics_dict_access_patterns(self):
        """Test all access patterns for Metrics in conditions."""

        @step(outputs=["metrics/evaluation"])
        def evaluate_model():
            metrics = {"test_accuracy": 0.93, "test_loss": 0.07}
            return Metrics.create(
                name="example_metrics",
                metrics=metrics,
                metadata={"source": "example"},
            )

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_metrics_access_patterns")
        pipeline.add_step(evaluate_model)

        # Test .metrics access
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate_model"].outputs["metrics/evaluation"].metrics["test_accuracy"]
                > 0.9,
                then_step=deploy_model,
                else_step=retrain_model,
            ),
        )

        result = pipeline.run()
        assert result.success
        assert "deploy_model" in result.step_results

    def test_metrics_data_access(self):
        """Test accessing Metrics via .data property."""

        @step(outputs=["metrics/evaluation"])
        def evaluate_model():
            return Metrics.create(
                name="example_metrics",
                test_accuracy=0.93,
                test_loss=0.07,
            )

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_metrics_data")
        pipeline.add_step(evaluate_model)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate_model"].outputs["metrics/evaluation"].data["test_accuracy"]
                > 0.9,
                then_step=deploy_model,
                else_step=retrain_model,
            ),
        )

        result = pipeline.run()
        assert result.success
        assert "deploy_model" in result.step_results

    def test_metrics_dict_style_access(self):
        """Test accessing Metrics via dict-style access."""

        @step(outputs=["metrics/evaluation"])
        def evaluate_model():
            return Metrics.create(
                name="example_metrics",
                test_accuracy=0.93,
                test_loss=0.07,
            )

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_metrics_dict_style")
        pipeline.add_step(evaluate_model)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate_model"].outputs["metrics/evaluation"]["test_accuracy"] > 0.9,
                then_step=deploy_model,
                else_step=retrain_model,
            ),
        )

        result = pipeline.run()
        assert result.success
        assert "deploy_model" in result.step_results

    def test_model_properties_access(self):
        """Test accessing Model properties in conditions."""

        @step(outputs=["model/trained"])
        def train_model():
            return Model(
                name="test_model",
                data="model_data",
                framework="pytorch",
                architecture="resnet50",
            )

        @step
        def deploy_model():
            return "deployed"

        @step
        def skip_deploy():
            return "skipped"

        pipeline = Pipeline("test_model_properties")
        pipeline.add_step(train_model)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["train_model"].outputs["model/trained"].framework == "pytorch",
                then_step=deploy_model,
                else_step=skip_deploy,
            ),
        )

        result = pipeline.run()
        assert result.success
        assert "deploy_model" in result.step_results

    def test_dataset_properties_access(self):
        """Test accessing Dataset properties in conditions."""

        @step(outputs=["data/processed"])
        def process_data():
            return Dataset(
                name="processed_data",
                data="data",
                properties={"samples": 10000, "size": "1GB"},
            )

        @step
        def use_large_processing():
            return "large"

        @step
        def use_small_processing():
            return "small"

        pipeline = Pipeline("test_dataset_properties")
        pipeline.add_step(process_data)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["process_data"].outputs["data/processed"].num_samples > 5000,
                then_step=use_large_processing,
                else_step=use_small_processing,
            ),
        )

        result = pipeline.run()
        assert result.success
        assert "use_large_processing" in result.step_results

    def test_featureset_properties_access(self):
        """Test accessing FeatureSet properties in conditions."""

        @step(outputs=["features/engineered"])
        def engineer_features():
            return FeatureSet.create(
                name="engineered_features",
                data=[[1, 2, 3], [4, 5, 6]],
                feature_names=["feat1", "feat2", "feat3"],
                num_samples=2,
            )

        @step
        def use_complex_model():
            return "complex"

        @step
        def use_simple_model():
            return "simple"

        pipeline = Pipeline("test_featureset_properties")
        pipeline.add_step(engineer_features)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["engineer_features"].outputs["features/engineered"].num_features > 2,
                then_step=use_complex_model,
                else_step=use_simple_model,
            ),
        )

        result = pipeline.run()
        assert result.success
        assert "use_complex_model" in result.step_results

    def test_metrics_metadata_access(self):
        """Test accessing Metrics metadata in conditions."""

        @step(outputs=["metrics/evaluation"])
        def evaluate_model():
            return Metrics.create(
                name="example_metrics",
                metrics={"test_accuracy": 0.93},
                metadata={"source": "example", "stage": "production"},
            )

        @step
        def deploy_model():
            return "deployed"

        @step
        def skip_deploy():
            return "skipped"

        pipeline = Pipeline("test_metrics_metadata")
        pipeline.add_step(evaluate_model)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate_model"].outputs["metrics/evaluation"].metadata.get("stage")
                == "production",
                then_step=deploy_model,
                else_step=skip_deploy,
            ),
        )

        result = pipeline.run()
        assert result.success
        assert "deploy_model" in result.step_results
