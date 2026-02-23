"""Tests for GenAI Observability integrations.

All tests use mocks — no API keys or external services needed.
"""

import time

import pytest

from flowyml.integrations.base import (
    BaseTracer,
    TraceSession,
    TraceSpan,
    estimate_cost,
    log_embedding_call,
    log_llm_call,
    log_tool_call,
    observe,
    safe_serialize,
    trace,
)
from flowyml.integrations.generic import span


# ════════════════════════════════════════════════════════
# TraceSpan Tests
# ════════════════════════════════════════════════════════
class TestTraceSpan:
    def test_create_span(self):
        s = TraceSpan(
            event_id="e1",
            trace_id="t1",
            parent_id=None,
            event_type="llm",
            name="test_llm",
        )
        assert s.status == "running"
        assert s.duration is None

    def test_end_span_success(self):
        s = TraceSpan(
            event_id="e1",
            trace_id="t1",
            parent_id=None,
            event_type="llm",
            name="test",
        )
        s.end(outputs={"result": "ok"})
        assert s.status == "success"
        assert s.duration is not None
        assert s.duration >= 0
        assert s.outputs == {"result": "ok"}

    def test_end_span_error(self):
        s = TraceSpan(
            event_id="e1",
            trace_id="t1",
            parent_id=None,
            event_type="tool",
            name="test",
        )
        s.end(error="something failed")
        assert s.status == "error"
        assert s.error == "something failed"

    def test_set_tokens(self):
        s = TraceSpan(
            event_id="e1",
            trace_id="t1",
            parent_id=None,
            event_type="llm",
            name="test",
        )
        s.set_tokens(
            prompt_tokens=100,
            completion_tokens=200,
            model="gpt-4o-mini",
        )
        assert s.prompt_tokens == 100
        assert s.completion_tokens == 200
        assert s.total_tokens == 300
        assert s.model == "gpt-4o-mini"
        assert s.cost > 0

    def test_to_event_dict(self):
        s = TraceSpan(
            event_id="e1",
            trace_id="t1",
            parent_id="p1",
            event_type="tool",
            name="search",
        )
        s.tool_name = "web_search"
        s.end(outputs={"results": "found"})
        d = s.to_event_dict()
        assert d["event_id"] == "e1"
        assert d["trace_id"] == "t1"
        assert d["parent_id"] == "p1"
        assert d["status"] == "success"
        assert d["metadata"]["tool_name"] == "web_search"


# ════════════════════════════════════════════════════════
# TraceSession Tests
# ════════════════════════════════════════════════════════
class TestTraceSession:
    def test_create_session(self):
        s = TraceSession(
            session_id="s1",
            name="test",
            project="demo",
        )
        assert s.total_tokens == 0
        assert s.total_cost == 0.0
        assert s.duration is not None

    def test_record_tokens(self):
        s = TraceSession(session_id="s1", name="test")
        s.record_tokens(prompt_tokens=10, completion_tokens=20, cost=0.01)
        assert s.total_prompt_tokens == 10
        assert s.total_completion_tokens == 20
        assert s.total_tokens == 30
        assert s.total_cost == 0.01

    def test_add_model_dedup(self):
        s = TraceSession(session_id="s1", name="test")
        s.add_model("gpt-4o")
        s.add_model("gpt-4o")
        s.add_model("claude-3")
        assert len(s.models_used) == 2

    def test_add_tool_dedup(self):
        s = TraceSession(session_id="s1", name="test")
        s.add_tool("search")
        s.add_tool("search")
        assert len(s.tools_used) == 1

    def test_record_step(self):
        session = TraceSession(session_id="s1", name="test")
        span = TraceSpan(
            event_id="e1",
            trace_id="t1",
            parent_id=None,
            event_type="llm",
            name="step1",
        )
        span.end()
        session.record_step(span)
        assert len(session.steps) == 1
        assert session.steps[0]["name"] == "step1"

    def test_record_step_with_error(self):
        session = TraceSession(session_id="s1", name="test")
        span = TraceSpan(
            event_id="e1",
            trace_id="t1",
            parent_id=None,
            event_type="llm",
            name="fail_step",
        )
        span.end(error="boom")
        session.record_step(span)
        assert len(session.errors) == 1
        assert "boom" in session.errors[0]

    def test_summary(self):
        s = TraceSession(
            session_id="s1",
            name="test",
            project="demo",
            framework="openai",
        )
        s.total_llm_calls = 3
        s.total_tokens = 500
        s.total_cost = 0.05
        s.end_time = s.start_time + 1.5
        summary = s.summary()
        assert summary["llm_calls"] == 3
        assert summary["total_tokens"] == 500
        assert summary["framework"] == "openai"
        assert summary["duration_seconds"] == 1.5


