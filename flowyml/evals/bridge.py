"""FlowyML Evaluations — Trace-to-Evaluation Bridge.

Connects the LLMTracer monitoring system to the evaluation framework,
enabling retroactive evaluation of traced LLM interactions.
"""

import logging
from typing import Any

from flowyml.evals.base import Scorer
from flowyml.evals.core import EvalResult, evaluate
from flowyml.evals.dataset import EvalDataset

logger = logging.getLogger(__name__)


class TraceBridge:
    """Bridge between LLM traces and the evaluation framework.

    Converts traced LLM interactions (from flowyml.monitoring.llm.LLMTracer)
    into evaluation datasets and runs scorers against them — no manual data
    preparation needed.

    This enables retroactive evaluation: trace your LLM calls in production,
    then evaluate them later with any scorer.

    Example:
        >>> from flowyml.monitoring.llm import LLMTracer
        >>> from flowyml.evals import TraceBridge, Relevance, Toxicity
        >>>
        >>> tracer = LLMTracer()
        >>> # ... traces accumulate during production usage ...
        >>>
        >>> bridge = TraceBridge()
        >>> result = bridge.evaluate_traces(
        ...     tracer=tracer,
        ...     scorers=[Relevance(), Toxicity()],
        ...     experiment="prod_quality_check",
        ... )
        >>> print(result.summary)
    """

    def evaluate_traces(
        self,
        tracer: Any = None,
        trace_events: list[dict] | None = None,
        scorers: list[Scorer] | None = None,
        experiment: str | None = None,
        limit: int | None = None,
        filters: dict | None = None,
        **kwargs: Any,
    ) -> EvalResult:
        """Evaluate traced LLM interactions.

        Args:
            tracer: LLMTracer instance (reads events from it)
            trace_events: Alternative: list of trace event dicts directly
            scorers: List of scorers to run
            experiment: Experiment name for tracking
            limit: Maximum number of traces to evaluate
            filters: Optional filters for trace selection
            **kwargs: Additional arguments for evaluate()

        Returns:
            EvalResult with scores for all traced interactions
        """
        if scorers is None:
            scorers = []

        # Gather trace events
        events = self._gather_events(tracer, trace_events, limit, filters)

        if not events:
            logger.warning("No trace events found to evaluate")
            return EvalResult(experiment=experiment, metadata={"source": "trace_bridge"})

        # Convert traces to EvalDataset
        examples = self._traces_to_examples(events)
        eval_ds = EvalDataset.create_genai(
            name=f"traces_{experiment or 'default'}",
            examples=examples,
            tags={"source": "trace_bridge", "n_traces": str(len(events))},
        )

        # Run evaluation
        result = evaluate(
            data=eval_ds,
            scorers=scorers,
            experiment=experiment,
            **kwargs,
        )
        result.metadata["source"] = "trace_bridge"
        result.metadata["n_traces"] = len(events)

        return result

    def evaluate_from_store(
        self,
        trace_ids: list[str] | None = None,
        scorers: list[Scorer] | None = None,
        experiment: str | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> EvalResult:
        """Evaluate traces loaded from the metadata store.

        Args:
            trace_ids: Optional specific trace IDs to evaluate
            scorers: List of scorers
            experiment: Experiment name
            limit: Maximum traces to load
            **kwargs: Additional arguments

        Returns:
            EvalResult
        """
        if scorers is None:
            scorers = []

        events = []
        try:
            from flowyml.storage.metadata import SQLMetadataStore

            store = SQLMetadataStore()

            if trace_ids:
                for trace_id in trace_ids:
                    trace = store.get_trace(trace_id)
                    if trace:
                        events.extend(trace.get("events", []))
            else:
                # Load recent traces
                traces = store.list_traces(limit=limit) if hasattr(store, "list_traces") else []
                for trace in traces:
                    events.append(trace)

        except Exception as e:
            logger.warning("Could not load traces from store: %s", e)

        return self.evaluate_traces(
            trace_events=events,
            scorers=scorers,
            experiment=experiment,
            **kwargs,
        )

    def _gather_events(
        self,
        tracer: Any,
        trace_events: list[dict] | None,
        limit: int | None,
        filters: dict | None,
    ) -> list[dict]:
        """Gather trace events from various sources."""
        events = []

        if trace_events:
            events = list(trace_events)
        elif tracer is not None:
            # Extract events from LLMTracer
            if hasattr(tracer, "events"):
                for event in tracer.events:
                    if hasattr(event, "to_dict"):
                        events.append(event.to_dict())
                    elif hasattr(event, "__dict__"):
                        events.append(vars(event))
                    elif isinstance(event, dict):
                        events.append(event)
            elif hasattr(tracer, "get_events"):
                events = tracer.get_events()

        # Apply filters
        if filters:
            events = self._apply_filters(events, filters)

        # Apply limit
        if limit and len(events) > limit:
            events = events[:limit]

        return events

    def _apply_filters(self, events: list[dict], filters: dict) -> list[dict]:
        """Apply filters to trace events."""
        filtered = []
        for event in events:
            matches = True
            for key, value in filters.items():
                event_val = event.get(key)
                if event_val != value:
                    matches = False
                    break
            if matches:
                filtered.append(event)
        return filtered

    def _traces_to_examples(self, events: list[dict]) -> list[dict[str, Any]]:
        """Convert trace events to scorer-compatible example dicts."""
        examples = []
        for event in events:
            example = {}

            # Map trace fields to scorer fields
            # LLMEvent typically has: name, event_type, input_data, output_data, metadata
            if "input_data" in event:
                example["inputs"] = event["input_data"]
            elif "input" in event:
                example["inputs"] = event["input"]
            elif "prompt" in event:
                example["inputs"] = event["prompt"]

            if "output_data" in event:
                example["outputs"] = event["output_data"]
            elif "output" in event:
                example["outputs"] = event["output"]
            elif "response" in event:
                example["outputs"] = event["response"]

            # Include context if available
            if "context" in event:
                example["context"] = event["context"]

            # Include metadata
            if "metadata" in event:
                example["trace_metadata"] = event["metadata"]

            if "inputs" in example and "outputs" in example:
                examples.append(example)

        return examples


# Convenience singleton
trace_bridge = TraceBridge()


def evaluate_traces(
    trace_ids: list[str] | None = None,
    tracer: Any = None,
    trace_events: list[dict] | None = None,
    scorers: list[Scorer] | None = None,
    experiment: str | None = None,
    limit: int | None = None,
    filters: dict | None = None,
    **kwargs: Any,
) -> EvalResult:
    """Evaluate LLM traces with scorers — convenience function.

    Top-level function that wraps TraceBridge for quick evaluation of
    traced LLM interactions without needing to create a bridge instance.

    Args:
        trace_ids: Optional specific trace IDs to evaluate from store
        tracer: LLMTracer instance to read events from
        trace_events: Direct list of trace event dicts
        scorers: List of scorers to run
        experiment: Experiment name for tracking
        limit: Maximum number of traces to evaluate
        filters: Optional filters for trace selection
        **kwargs: Additional arguments for evaluate()

    Returns:
        EvalResult with scores for all traced interactions

    Example:
        >>> from flowyml.evals import evaluate_traces, Relevance, Toxicity
        >>>
        >>> results = evaluate_traces(
        ...     trace_ids=["trace-001", "trace-002"],
        ...     scorers=[Relevance(), Toxicity()],
        ...     experiment="trace_quality_audit",
        ... )
    """
    bridge = TraceBridge()

    if trace_ids:
        return bridge.evaluate_from_store(
            trace_ids=trace_ids,
            scorers=scorers,
            experiment=experiment,
            limit=limit or 100,
            **kwargs,
        )
    else:
        return bridge.evaluate_traces(
            tracer=tracer,
            trace_events=trace_events,
            scorers=scorers,
            experiment=experiment,
            limit=limit,
            filters=filters,
            **kwargs,
        )
