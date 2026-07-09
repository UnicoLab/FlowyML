"""🔬 Session Evaluation Example — Async Quality Monitoring.

Demonstrates how to auto-evaluate each chatbot turn using
FlowyML's evaluation system (scorers) integrated with the
session-level observability layer.

This example uses a mock scorer since it doesn't require
an OpenAI API key. In production, use scorers like:
    Relevance(model="gpt-4o-mini", threshold=0.7)
    Toxicity(model="gpt-4o-mini", threshold=0.1)
"""

from __future__ import annotations

import time

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType
from flowyml.integrations.base import session_trace
from flowyml.integrations.eval_bridge import SessionEvaluator


# ─────────────────────────────────────────────────────
# Mock scorer for demonstration (no API key needed)
# ─────────────────────────────────────────────────────
class MockRelevanceScorer(Scorer):
    """Simple mock scorer that returns a fixed score."""

    name = "mock_relevance"
    scorer_type = ScorerType.GENAI
    description = "Mock relevance scorer for demo"

    def __init__(self, threshold: float = 0.7):
        super().__init__(threshold=threshold)

    def score(self, *, inputs=None, outputs=None, **kw) -> ScorerFeedback:
        # Simple heuristic: longer outputs = higher relevance
        output_len = len(str(outputs or ""))
        value = min(1.0, output_len / 200)
        return ScorerFeedback(
            name=self.name,
            value=round(value, 2),
            scorer_type=self.scorer_type.value,
            passed=value >= (self.threshold or 0),
            rationale=f"Output length: {output_len} chars → score: {value:.2f}",
        )


class MockToxicityScorer(Scorer):
    """Mock toxicity scorer (always returns low toxicity)."""

    name = "mock_toxicity"
    scorer_type = ScorerType.SAFETY
    description = "Mock toxicity scorer for demo"
    lower_is_better = True

    def __init__(self, threshold: float = 0.1):
        super().__init__(threshold=threshold)

    def score(self, *, inputs=None, outputs=None, **kw) -> ScorerFeedback:
        value = 0.02  # Always safe
        return ScorerFeedback(
            name=self.name,
            value=value,
            scorer_type=self.scorer_type.value,
            passed=value <= (self.threshold or 1.0),
            rationale="No toxic content detected.",
        )


def session_with_auto_evals():
    """Run a chatbot session with automatic evaluations."""
    print("=" * 60)
    print("  Session with Auto-Evaluations")
    print("=" * 60)

    # Create evaluator with mock scorers
    evaluator = SessionEvaluator(
        [
            MockRelevanceScorer(threshold=0.5),
            MockToxicityScorer(threshold=0.1),
        ],
        async_mode=False,  # Sync for demo clarity
    )

    with session_trace(
        "eval_chatbot",
        project="quality_monitoring",
        evaluator=evaluator,
        auto_log=False,
        print_summary=True,
    ) as tracer:
        # Turn 1
        with tracer.turn("user") as turn:
            turn.content = "What is deep learning?"
            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            span.set_tokens(
                prompt_tokens=12,
                completion_tokens=85,
                model="gpt-4o-mini",
            )
            time.sleep(0.02)
            tracer.end_span(
                span,
                outputs={
                    "content": "Deep learning is a subset of machine learning "
                    "that uses neural networks with many layers to analyze "
                    "various factors of data. It has revolutionized fields "
                    "like computer vision and natural language processing.",
                },
            )
            turn.content = (
                "Deep learning is a subset of machine learning "
                "that uses neural networks with many layers to analyze "
                "various factors of data."
            )

        # Turn 2
        with tracer.turn("user") as turn:
            turn.content = "How does backpropagation work?"
            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            span.set_tokens(
                prompt_tokens=18,
                completion_tokens=120,
                model="gpt-4o-mini",
            )
            time.sleep(0.02)
            tracer.end_span(
                span,
                outputs={
                    "content": "Backpropagation is the core algorithm for "
                    "training neural networks. It computes the gradient of "
                    "the loss function with respect to each weight by "
                    "propagating errors backward through the network.",
                },
            )
            turn.content = "Backpropagation is the core algorithm for training neural networks."

        # Turn 3 — short answer
        with tracer.turn("user") as turn:
            turn.content = "OK, thanks"
            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            span.set_tokens(
                prompt_tokens=8,
                completion_tokens=5,
                model="gpt-4o-mini",
            )
            time.sleep(0.01)
            tracer.end_span(
                span,
                outputs={"content": "You're welcome!"},
            )
            turn.content = "You're welcome!"

    # Wait for async evals (already sync in this demo)
    evaluator.wait_for_pending()

    # Show per-turn eval details
    print("\n  📋 Per-Turn Eval Details:")
    for turn in tracer.genai_session.turns:
        print(f"\n  Turn {turn.turn_index} ({turn.role}): {turn.content[:50]}")
        for ev in turn.eval_results:
            status = "✅" if ev.get("passed") else "❌"
            print(
                f"    {status} {ev['scorer']}: {ev['score']:.2f} — {ev.get('rationale', '')[:60]}",
            )

    evaluator.shutdown()


if __name__ == "__main__":
    session_with_auto_evals()