# ════════════════════════════════════════════════════════
# Cost Estimation Tests
# ════════════════════════════════════════════════════════
class TestCostEstimation:
    def test_known_model(self):
        cost = estimate_cost("gpt-4o-mini", 1000, 500)
        assert cost > 0

    def test_unknown_model(self):
        cost = estimate_cost("my-custom-model", 1000, 500)
        assert cost == 0.0

    def test_none_model(self):
        cost = estimate_cost(None, 1000, 500)
        assert cost == 0.0

    def test_model_name_normalization(self):
        cost1 = estimate_cost("openai/gpt-4o-mini", 1000, 500)
        cost2 = estimate_cost("gpt-4o-mini", 1000, 500)
        assert cost1 == cost2

    def test_anthropic_cost(self):
        cost = estimate_cost("claude-3-5-sonnet", 1000, 500)
        assert cost > 0

    def test_gemini_cost(self):
        cost = estimate_cost("gemini-2.0-flash", 1000, 500)
        assert cost > 0


# ════════════════════════════════════════════════════════
# Safe Serialization Tests
# ════════════════════════════════════════════════════════
class TestSafeSerde:
    def test_string(self):
        assert safe_serialize("hello") == "hello"

    def test_dict(self):
        result = safe_serialize({"key": "value"})
        assert "key" in result

    def test_list(self):
        result = safe_serialize([1, 2, 3])
        assert "[1, 2, 3]" == result

    def test_truncation(self):
        result = safe_serialize("x" * 100, max_len=10)
        assert len(result) == 10

    def test_non_serializable(self):
        result = safe_serialize(object())
        assert len(result) > 0


# ════════════════════════════════════════════════════════
# BaseTracer Tests
# ════════════════════════════════════════════════════════
class TestBaseTracer:
    def test_create_tracer(self):
        t = BaseTracer(
            name="test",
            project="demo",
            auto_log=False,
        )
        assert t.session.name == "test"
        assert t.session.project == "demo"

    def test_start_and_end_span(self):
        t = BaseTracer(name="test", auto_log=False)
        span = t.start_span("llm", "call1")
        assert span.status == "running"

        t.end_span(span, outputs={"result": "ok"})
        assert span.status == "success"
        assert len(t.session.steps) == 1

    def test_span_by_run_id(self):
        t = BaseTracer(name="test", auto_log=False)
        t.start_span("llm", "call1", run_id="run-1")
        result = t.end_span("run-1", outputs={"x": 1})
        assert result is not None
        assert result.name == "call1"

    def test_parent_child_spans(self):
        t = BaseTracer(name="test", auto_log=False)
        parent = t.start_span("chain", "parent", run_id="p1")
        child = t.start_span(
            "llm",
            "child",
            run_id="c1",
            parent_run_id="p1",
        )
        assert child.parent_id == parent.event_id
        t.end_span("c1")
        t.end_span("p1")

    def test_auto_parent_from_stack(self):
        t = BaseTracer(name="test", auto_log=False)
        parent = t.start_span("chain", "parent")
        child = t.start_span("llm", "child")
        assert child.parent_id == parent.event_id
        t.end_span(child)
        t.end_span(parent)

    def test_finalize(self):
        t = BaseTracer(name="test", auto_log=False)
        t.start_span("llm", "call1", run_id="r1")
        t.end_span("r1")
        t.finalize()
        assert t.session.end_time is not None

    def test_error_tracking(self):
        t = BaseTracer(name="test", auto_log=False)
        s = t.start_span("llm", "fail")
        t.end_span(s, error="something broke")
        assert len(t.session.errors) == 1
        assert "something broke" in t.session.errors[0]


