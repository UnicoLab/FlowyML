"""🔗 LangGraph Observability — FlowyML Integration Examples.

This example demonstrates 4 ways to add full GenAI observability
to your LangGraph/LangChain agents using FlowyML:

  1. FlowyMLCallbackHandler — Direct callback handler
  2. trace_graph()         — Context manager
  3. @observe()            — Decorator
  4. instrument()          — Permanent graph wrapper

Prerequisites:
    pip install langgraph langchain-openai flowyml

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from __future__ import annotations

import importlib.util

# ──────────────────────────────────────────────────────
# Optional dependency guard — skip cleanly if libs are missing
# ──────────────────────────────────────────────────────
_REQUIRED = ("langgraph", "langchain_openai", "langchain_core")
_MISSING = [m for m in _REQUIRED if importlib.util.find_spec(m) is None]
if _MISSING:
    print(
        "⚠️  This example requires LangGraph + LangChain.\n"
        f"    Missing: {', '.join(_MISSING)}\n"
        '    Install with:  pip install "flowyml[langgraph]" langchain-openai',
    )
    raise SystemExit(0)

# ──────────────────────────────────────────────────────
# Setup: Build a simple LangGraph ReAct Agent
# ──────────────────────────────────────────────────────
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402

from flowyml.integrations.langgraph import (  # noqa: E402
    FlowyMLCallbackHandler,
    instrument,
    observe,
    trace_graph,
)


# Define tools
@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    weather_data = {
        "san francisco": "☀️ 68°F, sunny",
        "new york": "🌧️ 45°F, rainy",
        "london": "☁️ 52°F, cloudy",
    }
    return weather_data.get(city.lower(), f"🌈 72°F for {city}")


@tool
def get_population(city: str) -> str:
    """Get the population of a city."""
    pop_data = {
        "san francisco": "873,965",
        "new york": "8,336,817",
        "london": "8,982,000",
    }
    return pop_data.get(city.lower(), "Unknown")


# Build the agent
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
graph = create_react_agent(llm, tools=[get_weather, get_population])


# ──────────────────────────────────────────────────────
# Example 1: Direct Callback Handler
# ──────────────────────────────────────────────────────
def example_callback_handler():
    """Use FlowyMLCallbackHandler directly for maximum control."""
    print("\n🔗 Example 1: Direct Callback Handler")
    print("─" * 40)

    handler = FlowyMLCallbackHandler(
        session_name="weather_agent",
        project="examples",
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content="What's the weather in San Francisco?")]},
        config={"callbacks": [handler]},
    )

    # Access the session for metrics
    handler.session.print_summary()

    print(f"Agent response: {result['messages'][-1].content}")


# ──────────────────────────────────────────────────────
# Example 2: Context Manager (trace_graph)
# ──────────────────────────────────────────────────────
def example_context_manager():
    """Use trace_graph() for clean session-scoped tracing."""
    print("\n🔗 Example 2: Context Manager (trace_graph)")
    print("─" * 40)

    with trace_graph("city_info_agent", project="examples") as session:
        # The session.config contains the callback handler
        result = graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Tell me the weather and population of New York",
                    ),
                ],
            },
            config=session.config,
        )

    # Summary is auto-printed, session.summary() also available
    print(f"Agent response: {result['messages'][-1].content}")
    print(f"Total cost: ${session.total_cost:.4f}")
    print(f"Total tokens: {session.total_tokens:,}")


# ──────────────────────────────────────────────────────
# Example 3: Decorator (@observe)
# ──────────────────────────────────────────────────────
@observe(name="travel_assistant", project="examples")
def example_decorator(query: str, flowyml_session=None):
    """Use @observe() for the cleanest integration.

    The decorator automatically creates a trace session
    and injects it as `flowyml_session`.
    """
    print("\n🔗 Example 3: Decorator (@observe)")
    print("─" * 40)

    result = graph.invoke(
        {"messages": [HumanMessage(content=query)]},
        config=flowyml_session.config if flowyml_session else {},
    )

    return result["messages"][-1].content


# ──────────────────────────────────────────────────────
# Example 4: Permanent Instrumentation
# ──────────────────────────────────────────────────────
def example_instrumented():
    """Use instrument() to permanently wrap a graph."""
    print("\n🔗 Example 4: Permanent Instrumentation")
    print("─" * 40)

    # Wrap the graph once — every invocation is auto-traced
    traced_graph = instrument(
        graph,
        name="smart_agent",
        project="examples",
    )

    # Every call is automatically observed!
    result = traced_graph.invoke(
        {"messages": [HumanMessage(content="What's the weather in London?")]},
    )

    print(f"Agent response: {result['messages'][-1].content}")

    # Call again — still traced!
    result2 = traced_graph.invoke(
        {"messages": [HumanMessage(content="And the population?")]},
    )

    print(f"Agent response: {result2['messages'][-1].content}")


# ──────────────────────────────────────────────────────
# Example 5: Multi-turn Conversation with Full Tracking
# ──────────────────────────────────────────────────────
def example_multi_turn():
    """Track an entire multi-turn conversation in one session."""
    print("\n🔗 Example 5: Multi-turn Conversation")
    print("─" * 40)

    with trace_graph("multi_turn_agent", project="examples") as session:
        messages = []

        # Turn 1
        messages.append(HumanMessage(content="What's the weather in SF?"))
        result = graph.invoke(
            {"messages": messages},
            config=session.config,
        )
        messages = result["messages"]
        print(f"Turn 1: {messages[-1].content}")

        # Turn 2
        messages.append(HumanMessage(content="And the population?"))
        result = graph.invoke(
            {"messages": messages},
            config=session.config,
        )
        messages = result["messages"]
        print(f"Turn 2: {messages[-1].content}")

        # Turn 3
        messages.append(HumanMessage(content="Compare that to New York"))
        result = graph.invoke(
            {"messages": messages},
            config=session.config,
        )
        messages = result["messages"]
        print(f"Turn 3: {messages[-1].content}")

    # All 3 turns are tracked in one session!
    print(f"\nTotal LLM calls across 3 turns: {session.total_llm_calls}")
    print(f"Total tokens: {session.total_tokens:,}")
    print(f"Total estimated cost: ${session.total_cost:.4f}")


# ──────────────────────────────────────────────────────
# Run Examples
# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    examples = {
        "1": ("Callback Handler", example_callback_handler),
        "2": ("Context Manager", example_context_manager),
        "3": ("Decorator", lambda: example_decorator("What's the weather in SF and NY?")),
        "4": ("Instrumented Graph", example_instrumented),
        "5": ("Multi-turn Conversation", example_multi_turn),
    }

    if len(sys.argv) > 1:
        choice = sys.argv[1]
        if choice in examples:
            name, func = examples[choice]
            print(f"\n{'=' * 60}")
            print(f"  Running: {name}")
            print(f"{'=' * 60}")
            func()
        else:
            print(f"Unknown example: {choice}. Choose 1-5.")
    else:
        print("🔗 FlowyML + LangGraph Observability Examples")
        print("=" * 60)
        print("\nUsage: python langgraph_observability.py [1-5]")
        print("\nAvailable examples:")
        for k, (name, _) in examples.items():
            print(f"  {k}. {name}")
        print("\nRunning all examples...\n")

        for k, (name, func) in examples.items():
            try:
                print(f"\n{'=' * 60}")
                print(f"  Running Example {k}: {name}")
                print(f"{'=' * 60}")
                if k == "3":
                    func()
                else:
                    func()
            except Exception as e:
                print(f"  ⚠️  Skipped (requires API key): {e}")
