"""🤖 Multi-Turn Chatbot Session — FlowyML GenAI Observability.

Demonstrates session-level aggregation for a chatbot application:
  • Each turn (user↔assistant) is tracked with tokens, cost, latency
  • Session-level summaries aggregate all turns
  • Optional: auto-evaluations run in background threads
  • Optional: real-time event streaming for dashboards

This example simulates a chatbot without calling a real LLM.
"""

from __future__ import annotations

import time

from flowyml.integrations.base import session_trace
from flowyml.integrations.streaming import SessionEventStream


def simple_chatbot_session():
    """Basic multi-turn session tracking."""
    print("=" * 60)
    print("  Example 1: Simple Chatbot Session")
    print("=" * 60)

    with session_trace(
        "customer_support_bot",
        project="support",
        framework="custom",
        thread_id="thread-abc-123",
        user_id="user-42",
        auto_log=False,
        print_summary=True,
    ) as tracer:
        # Turn 1: User asks a question
        with tracer.turn("user") as turn:
            turn.content = "What is your return policy?"

            # Simulate LLM call via span
            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            time.sleep(0.05)  # Simulate latency
            span.set_tokens(
                prompt_tokens=45,
                completion_tokens=120,
                model="gpt-4o-mini",
            )
            tracer.end_span(
                span,
                outputs={
                    "content": "Our return policy allows returns within 30 days of purchase with a receipt.",
                },
            )
            turn.content = "Our return policy allows returns within 30 days of purchase with a receipt."

        # Turn 2: Follow-up question
        with tracer.turn("user") as turn:
            turn.content = "Can I return without a receipt?"

            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            time.sleep(0.03)
            span.set_tokens(
                prompt_tokens=80,
                completion_tokens=95,
                model="gpt-4o-mini",
            )
            tracer.end_span(
                span,
                outputs={
                    "content": "Without a receipt, we can offer store credit at the current selling price.",
                },
            )
            turn.content = "Without a receipt, we can offer store credit at the current selling price."

        # Turn 3: User asks about a tool
        with tracer.turn("user") as turn:
            turn.content = "Can you check my order status for order #12345?"

            # Simulate tool call span
            tool_span = tracer.start_span("tool", "order_lookup")
            tool_span.tool_name = "order_lookup"
            tool_span.tool_input = {"order_id": "12345"}
            tool_span.tool_output = {"status": "shipped", "eta": "2 days"}
            time.sleep(0.02)
            tracer.end_span(tool_span)

            # Then LLM reply
            llm_span = tracer.start_span("llm", "gpt-4o-mini:reply")
            time.sleep(0.04)
            llm_span.set_tokens(
                prompt_tokens=110,
                completion_tokens=75,
                model="gpt-4o-mini",
            )
            tracer.end_span(
                llm_span,
                outputs={
                    "content": "Order #12345 has been shipped and should arrive in approximately 2 business days.",
                },
            )
            turn.content = "Order #12345 has been shipped and should arrive in approximately 2 business days."


def session_with_streaming():
    """Session with real-time event streaming."""
    print("\n" + "=" * 60)
    print("  Example 2: Session with Event Streaming")
    print("=" * 60)

    # Set up event stream
    events_received = []
    stream = SessionEventStream(
        callback=lambda etype, data: events_received.append(
            (etype, data),
        ),
    )

    with session_trace(
        "streaming_bot",
        project="demo",
        auto_log=False,
        print_summary=True,
    ) as tracer:
        # Attach the event stream
        tracer.genai_session.on_event(stream)

        with tracer.turn("user") as turn:
            turn.content = "Hello!"
            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            span.set_tokens(
                prompt_tokens=10,
                completion_tokens=20,
                model="gpt-4o-mini",
            )
            time.sleep(0.01)
            tracer.end_span(span, outputs={"content": "Hi there!"})
            turn.content = "Hi there!"

    print(f"\n  📡 Events captured: {len(events_received)}")
    for etype, data in events_received:
        print(f"     → {etype}: {str(data)[:80]}...")


def session_with_manual_evals():
    """Session with manually attached evaluation scores."""
    print("\n" + "=" * 60)
    print("  Example 3: Session with Manual Evals")
    print("=" * 60)

    with session_trace(
        "eval_bot",
        project="quality",
        auto_log=False,
        print_summary=True,
    ) as tracer:
        with tracer.turn("user") as turn:
            turn.content = "What is machine learning?"
            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            span.set_tokens(
                prompt_tokens=15,
                completion_tokens=80,
                model="gpt-4o-mini",
            )
            tracer.end_span(
                span,
                outputs={
                    "content": "Machine learning is a subset of AI that enables systems to learn from data.",
                },
            )
            turn.content = "Machine learning is a subset of AI that enables systems to learn from data."

        # Manually add evals after the turn
        tracer.genai_session.add_eval(
            "relevance",
            0.92,
            passed=True,
            rationale="Response directly answers the question.",
        )
        tracer.genai_session.add_eval(
            "coherence",
            0.88,
            passed=True,
            rationale="Clear and well-structured explanation.",
        )

        with tracer.turn("user") as turn:
            turn.content = "Tell me more about neural networks"
            span = tracer.start_span("llm", "gpt-4o-mini:reply")
            span.set_tokens(
                prompt_tokens=30,
                completion_tokens=120,
                model="gpt-4o-mini",
            )
            tracer.end_span(
                span,
                outputs={
                    "content": "Neural networks are computing systems inspired by biological neural networks.",
                },
            )
            turn.content = "Neural networks are computing systems inspired by biological neural networks."

        tracer.genai_session.add_eval(
            "relevance",
            0.85,
            passed=True,
            rationale="Good follow-up response.",
        )
        tracer.genai_session.add_eval(
            "coherence",
            0.91,
            passed=True,
            rationale="Clear explanation with good context.",
        )


def experiment_tracking():
    """Convert session metrics for experiment tracking."""
    print("\n" + "=" * 60)
    print("  Example 4: Experiment Metrics from Session")
    print("=" * 60)

    with session_trace(
        "experiment_bot",
        project="research",
        auto_log=False,
        print_summary=False,
    ) as tracer:
        for i in range(5):
            with tracer.turn("user") as turn:
                turn.content = f"Question {i + 1}"
                span = tracer.start_span("llm", "gpt-4o-mini:reply")
                span.set_tokens(
                    prompt_tokens=20 + i * 5,
                    completion_tokens=50 + i * 10,
                    model="gpt-4o-mini",
                )
                time.sleep(0.01)
                tracer.end_span(
                    span,
                    outputs={"content": f"Answer {i + 1}"},
                )
                turn.content = f"Answer {i + 1}"

            tracer.genai_session.add_eval(
                "relevance",
                0.7 + i * 0.05,
            )

    # Get experiment-ready metrics
    metrics = tracer.genai_session.to_experiment_metrics()
    print("\n  📊 Experiment Metrics:")
    for k, v in metrics.items():
        print(f"     {k}: {v:.4f}")


if __name__ == "__main__":
    simple_chatbot_session()
    session_with_streaming()
    session_with_manual_evals()
    experiment_tracking()