# ════════════════════════════════════════════════════════
# trace() Context Manager Tests
# ════════════════════════════════════════════════════════
class TestTraceContextManager:
    def test_basic_trace(self):
        with trace(
            "test_trace",
            auto_log=False,
            print_summary=False,
        ) as tracer:
            span = tracer.start_span("llm", "hello")
            span.set_tokens(prompt_tokens=10, completion_tokens=5)
            tracer.end_span(span, outputs={"msg": "hi"})

        assert tracer.session.end_time is not None
        assert len(tracer.session.steps) == 1

    def test_trace_with_error(self):
        with pytest.raises(ValueError):
            with trace(
                "error_trace",
                auto_log=False,
                print_summary=False,
            ) as tracer:
                raise ValueError("test error")

        assert "test error" in tracer.session.errors

    def test_trace_with_project(self):
        with trace(
            "proj_trace",
            project="myproj",
            auto_log=False,
            print_summary=False,
        ) as tracer:
            pass
        assert tracer.session.project == "myproj"


# ════════════════════════════════════════════════════════
# observe() Decorator Tests
# ════════════════════════════════════════════════════════
class TestObserveDecorator:
    def test_basic_observe(self):
        @observe(name="test_fn", auto_log=False, print_summary=False)
        def my_func(x, flowyml_session=None):
            assert flowyml_session is not None
            return x * 2

        result = my_func(5)
        assert result == 10

    def test_observe_without_session_param(self):
        @observe(name="simple", auto_log=False, print_summary=False)
        def simple_fn(x):
            return x + 1

        result = simple_fn(5)
        assert result == 6

    def test_observe_uses_function_name(self):
        @observe(auto_log=False, print_summary=False)
        def my_custom_name(flowyml_session=None):
            return flowyml_session.session.name

        result = my_custom_name()
        assert result == "my_custom_name"


# ════════════════════════════════════════════════════════
# Manual Logging Tests
# ════════════════════════════════════════════════════════
class TestManualLogging:
    def test_log_llm_call(self):
        span = log_llm_call(
            model="gpt-4o-mini",
            prompt="Hello",
            response="Hi there!",
            prompt_tokens=5,
            completion_tokens=10,
        )
        assert span.model == "gpt-4o-mini"
        assert span.prompt_tokens == 5
        assert span.total_tokens == 15
        assert span.cost > 0

    def test_log_tool_call(self):
        span = log_tool_call(
            name="calculator",
            tool_input="2 + 2",
            tool_output="4",
        )
        assert span.tool_name == "calculator"
        assert span.status == "success"

    def test_log_embedding_call(self):
        span = log_embedding_call(
            model="text-embedding-3-small",
            input_text="Hello world",
            token_count=2,
        )
        assert span.event_type == "embedding"
        assert span.model == "text-embedding-3-small"

    def test_log_llm_within_trace(self):
        with trace(
            "test",
            auto_log=False,
            print_summary=False,
        ) as tracer:
            span = log_llm_call(
                model="gpt-4o",
                prompt="Test",
                response="Response",
                prompt_tokens=10,
                completion_tokens=20,
                tracer=tracer,
            )
        assert span.total_tokens == 30
        assert tracer.session.total_llm_calls == 1


# ════════════════════════════════════════════════════════
# span() Context Manager Tests (generic.py)
# ════════════════════════════════════════════════════════
class TestSpanContextManager:
    def test_basic_span(self):
        with span("test_step", "custom") as s:
            s.outputs = {"result": "done"}
        assert s.status == "success"
        assert s.duration is not None

    def test_span_with_error(self):
        with pytest.raises(RuntimeError):
            with span("fail_step") as s:
                raise RuntimeError("oops")
        assert s.status == "error"
        assert s.error == "oops"

    def test_span_with_tracer(self):
        tracer = BaseTracer(name="test", auto_log=False)
        with span("nested", "llm", tracer=tracer) as s:
            s.set_tokens(prompt_tokens=10, model="gpt-4o")
        assert len(tracer.session.steps) == 1


