"""Classical ML Evaluation Example.

Demonstrates how to evaluate classification and regression models
using FlowyML's built-in scorers.
"""

from flowyml.evals import (
    EvalDataset,
    EvalSuite,
    evaluate,
    Accuracy,
    Precision,
    Recall,
    F1Score,
    MSE,
    RMSE,
    R2Score,
)


def classification_example():
    """Evaluate a classification model."""
    # Create evaluation dataset
    predictions = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
    targets = [1, 0, 0, 1, 0, 1, 1, 0, 1, 0]

    data = EvalDataset.create_classical(
        name="binary_classifier_v2",
        predictions=predictions,
        targets=targets,
        version="2.0",
        tags={"model": "xgboost", "task": "fraud_detection"},
    )

    # Define an evaluation suite
    suite = EvalSuite(
        name="classification_quality",
        scorers=[
            Accuracy(threshold=0.85),
            Precision(threshold=0.8),
            Recall(threshold=0.8),
            F1Score(threshold=0.8),
        ],
        description="Standard classification quality gates",
    )

    # Run evaluation
    result = suite.run(data=data, experiment="fraud_detection_v2")

    # Inspect results
    print("=== Classification Results ===")
    print(f"Passed: {result.passed}")
    print(f"Pass Rate: {result.pass_rate:.2%}")
    for name, value in result.summary.items():
        print(f"  {name}: {value:.4f}")


def regression_example():
    """Evaluate a regression model."""
    predictions = [2.5, 3.1, 4.0, 5.2, 6.1]
    targets = [2.4, 3.0, 4.2, 5.0, 6.3]

    data = EvalDataset.create_classical(
        name="price_predictor_v3",
        predictions=predictions,
        targets=targets,
        version="3.0",
    )

    result = evaluate(
        data=data,
        scorers=[MSE(), RMSE(), R2Score(threshold=0.9)],
        experiment="price_prediction_v3",
    )

    print("\n=== Regression Results ===")
    print(f"Passed: {result.passed}")
    for name, value in result.summary.items():
        print(f"  {name}: {value:.4f}")


if __name__ == "__main__":
    classification_example()
    regression_example()
