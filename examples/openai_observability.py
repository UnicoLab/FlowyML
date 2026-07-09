#!/usr/bin/env python3
"""Example: OpenAI SDK Observability with FlowyML.

Demonstrates how to trace OpenAI API calls directly — no LangChain needed.
Full token tracking, cost estimation, and streaming support.

Requirements:
    pip install "flowyml[openai]"

Usage:
    export OPENAI_API_KEY="your-key"
    python examples/openai_observability.py
"""

from __future__ import annotations

import importlib.util
import os


def _preflight() -> bool:
    """Return ``True`` if the OpenAI SDK and an API key are available."""
    if importlib.util.find_spec("openai") is None:
        print(
            '⚠️  This example requires the OpenAI SDK.\n    Install with:  pip install "flowyml[openai]"',
        )
        return False
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "⚠️  Set OPENAI_API_KEY to run this example — it makes real "
            "OpenAI API calls.\n    export OPENAI_API_KEY=sk-...",
        )
        return False
    return True


def example_traced_client():
    """Drop-in replacement for openai.OpenAI()."""
    from flowyml.integrations.openai_integration import TracedOpenAI

    # Just replace openai.OpenAI() with TracedOpenAI()
    client = TracedOpenAI(project="demo")

    # Chat completion — automatically traced
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain quantum computing in 2 sentences."},
        ],
        temperature=0,
    )
    print(f"Response: {response.choices[0].message.content}")

    # Multiple calls — all tracked in the same session
    response2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Now explain it to a 5 year old."},
        ],
    )
    print(f"Simple: {response2.choices[0].message.content}")

    # Embeddings — also tracked
    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input="Hello world",
    )
    print(f"Embedding dimensions: {len(embedding.data[0].embedding)}")

    # Print the summary
    client.finalize()


def example_patch_existing():
    """Patch an existing OpenAI client for tracing."""
    import openai

    from flowyml.integrations.openai_integration import patch_openai

    client = openai.OpenAI()
    tracer = patch_openai(client, project="production", name="api_calls")

    # Use the client exactly as before
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What is 2+2?"}],
    )
    print(f"Answer: {response.choices[0].message.content}")

    # Access metrics
    tracer.session.print_summary()
    print(f"Total cost: ${tracer.session.total_cost:.4f}")
    print(f"Total tokens: {tracer.session.total_tokens}")


def example_streaming():
    """Streaming responses are tracked automatically."""
    from flowyml.integrations.openai_integration import TracedOpenAI

    client = TracedOpenAI(project="streaming_demo")

    print("Streaming response: ", end="")
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Write a haiku about AI"}],
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()

    # Tokens counted after stream completes
    client.finalize()


def example_decorator():
    """Use the @trace_openai decorator."""
    import openai

    from flowyml.integrations.openai_integration import trace_openai

    client = openai.OpenAI()

    @trace_openai(name="translator", project="nlp")
    def translate(text: str, target_lang: str = "French"):
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Translate to {target_lang}."},
                {"role": "user", "content": text},
            ],
        )

    result = translate("Hello, how are you?")
    print(f"Translation: {result.choices[0].message.content}")


if __name__ == "__main__":
    import sys

    examples = {
        "traced": example_traced_client,
        "patch": example_patch_existing,
        "stream": example_streaming,
        "decorator": example_decorator,
    }

    if not _preflight():
        raise SystemExit(0)

    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("Available examples:")
        for name in examples:
            print(f"  python {sys.argv[0]} {name}")
        print("\nRunning 'traced' example...\n")
        example_traced_client()