# ════════════════════════════════════════════════════════
# LangGraph Callback Handler Tests
# ════════════════════════════════════════════════════════
class TestCallbackHandler:
    def test_create_handler(self):
        from flowyml.integrations.langgraph import FlowyMLCallbackHandler

        handler = FlowyMLCallbackHandler(
            session_name="test",
            project="demo",
            auto_log=False,
        )
        assert handler.session.name == "test"
        assert handler.session.project == "demo"

    def test_llm_lifecycle(self):
        from flowyml.integrations.langgraph import FlowyMLCallbackHandler

        handler = FlowyMLCallbackHandler(
            session_name="test",
            auto_log=False,
        )

        # Start
        handler.on_chat_model_start(
            serialized={
                "name": "ChatOpenAI",
                "kwargs": {"model": "gpt-4o-mini"},
            },
            messages=[
                [
                    type(
                        "Msg",
                        (),
                        {
                            "type": "human",
                            "content": "Hello!",
                        },
                    )(),
                ],
            ],
            run_id="run-1",
        )
        assert handler.session.total_llm_calls == 1

        # End
        class FakeGen:
            text = "Hi there!"
            generation_info = {}

        class FakeResponse:
            llm_output = {
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
                "model_name": "gpt-4o-mini",
            }
            generations = [[FakeGen()]]

        handler.on_llm_end(FakeResponse(), run_id="run-1")
        assert handler.session.total_tokens == 30
        assert handler.session.total_cost > 0
        assert len(handler.session.steps) == 1

    def test_tool_lifecycle(self):
        from flowyml.integrations.langgraph import FlowyMLCallbackHandler

        handler = FlowyMLCallbackHandler(
            session_name="test",
            auto_log=False,
        )

        handler.on_tool_start(
            serialized={"name": "web_search"},
            input_str="latest AI news",
            run_id="tool-1",
        )
        assert handler.session.total_tool_calls == 1
        assert "web_search" in handler.session.tools_used

        handler.on_tool_end("Found 10 results", run_id="tool-1")
        assert len(handler.session.steps) == 1

    def test_chain_lifecycle(self):
        from flowyml.integrations.langgraph import FlowyMLCallbackHandler

        handler = FlowyMLCallbackHandler(
            session_name="test",
            auto_log=False,
        )

        handler.on_chain_start(
            serialized={"name": "QAChain"},
            inputs={"question": "What?"},
            run_id="chain-1",
        )
        assert handler.session.total_chain_calls == 1

        handler.on_chain_end(
            {"answer": "42"},
            run_id="chain-1",
        )
        assert len(handler.session.steps) == 1

    def test_error_handling(self):
        from flowyml.integrations.langgraph import FlowyMLCallbackHandler

        handler = FlowyMLCallbackHandler(
            session_name="test",
            auto_log=False,
        )

        handler.on_llm_start(
            serialized={"name": "LLM"},
            prompts=["test"],
            run_id="err-1",
        )
        handler.on_llm_error(
            ValueError("API error"),
            run_id="err-1",
        )
        assert len(handler.session.errors) == 1
        assert handler.session.steps[0]["status"] == "error"


# ════════════════════════════════════════════════════════
# LangGraph trace_graph() Tests
# ════════════════════════════════════════════════════════
class TestTraceGraph:
    def test_trace_graph_yields_config(self):
        from flowyml.integrations.langgraph import trace_graph

        with trace_graph(
            "test_agent",
            auto_log=False,
            print_summary=False,
        ) as session:
            config = session.config
            assert "callbacks" in config
            assert len(config["callbacks"]) == 1

    def test_trace_graph_session_access(self):
        from flowyml.integrations.langgraph import trace_graph

        with trace_graph(
            "test_agent",
            project="demo",
            auto_log=False,
            print_summary=False,
        ) as session:
            assert session.name == "test_agent"
            assert session.project == "demo"


# ════════════════════════════════════════════════════════
# LangChain Integration Tests
# ════════════════════════════════════════════════════════
class TestLangChainIntegration:
    def test_trace_chain(self):
        from flowyml.integrations.langchain import trace_chain

        with trace_chain(
            "test_chain",
            auto_log=False,
            print_summary=False,
        ) as session:
            config = session.config
            assert "callbacks" in config

    def test_observe_chain(self):
        from flowyml.integrations.langchain import observe_chain

        @observe_chain(
            name="test_fn",
            auto_log=False,
            print_summary=False,
        )
        def my_func(x, flowyml_session=None):
            assert flowyml_session is not None
            return x * 2

        assert my_func(5) == 10


