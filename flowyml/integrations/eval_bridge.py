"""🔬 Eval Bridge — Automatic Session-Level Evaluations.

Connects the GenAI session layer to FlowyML's evaluation system.
Evaluators run scorers on each turn automatically, either synchronously
or asynchronously in background threads.

Usage::

    from flowyml.integrations.eval_bridge import SessionEvaluator
    from flowyml.evals import Relevance, Toxicity

    evaluator = SessionEvaluator([
        Relevance(model="gpt-4o-mini", threshold=0.7),
        Toxicity(model="gpt-4o-mini", threshold=0.1),
    ])

    with session_trace("chatbot", evaluator=evaluator) as tracer:
        with tracer.turn("user") as t:
            t.content = response
            # Evals run automatically after each turn ↑
"""

from __future__ import annotations

import contextlib
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["SessionEvaluator"]


class SessionEvaluator:
    """Auto-evaluates turns within a GenAI session.

    Attach to a :class:`GenAISession` or pass to ``session_trace()`` to
    automatically score each turn against a list of scorers.

    Args:
        scorers: List of :class:`Scorer` instances from ``flowyml.evals``.
        async_mode: If True, evals run in a thread pool to avoid blocking.
        max_workers: Number of threads for async evaluation.
        on_eval_complete: Optional callback ``(turn, feedback) -> None``.
    """

    def __init__(
        self,
        scorers: list[Any] | None = None,
        *,
        async_mode: bool = True,
        max_workers: int = 4,
        on_eval_complete: Any | None = None,
    ):
        self.scorers = scorers or []
        self.async_mode = async_mode
        self._executor = ThreadPoolExecutor(max_workers=max_workers) if async_mode else None
        self._on_eval_complete = on_eval_complete
        self._futures: list[Any] = []

    def evaluate_turn(self, turn: Any) -> list[dict[str, Any]]:
        """Evaluate a single turn against all configured scorers.

        Called automatically by :meth:`GenAISession.record_turn` when
        this evaluator is attached.

        Returns:
            List of eval result dicts added to the turn.
        """
        if not self.scorers:
            return []

        if self.async_mode and self._executor:
            future = self._executor.submit(
                self._run_evals,
                turn,
            )
            self._futures.append(future)
            return []  # Results will be attached async
        else:
            return self._run_evals(turn)

    def _run_evals(self, turn: Any) -> list[dict[str, Any]]:
        """Run all scorers against a turn (sync, possibly in a thread)."""
        results = []
        for scorer in self.scorers:
            try:
                feedback = scorer.score(
                    inputs=turn.content if turn.role == "user" else "",
                    outputs=turn.content if turn.role != "user" else "",
                )
                result = turn.add_eval(
                    scorer_name=feedback.name,
                    score=float(feedback.value)
                    if isinstance(
                        feedback.value,
                        (int, float),
                    )
                    else 0.0,
                    passed=feedback.passed,
                    rationale=feedback.rationale,
                    metadata=feedback.metadata,
                )
                results.append(result)

                if self._on_eval_complete:
                    with contextlib.suppress(Exception):
                        self._on_eval_complete(turn, feedback)

            except Exception as e:
                logger.warning(
                    f"Scorer {getattr(scorer, 'name', '?')} failed: {e}",
                )
                result = turn.add_eval(
                    scorer_name=getattr(scorer, "name", "unknown"),
                    score=0.0,
                    passed=False,
                    rationale=f"Error: {e}",
                )
                results.append(result)

        return results

    def wait_for_pending(self, timeout: float | None = None) -> None:
        """Wait for all async evaluations to complete.

        Call this at the end of the session to ensure all background
        evals have finished before reading final scores.
        """
        for future in self._futures:
            try:
                future.result(timeout=timeout)
            except Exception as e:
                logger.warning(f"Async eval failed: {e}")
        self._futures.clear()

    def shutdown(self) -> None:
        """Shutdown the thread pool."""
        if self._executor:
            self.wait_for_pending(timeout=30)
            self._executor.shutdown(wait=False)

    def __del__(self):
        try:
            if self._executor:
                self._executor.shutdown(wait=False)
        except Exception:
            pass
