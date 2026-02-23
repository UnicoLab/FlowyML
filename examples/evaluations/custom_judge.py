"""Custom Scorer Example.

Demonstrates creating custom scorers using `make_judge()` for
LLM-based judges and `make_scorer()` for Python function scorers.
"""

from flowyml.evals import (
    EvalDataset,
    evaluate,
    make_judge,
    make_scorer,
)


def custom_function_scorer():
    """Create a scorer from a Python function."""

    def word_count_score(*, outputs=None, **kwargs):
        """Score based on response length (normalized to 0-1)."""
        if outputs is None:
            return 0.0
        words = len(str(outputs).split())
        return min(words / 50, 1.0)

    scorer = make_scorer(
        "word_count",
        word_count_score,
        scorer_type="genai",
        threshold=0.3,
        description="Scores based on response length",
    )

    data = EvalDataset.create_genai(
        "length_test",
        examples=[
            {"outputs": "Short."},
            {"outputs": "This is a medium-length response with some details."},
            {"outputs": " ".join(["word"] * 100)},
        ],
    )

    result = evaluate(data=data, scorers=[scorer])
    print("=== Word Count Scorer ===")
    for i, fb in enumerate(result.get_scores("word_count")):
        print(f"  Example {i + 1}: score={fb.value:.2f}, passed={fb.passed}")


def custom_llm_judge():
    """Create a custom LLM judge with instructions and rubric."""
    # Simple judge
    quality_judge = make_judge(
        name="response_quality",
        instructions=(
            "Evaluate if the response correctly answers the question. " "Consider: accuracy, completeness, conciseness."
        ),
        model="openai:/gpt-4o-mini",
        threshold=0.7,
    )

    # Rubric-based judge
    rubric_judge = make_judge(
        name="technical_accuracy",
        instructions="Evaluate the technical accuracy of the response.",
        model="openai:/gpt-4o-mini",
        rubric={
            5: "Perfectly accurate, cites correct sources",
            4: "Mostly accurate, minor omissions",
            3: "Partially accurate, some errors",
            2: "Mostly inaccurate",
            1: "Completely wrong or hallucinated",
        },
    )

    data = EvalDataset.create_genai(
        "quality_test",
        examples=[
            {
                "inputs": {"query": "What is Python?"},
                "outputs": "Python is a high-level programming language known for readability.",
            },
        ],
    )

    result = evaluate(data=data, scorers=[quality_judge, rubric_judge])
    print("\n=== Custom LLM Judges ===")
    for name in result.scorer_names:
        scores = result.get_scores(name)
        for fb in scores:
            print(f"  {name}: {fb.value:.2f} — {fb.rationale or 'No rationale'}")


if __name__ == "__main__":
    custom_function_scorer()
    custom_llm_judge()