# ════════════════════════════════════════════════════════
# Session Summary Output Tests
# ════════════════════════════════════════════════════════
class TestSummaryOutput:
    def test_print_summary(self, capsys):
        session = TraceSession(
            session_id="s1",
            name="test_agent",
            project="demo",
            framework="langgraph",
        )
        session.total_llm_calls = 3
        session.total_tool_calls = 2
        session.total_tokens = 500
        session.total_cost = 0.05
        session.models_used = ["gpt-4o"]
        session.tools_used = ["search"]
        session.end_time = session.start_time + 1.5
        session.print_summary()

        captured = capsys.readouterr()
        assert "FlowyML Trace" in captured.out
        assert "test_agent" in captured.out
        assert "demo" in captured.out
        assert "500" in captured.out
        assert "gpt-4o" in captured.out


# ═════════════════════════════════════════════════════════════
# Session-Based Observability Tests
# ═════════════════════════════════════════════════════════════


class TestTurn:
    """Tests for the Turn dataclass."""

    def test_turn_creation(self):
        from flowyml.integrations.base import Turn

        turn = Turn(
            turn_id="t1",
            session_id="s1",
            turn_index=1,
            role="user",
            content="Hello",
        )
        assert turn.turn_id == "t1"
        assert turn.session_id == "s1"
        assert turn.turn_index == 1
        assert turn.role == "user"
        assert turn.content == "Hello"
        assert turn.status == "running"

    def test_turn_end_aggregates_spans(self):
        from flowyml.integrations.base import TraceSpan, Turn

        turn = Turn(
            turn_id="t1",
            session_id="s1",
            turn_index=1,
        )
        span1 = TraceSpan(
            span_id="sp1",
            trace_id="s1",
            event_type="llm",
            name="call1",
        )
        span1.prompt_tokens = 10
        span1.completion_tokens = 20
        span1.total_tokens = 30
        span1.cost = 0.001
        span1.model = "gpt-4o-mini"

        span2 = TraceSpan(
            span_id="sp2",
            trace_id="s1",
            event_type="tool",
            name="search",
        )
        span2.tool_name = "search"
        span2.tool_input = {"q": "test"}
        span2.tool_output = {"r": "result"}

        turn.spans = [span1, span2]
        turn.end(content="response")

        assert turn.status == "success"
        assert turn.content == "response"
        assert turn.input_tokens == 10
        assert turn.output_tokens == 20
        assert turn.total_tokens == 30
        assert turn.cost == 0.001
        assert turn.model == "gpt-4o-mini"
        assert len(turn.tool_calls) == 1
        assert turn.tool_calls[0]["name"] == "search"

    def test_turn_end_error(self):
        from flowyml.integrations.base import Turn

        turn = Turn(turn_id="t1", session_id="s1", turn_index=1)
        turn.end(error="something broke")
        assert turn.status == "error"
        assert turn.error == "something broke"

    def test_turn_add_eval(self):
        from flowyml.integrations.base import Turn

        turn = Turn(turn_id="t1", session_id="s1", turn_index=1)
        result = turn.add_eval(
            "relevance",
            0.85,
            passed=True,
            rationale="Good response",
        )
        assert result["scorer"] == "relevance"
        assert result["score"] == 0.85
        assert result["passed"] is True
        assert len(turn.eval_results) == 1

    def test_turn_to_dict(self):
        from flowyml.integrations.base import Turn

        turn = Turn(
            turn_id="t1",
            session_id="s1",
            turn_index=1,
            role="assistant",
            content="Hi there",
        )
        d = turn.to_dict()
        assert d["turn_id"] == "t1"
        assert d["role"] == "assistant"
        assert d["content"] == "Hi there"
        assert "timestamp" in d


