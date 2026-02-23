"""GenAI Evaluation Example.

Demonstrates how to evaluate LLM outputs using FlowyML's
LLM-as-a-judge scorers.
"""

from flowyml.evals import (
    EvalDataset,
    evaluate,
    Relevance,
    Coherence,
    Toxicity,
    Faithfulness,
)


def genai_evaluation():
    """Evaluate LLM outputs with GenAI judges."""
    # Create a GenAI evaluation dataset
    data = EvalDataset.create_genai(
        name="rag_golden_set",
        examples=[
            {
                "inputs": {"query": "What is FlowyML?"},
                "outputs": "FlowyML is a next-generation ML pipeline framework " "that combines simplicity with power.",
                "expected": "FlowyML is an ML pipeline orchestration framework.",
                "context": ["FlowyML is a developer-first ML pipeline framework."],
            },
            {
                "inputs": {"query": "How to create a pipeline?"},
                "outputs": "Use Pipeline class: `pipeline = Pipeline('my_pipeline')`",
                "expected": "Create a Pipeline instance and add steps to it.",
                "context": ["The Pipeline class is the core of FlowyML."],
            },
        ],
        version="1.0",
        tags={"domain": "product_docs"},
    )

    # Evaluate with multiple GenAI scorers
    result = evaluate(
        data=data,
        scorers=[
            Relevance(model="openai:/gpt-4o-mini", threshold=0.7),
            Coherence(model="openai:/gpt-4o-mini"),
            Toxicity(model="openai:/gpt-4o-mini", threshold=0.1),
            Faithfulness(model="openai:/gpt-4o-mini", threshold=0.8),
        ],
        experiment="rag_quality_v1",
    )

    print("=== GenAI Evaluation Results ===")
    print(f"Overall passed: {result.passed}")
    print(f"Pass rate: {result.pass_rate:.2%}")
    print()

    for scorer_name in result.scorer_names:
        scores = result.get_scores(scorer_name)
        print(f"--- {scorer_name} ---")
        for i, feedback in enumerate(scores):
            print(f"  Example {i + 1}: {feedback.value:.2f}")
            if feedback.rationale:
                print(f"    Rationale: {feedback.rationale[:100]}...")


if __name__ == "__main__":
    genai_evaluation()
