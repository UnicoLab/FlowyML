#!/usr/bin/env python3
"""Example: LangChain Observability with FlowyML.

Demonstrates how to trace LangChain chains and runnables
with full token tracking, cost estimation, and logging.

Requirements:
    pip install "flowyml[langchain]" langchain-openai

Usage:
    export OPENAI_API_KEY="your-key"
    python examples/langchain_observability.py
"""

from __future__ import annotations


def example_trace_chain():
    """Trace a LangChain chain with a context manager."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    from flowyml.integrations.langchain import trace_chain

    # Build a simple chain
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. Be concise."),
            ("human", "{question}"),
        ],
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = prompt | llm

    # Trace it — 2 lines of code!
    with trace_chain("qa_chain", project="demo") as session:
        result = chain.invoke(
            {"question": "What is machine learning?"},
            config=session.config,
        )
        print(f"Answer: {result.content[:100]}...")

    # Summary prints automatically:
    # ═══════════════════════════════════════════════════
    #   🔗 FlowyML Trace — qa_chain (langchain)
    # ═══════════════════════════════════════════════════
    #   🤖 LLM Calls  : 1
    #   📊 Tokens     : ...
    #   💰 Est. Cost  : $...
    # ═══════════════════════════════════════════════════


def example_observe_chain():
    """Use the @observe_chain decorator for zero-config tracing."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    from flowyml.integrations.langchain import observe_chain

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Summarize the following in one sentence."),
            ("human", "{text}"),
        ],
    )
    llm = ChatOpenAI(model="gpt-4o-mini")
    chain = prompt | llm

    @observe_chain(name="summarizer", project="nlp")
    def summarize(text: str, flowyml_session=None):
        return chain.invoke(
            {"text": text},
            config=flowyml_session.config,
        )

    result = summarize(
        "Artificial intelligence is the simulation of human intelligence "
        "by machines, particularly computer systems. It encompasses "
        "learning, reasoning, and self-correction.",
    )
    print(f"Summary: {result.content}")


def example_instrument_chain():
    """Permanently instrument a chain — trace every invocation."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    from flowyml.integrations.langchain import instrument_chain

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Translate to French."),
            ("human", "{text}"),
        ],
    )
    llm = ChatOpenAI(model="gpt-4o-mini")
    chain = prompt | llm

    # Instrument once
    traced_chain = instrument_chain(chain, name="translator", project="demo")

    # Every call is auto-traced
    result1 = traced_chain.invoke({"text": "Hello, how are you?"})
    print(f"French: {result1.content}")

    result2 = traced_chain.invoke({"text": "The weather is nice today."})
    print(f"French: {result2.content}")


if __name__ == "__main__":
    import sys

    examples = {
        "trace": example_trace_chain,
        "observe": example_observe_chain,
        "instrument": example_instrument_chain,
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