class TestGenAISession:
    """Tests for the GenAISession dataclass."""

    def test_session_creation(self):
        from flowyml.integrations.base import GenAISession

        session = GenAISession(
            session_id="s1",
            name="test_bot",
            project="demo",
            thread_id="thread-1",
        )
        assert session.session_id == "s1"
        assert session.name == "test_bot"
        assert session.status == "active"
        assert session.total_turns == 0

    def test_record_turn_updates_aggregates(self):
        from flowyml.integrations.base import GenAISession, Turn

        session = GenAISession(session_id="s1", name="test")

        turn = Turn(turn_id="t1", session_id="s1", turn_index=1)
        turn.input_tokens = 10
        turn.output_tokens = 20
        turn.total_tokens = 30
        turn.cost = 0.001
        turn.latency = 0.5
        turn.model = "gpt-4o-mini"
        turn.tool_calls = [{"name": "search"}]
        turn.status = "success"

        session.record_turn(turn)

        assert session.total_turns == 1
        assert session.total_input_tokens == 10
        assert session.total_output_tokens == 20
        assert session.total_tokens == 30
        assert session.total_cost == 0.001
        assert session.total_latency == 0.5
        assert "gpt-4o-mini" in session.models_used
        assert "search" in session.tools_used

    def test_multi_turn_aggregation(self):
        from flowyml.integrations.base import GenAISession, Turn

        session = GenAISession(session_id="s1", name="test")

        for i in range(3):
            turn = Turn(turn_id=f"t{i}", session_id="s1", turn_index=i + 1)
            turn.total_tokens = 100
            turn.cost = 0.01
            turn.latency = 0.3
            turn.status = "success"
            session.record_turn(turn)

        assert session.total_turns == 3
        assert session.total_tokens == 300
        assert session.total_cost == pytest.approx(0.03)

    def test_session_add_eval(self):
        from flowyml.integrations.base import GenAISession, Turn

        session = GenAISession(session_id="s1", name="test")
        turn = Turn(turn_id="t1", session_id="s1", turn_index=1)
        turn.status = "success"
        session.record_turn(turn)

        result = session.add_eval("relevance", 0.9, passed=True)
        assert result["scorer"] == "relevance"
        assert "relevance" in session.eval_scores
        assert session.eval_scores["relevance"] == [0.9]

    def test_session_summary(self):
        from flowyml.integrations.base import GenAISession, Turn

        session = GenAISession(
            session_id="s1",
            name="test_bot",
            project="demo",
            framework="custom",
        )
        turn = Turn(turn_id="t1", session_id="s1", turn_index=1)
        turn.total_tokens = 100
        turn.cost = 0.01
        turn.latency = 0.5
        turn.model = "gpt-4o-mini"
        turn.status = "success"
        session.record_turn(turn)

        summary = session.summary()
        assert summary["name"] == "test_bot"
        assert summary["project"] == "demo"
        assert summary["total_turns"] == 1
        assert summary["total_tokens"] == 100

    def test_session_experiment_metrics(self):
        from flowyml.integrations.base import GenAISession, Turn

        session = GenAISession(session_id="s1", name="test")
        for i in range(2):
            turn = Turn(turn_id=f"t{i}", session_id="s1", turn_index=i + 1)
            turn.total_tokens = 50
            turn.cost = 0.005
            turn.latency = 0.2
            turn.status = "success"
            session.record_turn(turn)

        session.add_eval("relevance", 0.8)
        session.add_eval("relevance", 0.9)

        metrics = session.to_experiment_metrics()
        assert metrics["total_turns"] == 2
        assert metrics["total_tokens"] == 100
        assert "eval_relevance_mean" in metrics
        assert metrics["eval_relevance_mean"] == pytest.approx(0.85)

    def test_session_print_summary(self, capsys):
        from flowyml.integrations.base import GenAISession, Turn

        session = GenAISession(
            session_id="s1",
            name="test_bot",
            project="demo",
            thread_id="thread-1",
        )
        turn = Turn(turn_id="t1", session_id="s1", turn_index=1)
        turn.total_tokens = 100
        turn.cost = 0.01
        turn.latency = 0.5
        turn.model = "gpt-4o-mini"
        turn.status = "success"
        session.record_turn(turn)
        session.end_time = session.start_time + 1.0
        session.status = "completed"
        session.print_summary()

        captured = capsys.readouterr()
        assert "GenAI Session" in captured.out
        assert "test_bot" in captured.out
        assert "demo" in captured.out

    def test_session_event_callbacks(self):
        from flowyml.integrations.base import GenAISession, Turn

        events = []
        session = GenAISession(session_id="s1", name="test")
        session.on_event(lambda etype, data: events.append((etype, data)))

        turn = Turn(turn_id="t1", session_id="s1", turn_index=1)
        turn.status = "success"
        session.record_turn(turn)

        assert len(events) == 1
        assert events[0][0] == "turn_end"


