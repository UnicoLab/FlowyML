"""Tests for conditional execution with If statements."""

import pytest
from flowyml import Pipeline, step, If, Metrics, Model, Dataset
from flowyml.core.context import Context


class TestConditionalExecution:
    """Test conditional execution with If statements."""

    def test_basic_if_condition(self):
        """Test basic If condition with simple values."""

        @step(outputs=["accuracy"])
        def evaluate_model():
            return 0.95

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_conditional")
        pipeline.add_step(evaluate_model)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate_model"].outputs["accuracy"] > 0.9,
                then_step=deploy_model,
                else_step=retrain_model,
            ),
        )

        result = pipeline.run()

        assert result.success
        # Should have executed evaluate_model and deploy_model (since accuracy > 0.9)
        assert "evaluate_model" in result.step_results
        assert "deploy_model" in result.step_results
        assert result.step_results["evaluate_model"].success
        assert result.step_results["deploy_model"].success
        assert result.outputs["deploy_model"] == "deployed"

    def test_if_condition_with_else_branch(self):
        """Test If condition that triggers else branch."""

        @step(outputs=["accuracy"])
        def evaluate_model():
            return 0.85  # Below threshold

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_conditional_else")
        pipeline.add_step(evaluate_model)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate_model"].outputs["accuracy"] > 0.9,
                then_step=deploy_model,
                else_step=retrain_model,
            ),
        )

        result = pipeline.run()

        assert result.success
        # Should have executed evaluate_model and retrain_model (since accuracy <= 0.9)
        assert "evaluate_model" in result.step_results
        assert "retrain_model" in result.step_results
        assert result.step_results["evaluate_model"].success
        assert result.step_results["retrain_model"].success
        assert result.outputs["retrain_model"] == "retrained"
        # deploy_model should not have been executed
        assert "deploy_model" not in result.step_results

    def test_if_condition_with_metrics_asset(self):
        """Test If condition accessing Metrics asset properties."""

        @step(outputs=["metrics/evaluation"])
        def evaluate_model():
            # Metrics.create takes metrics as keyword arguments
            metrics = Metrics.create(
                name="evaluation_metrics",
                test_accuracy=0.93,
                test_loss=0.07,
            )
            return metrics

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_conditional_metrics")
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

    def test_if_condition_with_metrics_data_access(self):
        """Test If condition accessing Metrics via .data property."""

        @step(outputs=["metrics/evaluation"])
        def evaluate_model():
            metrics = Metrics.create(
                name="evaluation_metrics",
                test_accuracy=0.93,
                test_loss=0.07,
            )
            return metrics

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_conditional_metrics_data")
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
        assert "evaluate_model" in result.step_results
        assert "deploy_model" in result.step_results

    def test_if_condition_with_metrics_dict_access(self):
        """Test If condition accessing Metrics via dict-style access."""

        @step(outputs=["metrics/evaluation"])
        def evaluate_model():
            metrics = Metrics.create(
                name="evaluation_metrics",
                test_accuracy=0.93,
                test_loss=0.07,
            )
            return metrics

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_conditional_metrics_dict")
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
        assert "evaluate_model" in result.step_results
        assert "deploy_model" in result.step_results

    def test_if_condition_with_metrics_create_from_dict(self):
        """Test If condition with Metrics created from a dict (user's example pattern)."""

        @step(inputs=["model/trained"], outputs=["metrics/evaluation"])
        def evaluate_model(model):
            """Evaluate the trained model."""
            metrics_dict = {"test_accuracy": 0.93, "test_loss": 0.07}
            # Create Metrics using **kwargs pattern
            return Metrics.create(
                name="example_metrics",
                **metrics_dict,
                tags={"source": "example"},
            )

        @step
        def deploy_model():
            return "deployed"

        @step
        def retrain_model():
            return "retrained"

        pipeline = Pipeline("test_conditional_metrics_create")

        # Add a dummy model step
        @step(outputs=["model/trained"])
        def train_model():
            return "model_data"

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

    def test_if_condition_with_model_asset(self):
        """Test If condition accessing Model asset properties."""

        @step(outputs=["model/trained"])
        def train_model():
            model = Model(
                name="test_model",
                data="model_data",
                framework="pytorch",
            )
            return model

        @step
        def deploy_model():
            return "deployed"

        @step
        def skip_deploy():
            return "skipped"

        pipeline = Pipeline("test_conditional_model")
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
        assert "train_model" in result.step_results
        assert "deploy_model" in result.step_results
        assert result.step_results["deploy_model"].success

    def test_if_condition_with_dataset_asset(self):
        """Test If condition accessing Dataset asset properties."""

        @step(outputs=["data/processed"])
        def process_data():
            dataset = Dataset(
                name="processed_data",
                data="data",
                properties={"samples": 10000},
            )
            return dataset

        @step
        def use_large_processing():
            return "large"

        @step
        def use_small_processing():
            return "small"

        pipeline = Pipeline("test_conditional_dataset")
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
        assert "process_data" in result.step_results
        assert "use_large_processing" in result.step_results
        assert result.step_results["use_large_processing"].success

    def test_if_fluent_api(self):
        """Test If condition using fluent API (.then().else_())."""

        @step(outputs=["score"])
        def evaluate():
            return 0.95

        @step
        def approve():
            return "approved"

        @step
        def reject():
            return "rejected"

        pipeline = Pipeline("test_fluent_if")
        pipeline.add_step(evaluate)
        pipeline.add_control_flow(
            If(condition=lambda ctx: ctx.steps["evaluate"].outputs["score"] > 0.9).then(approve).else_(reject),
        )

        result = pipeline.run()

        assert result.success
        assert "evaluate" in result.step_results
        assert "approve" in result.step_results
        assert result.outputs["approve"] == "approved"

    def test_if_with_context(self):
        """Test If condition with context parameters."""

        @step(outputs=["value"])
        def compute():
            return 42

        @step
        def high_value():
            return "high"

        @step
        def low_value():
            return "low"

        ctx = Context(threshold=40)

        pipeline = Pipeline("test_conditional_context", context=ctx)
        pipeline.add_step(compute)
        pipeline.add_control_flow(
            If(
                condition=lambda ctx_obj: ctx_obj.steps["compute"].outputs["value"]
                > ctx_obj.result.step_results["compute"].outputs.get("value", 0) - 2,
                then_step=high_value,
                else_step=low_value,
            ),
        )

        result = pipeline.run()

        assert result.success
        assert "compute" in result.step_results

    def test_if_with_multiple_conditions(self):
        """Test multiple If conditions in sequence."""

        @step(outputs=["accuracy"])
        def evaluate():
            return 0.92

        @step
        def deploy():
            return "deployed"

        @step
        def retrain():
            return "retrained"

        @step
        def archive():
            return "archived"

        pipeline = Pipeline("test_multiple_conditions")
        pipeline.add_step(evaluate)
        # First condition: accuracy > 0.9 -> deploy, else retrain
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate"].outputs["accuracy"] > 0.9,
                then_step=deploy,
                else_step=retrain,
            ),
        )
        # Second condition: accuracy < 0.8 -> archive
        pipeline.add_control_flow(
            If(
                condition=lambda ctx: ctx.steps["evaluate"].outputs["accuracy"] < 0.8,
                then_step=archive,
                else_step=None,  # No else step
            ),
        )

        result = pipeline.run()

        assert result.success
        assert "evaluate" in result.step_results
        # Should execute deploy (accuracy > 0.9)
        assert "deploy" in result.step_results
        # Should not execute archive (accuracy >= 0.8)
        assert "archive" not in result.step_results
