"""Third-Party Adapter Example.

Demonstrates how to use FlowyML's adapter scorers for DeepEval, RAGAS,
and Phoenix evaluation frameworks. These are optional dependencies that
provide additional evaluation metrics.

Prerequisites:
    pip install deepeval        # For DeepEval scorers
    pip install ragas           # For RAGAS scorers
    pip install arize-phoenix-evals  # For Phoenix scorers
"""

from flowyml.evals import (
    EvalDataset,
    evaluate,
    get_scorer,
    list_scorers,
)


def show_available_adapters():
    """List all available adapter scorers."""
    print("=== Available Adapter Scorers ===")
    all_scorers = list_scorers("genai")
    adapter_scorers = [s for s in all_scorers if "." in s["name"]]
    for s in adapter_scorers:
        print(f"  {s['name']:30s} — {s['description']}")
    print(f"\nTotal adapter scorers: {len(adapter_scorers)}")


def registry_usage():
    """Access adapter scorers via the registry with namespaced names."""
    print("\n=== Registry Access ===")

    # All adapter scorers are accessible via get_scorer()
    try:
        scorer = get_scorer("deepeval.hallucination", threshold=0.5)
        print(f"✅ {scorer.name}: {scorer.description}")
    except ImportError as e:
        print(f"⚠️  {e}")

    try:
        scorer = get_scorer("ragas.faithfulness", threshold=0.8)
        print(f"✅ {scorer.name}: {scorer.description}")
    except ImportError as e:
        print(f"⚠️  {e}")

    try:
        scorer = get_scorer("phoenix.qa_correctness", threshold=0.7)
        print(f"✅ {scorer.name}: {scorer.description}")
    except ImportError as e:
        print(f"⚠️  {e}")


def deepeval_example():
    """Run DeepEval adapter scorers."""
    print("\n=== DeepEval Adapter ===")
    try:
        from flowyml.evals import DeepEvalAnswerRelevancy, DeepEvalHallucination

        data = EvalDataset.create_genai(
            "deepeval_test",
            examples=[
                {
                    "inputs": {"query": "What is FlowyML?"},
                    "outputs": "FlowyML is an ML pipeline framework.",
                    "context": ["FlowyML is a developer-first ML pipeline framework."],
                },
            ],
        )

        result = evaluate(
            data=data,
            scorers=[DeepEvalAnswerRelevancy(), DeepEvalHallucination()],
            experiment="deepeval_test",
        )
        print(f"Results: {result.summary}")
    except ImportError:
        print("⚠️  deepeval not installed — pip install deepeval")


def ragas_example():
    """Run RAGAS adapter scorers."""
    print("\n=== RAGAS Adapter ===")
    try:
        from flowyml.evals import RagasFaithfulness, RagasContextPrecision

        data = EvalDataset.create_genai(
            "ragas_test",
            examples=[
                {
                    "inputs": {"query": "What is Python?"},
                    "outputs": "Python is a high-level language.",
                    "expected": "Python is a high-level, general-purpose programming language.",
                    "context": ["Python is a high-level, general-purpose programming language."],
                },
            ],
        )

        result = evaluate(
            data=data,
            scorers=[RagasFaithfulness(), RagasContextPrecision()],
            experiment="ragas_test",
        )
        print(f"Results: {result.summary}")
    except ImportError:
        print("⚠️  ragas not installed — pip install ragas")


def phoenix_example():
    """Run Phoenix adapter scorers."""
    print("\n=== Phoenix Adapter ===")
    try:
        from flowyml.evals import PhoenixToxicity, PhoenixQACorrectness

        data = EvalDataset.create_genai(
            "phoenix_test",
            examples=[
                {
                    "inputs": {"query": "What is Python?"},
                    "outputs": "Python is a high-level language.",
                    "context": ["Python is a programming language."],
                },
            ],
        )

        result = evaluate(
            data=data,
            scorers=[PhoenixToxicity(), PhoenixQACorrectness()],
            experiment="phoenix_test",
        )
        print(f"Results: {result.summary}")
    except ImportError:
        print("⚠️  arize-phoenix-evals not installed — pip install arize-phoenix-evals")


if __name__ == "__main__":
    show_available_adapters()
    registry_usage()
    deepeval_example()
    ragas_example()
    phoenix_example()