class TestSessionTracer:
    """Tests for the SessionTracer class."""

    def test_basic_session_tracer(self):
        from flowyml.integrations.base import SessionTracer

        tracer = SessionTracer(
            "test_bot",
            project="demo",
            auto_log=False,
        )
        assert tracer.genai_session.name == "test_bot"
        assert tracer.genai_session.project == "demo"
        assert tracer.genai_session.status == "active"

    def test_turn_context_manager(self):
        from flowyml.integrations.base import SessionTracer

        tracer = SessionTracer("test_bot", auto_log=False)

        with tracer.turn("user") as t:
            t.content = "Hello"
            span = tracer.start_span("llm", "reply")
            span.set_tokens(prompt_tokens=10, completion_tokens=20, model="gpt-4o-mini")
            tracer.end_span(span, outputs={"content": "Hi!"})
            t.content = "Hi!"

        assert tracer.genai_session.total_turns == 1
        assert tracer.genai_session.total_tokens == 30
        assert len(tracer.genai_session.turns) == 1
        assert tracer.genai_session.turns[0].content == "Hi!"

    def test_multi_turn_session(self):
        from flowyml.integrations.base import SessionTracer

        tracer = SessionTracer("test_bot", auto_log=False)

        for i in range(3):
            with tracer.turn("user") as t:
                t.content = f"Question {i}"
                span = tracer.start_span("llm", f"reply_{i}")
                span.set_tokens(prompt_tokens=10, completion_tokens=20, model="gpt-4o-mini")
                tracer.end_span(span)
                t.content = f"Answer {i}"

        assert tracer.genai_session.total_turns == 3
        assert len(tracer.genai_session.turns) == 3

    def test_turn_error_handling(self):
        from flowyml.integrations.base import SessionTracer

        tracer = SessionTracer("test_bot", auto_log=False)

        with pytest.raises(ValueError):
            with tracer.turn("user") as t:
                raise ValueError("test error")

        assert tracer.genai_session.total_turns == 1
        assert tracer.genai_session.turns[0].status == "error"
        assert "test error" in tracer.genai_session.turns[0].error

    def test_end_session(self):
        from flowyml.integrations.base import SessionTracer

        tracer = SessionTracer("test_bot", auto_log=False)

        with tracer.turn("user") as t:
            t.content = "Hello"

        session = tracer.end_session()
        assert session.status == "completed"
        assert session.end_time is not None

    def test_span_attached_to_turn(self):
        from flowyml.integrations.base import SessionTracer

        tracer = SessionTracer("test_bot", auto_log=False)

        with tracer.turn("user") as t:
            span1 = tracer.start_span("llm", "call1")
            tracer.end_span(span1)
            span2 = tracer.start_span("tool", "search")
            tracer.end_span(span2)

        turn = tracer.genai_session.turns[0]
        assert len(turn.spans) == 2


class TestSessionEvaluator:
    """Tests for the SessionEvaluator class."""

    def test_evaluator_creation(self):
        from flowyml.integrations.eval_bridge import SessionEvaluator

        evaluator = SessionEvaluator([], async_mode=False)
        assert evaluator.scorers == []

    def test_sync_evaluation(self):
        from flowyml.integrations.base import Turn
        from flowyml.integrations.eval_bridge import SessionEvaluator
        from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType

        class MockScorer(Scorer):
            name = "mock"
            scorer_type = ScorerType.GENAI

            def score(self, **kw):
                return ScorerFeedback(
                    name=self.name,
                    value=0.85,
                    scorer_type="genai",
                    passed=True,
                    rationale="Good",
                )

        evaluator = SessionEvaluator(
            [MockScorer()],
            async_mode=False,
        )

        turn = Turn(
            turn_id="t1",
            session_id="s1",
            turn_index=1,
            role="assistant",
            content="Hello!",
        )
        results = evaluator.evaluate_turn(turn)

        assert len(results) == 1
        assert results[0]["scorer"] == "mock"
        assert results[0]["score"] == 0.85
        assert len(turn.eval_results) == 1

    def test_async_evaluation(self):
        import time
        from flowyml.integrations.base import Turn
        from flowyml.integrations.eval_bridge import SessionEvaluator
        from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType

        class SlowScorer(Scorer):
            name = "slow"
            scorer_type = ScorerType.GENAI

            def score(self, **kw):
                time.sleep(0.05)
                return ScorerFeedback(
                    name=self.name,
                    value=0.9,
                    scorer_type="genai",
                )

        evaluator = SessionEvaluator(
            [SlowScorer()],
            async_mode=True,
        )
        turn = Turn(
            turn_id="t1",
            session_id="s1",
            turn_index=1,
            content="Test",
        )
        results = evaluator.evaluate_turn(turn)
        assert results == []  # Async returns empty immediately

        evaluator.wait_for_pending(timeout=5)
        assert len(turn.eval_results) == 1
        evaluator.shutdown()

    def test_scorer_error_handling(self):
        from flowyml.integrations.base import Turn
        from flowyml.integrations.eval_bridge import SessionEvaluator
        from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType

        class BrokenScorer(Scorer):
            name = "broken"
            scorer_type = ScorerType.GENAI

            def score(self, **kw):
                raise RuntimeError("scorer crashed")

        evaluator = SessionEvaluator(
            [BrokenScorer()],
            async_mode=False,
        )
        turn = Turn(
            turn_id="t1",
            session_id="s1",
            turn_index=1,
            content="Test",
        )
        results = evaluator.evaluate_turn(turn)

        assert len(results) == 1
        assert results[0]["score"] == 0.0
        assert "Error" in results[0]["rationale"]


