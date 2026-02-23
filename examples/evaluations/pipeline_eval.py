"""Pipeline Evaluation Example.

Demonstrates using EvalStep to integrate evaluations directly
into FlowyML pipelines as first-class steps.
"""

from flowyml.evals import EvalStep, Accuracy, F1Score


def pipeline_eval_example():
    """Add quality gates to a training pipeline."""
    # Define an evaluation step
    eval_step = EvalStep(
        name="quality_gate",
        scorers=[
            Accuracy(threshold=0.9),
            F1Score(threshold=0.85),
        ],
        fail_on_regression=True,
        baseline_experiment="model_v1",
        regression_threshold=0.05,
    )

    print("=== Pipeline Eval Step ===")
    print(f"Step name: {eval_step.name}")
    print(f"Scorers: {[s.name for s in eval_step.scorers]}")
    print(f"Fail on regression: {eval_step.fail_on_regression}")

    # In a real pipeline:
    # pipeline = Pipeline("training_with_eval")
    # pipeline.add_step(train_step)
    # pipeline.add_step(eval_step)
    # pipeline.run()


if __name__ == "__main__":
    pipeline_eval_example()
