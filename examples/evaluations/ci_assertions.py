"""CI/CD Assertions Example.

Demonstrates using EvalAssert for quality gates in CI/CD pipelines.
This can be used in pytest tests or GitHub Actions.
"""

from __future__ import annotations

from flowyml.evals import (
    Accuracy,
    EvalAssert,
    EvalDataset,
    F1Score,
    Precision,
    evaluate,
)


def ci_assertions_example():
    """Run evaluations with CI/CD assertions."""
    # Prepare test data
    data = EvalDataset.create_classical(
        "golden_set",
        predictions=[1, 0, 1, 1, 0, 1, 0, 1, 1, 0],
        targets=[1, 0, 1, 1, 0, 1, 1, 1, 1, 0],
        version="2.0",
    )

    # Run evaluation
    result = evaluate(
        data=data,
        scorers=[Accuracy(), F1Score(), Precision()],
        experiment="ci_test",
    )

    # Create assertions
    assertion = EvalAssert(eval_result=result)

    print("=== CI/CD Assertions ===")
    print(f"Accuracy: {result.summary.get('accuracy', 0):.4f}")
    print(f"F1 Score: {result.summary.get('f1_score', 0):.4f}")

    # Assert thresholds
    try:
        assertion.assert_min_score("accuracy", 0.8)
        print("✅ Accuracy >= 0.8")
    except AssertionError as e:
        print(f"❌ {e}")

    try:
        assertion.assert_min_score("f1_score", 0.85)
        print("✅ F1 Score >= 0.85")
    except AssertionError as e:
        print(f"❌ {e}")

    try:
        assertion.assert_pass_rate(0.95)
        print("✅ Pass rate >= 95%")
    except AssertionError as e:
        print(f"❌ {e}")

    # Validate all at once (don't raise — we just want the boolean here)
    passed = assertion.validate(raise_on_failure=False)
    print(f"\nOverall: {'PASSED' if passed else 'FAILED'}")


if __name__ == "__main__":
    ci_assertions_example()