class TestSessionEventStream:
    """Tests for the SessionEventStream class."""

    def test_basic_event_stream(self):
        from flowyml.integrations.streaming import SessionEventStream

        events = []
        stream = SessionEventStream(
            callback=lambda etype, data: events.append((etype, data)),
        )
        stream("turn_end", {"turn_id": "t1", "role": "user"})

        assert len(events) == 1
        assert events[0][0] == "turn_end"

    def test_event_buffer(self):
        from flowyml.integrations.streaming import SessionEventStream

        stream = SessionEventStream(buffer_size=5)
        for i in range(10):
            stream("event", {"index": i})

        assert stream.event_count == 5
        assert stream.events[0]["data"]["index"] == 9  # Most recent

    def test_multiple_callbacks(self):
        from flowyml.integrations.streaming import SessionEventStream

        results = {"cb1": [], "cb2": []}
        stream = SessionEventStream(
            callback=lambda e, d: results["cb1"].append(e),
        )
        stream.on(lambda e, d: results["cb2"].append(e))
        stream("test", {})

        assert len(results["cb1"]) == 1
        assert len(results["cb2"]) == 1

    def test_clear_buffer(self):
        from flowyml.integrations.streaming import SessionEventStream

        stream = SessionEventStream()
        stream("test", {})
        assert stream.event_count == 1
        stream.clear()
        assert stream.event_count == 0


class TestSessionTrace:
    """Tests for the session_trace() context manager."""

    def test_session_trace_basic(self, capsys):
        from flowyml.integrations.base import session_trace

        with session_trace(
            "test_session",
            project="demo",
            auto_log=False,
            print_summary=True,
        ) as tracer:
            with tracer.turn("user") as t:
                t.content = "Hello"
                span = tracer.start_span("llm", "reply")
                span.set_tokens(prompt_tokens=5, completion_tokens=10, model="gpt-4o-mini")
                tracer.end_span(span)
                t.content = "Hi!"

        captured = capsys.readouterr()
        assert "GenAI Session" in captured.out
        assert "test_session" in captured.out

    def test_session_trace_no_summary(self, capsys):
        from flowyml.integrations.base import session_trace

        with session_trace(
            "quiet",
            auto_log=False,
            print_summary=False,
        ) as tracer:
            pass

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_session_trace_error_propagation(self):
        from flowyml.integrations.base import session_trace

        with pytest.raises(RuntimeError, match="boom"):
            with session_trace(
                "error_session",
                auto_log=False,
                print_summary=False,
            ) as tracer:
                raise RuntimeError("boom")

        assert len(tracer.genai_session.errors) == 1

    def test_session_with_evaluator(self):
        from flowyml.integrations.base import session_trace
        from flowyml.integrations.eval_bridge import SessionEvaluator
        from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType

        class SimpleScorer(Scorer):
            name = "test_scorer"
            scorer_type = ScorerType.GENAI

            def score(self, **kw):
                return ScorerFeedback(
                    name=self.name,
                    value=0.9,
                    scorer_type="genai",
                )

        evaluator = SessionEvaluator(
            [SimpleScorer()],
            async_mode=False,
        )

        with session_trace(
            "eval_session",
            evaluator=evaluator,
            auto_log=False,
            print_summary=False,
        ) as tracer:
            with tracer.turn("user") as t:
                t.content = "test"

        session = tracer.genai_session
        assert "test_scorer" in session.eval_scores
        assert len(session.eval_scores["test_scorer"]) == 1
