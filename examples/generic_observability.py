#!/usr/bin/env python3
"""Example: Generic GenAI Observability with FlowyML.

Works with ANY GenAI framework — CrewAI, AutoGen, Haystack, DSPy, or custom code.
No framework-specific dependencies needed.

Requirements:
    pip install flowyml

Usage:
    python examples/generic_observability.py
"""

from __future__ import annotations

import time


def example_decorator():
    """Use @observe() with any custom GenAI code."""
    from flowyml.integrations.generic import log_llm_call, observe

    @observe(name="research_pipeline", project="analytics")
    def research(topic: str, flowyml_session=None):
        """Simulate a multi-step research pipeline."""

        # Step 1: Simulate an embedding call
        from flowyml.integrations.generic import log_embedding_call

        log_embedding_call(
            model="text-embedding-3-small",
            input_text=topic,
            token_count=len(topic.split()),
            tracer=flowyml_session,
        )

        # Step 2: Simulate an LLM call
        time.sleep(0.1)  # Simulate latency
        log_llm_call(
            model="gpt-4o-mini",
            prompt=f"Research the topic: {topic}",
            response="Here are the key findings about AI trends...",
            prompt_tokens=50,
            completion_tokens=200,
            tracer=flowyml_session,
        )

        # Step 3: Simulate a tool call
        from flowyml.integrations.generic import log_tool_call

        log_tool_call(
            name="web_search",
            tool_input=topic,
            tool_output="Found 15 relevant articles",
            tracer=flowyml_session,
        )

        # Step 4: Simulate a summary LLM call
        log_llm_call(
            model="gpt-4o",
            prompt="Summarize all findings",
            response="The research shows three main trends...",
            prompt_tokens=300,
            completion_tokens=150,
            tracer=flowyml_session,
        )

        return "Research complete!"

    # Just call it — everything is traced automatically
    result = research("latest AI agent frameworks")
    print(f"Result: {result}")


def example_context_manager():
    """Use trace() for block-scoped tracing."""
    from flowyml.integrations.generic import trace

    with trace("data_pipeline", project="ml_ops") as tracer:
        # Step 1: Embedding generation
        span1 = tracer.start_span("embedding", "generate_embeddings")
        time.sleep(0.05)
        span1.set_tokens(prompt_tokens=500, model="text-embedding-3-small")
        tracer.session.total_embedding_calls += 1
        tracer.session.add_model("text-embedding-3-small")
        tracer.end_span(span1, outputs={"vectors": 100})

        # Step 2: LLM processing
        span2 = tracer.start_span("llm", "analyze_data")
        time.sleep(0.05)
        span2.set_tokens(
            prompt_tokens=200,
            completion_tokens=500,
            model="gpt-4o",
        )
        tracer.session.total_llm_calls += 1
        tracer.session.add_model("gpt-4o")
        tracer.session.record_tokens(
            prompt_tokens=200,
            completion_tokens=500,
            cost=span2.cost,
        )
        tracer.end_span(span2, outputs={"analysis": "positive trend"})

        # Step 3: Tool execution
        span3 = tracer.start_span("tool", "save_results")
        time.sleep(0.02)
        span3.tool_name = "database_writer"
        tracer.session.total_tool_calls += 1
        tracer.end_span(span3, outputs={"rows_written": 42})


def example_span_context_manager():
    """Use span() for the simplest possible tracing."""
    from flowyml.integrations.generic import span

    # Each span is self-contained
    with span("quick_llm_call", "llm") as s:
        time.sleep(0.01)
        s.set_tokens(prompt_tokens=10, completion_tokens=20, model="gpt-4o-mini")
        s.outputs = {"response": "Hello!"}

    print(f"Span completed: {s.name}, duration={s.duration:.3f}s, cost=${s.cost:.6f}")


def example_fire_and_forget():
    """Log individual calls without any wrapping."""
    from flowyml.integrations.generic import (
        log_embedding_call,
        log_llm_call,
        log_tool_call,
    )

    # These are fire-and-forget — each creates its own session
    log_llm_call(
        model="gpt-4o",
        prompt="What is the meaning of life?",
        response="42",
        prompt_tokens=10,
        completion_tokens=1,
        project="philosophy",
    )

    log_tool_call(
        name="calculator",
        tool_input="6 * 7",
        tool_output="42",
        project="math",
    )

    log_embedding_call(
        model="text-embedding-3-small",
        input_text=["Hello", "World"],
        token_count=2,
        project="search",
    )

    print("All calls logged successfully!")


if __name__ == "__main__":
    import sys

    examples = {
        "decorator": example_decorator,
        "context": example_context_manager,
        "span": example_span_context_manager,
        "fire": example_fire_and_forget,
    }

    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("Available examples:")
        for name in examples:
            print(f"  python {sys.argv[0]} {name}")
        print("\nRunning all examples...\n")
        for name, fn in examples.items():
            print(f"\n{'═' * 60}")
            print(f"  Example: {name}")
            print(f"{'═' * 60}")
            fn()
