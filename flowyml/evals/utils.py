"""FlowyML Evaluations — Shared Utilities.

Common helpers for the evaluation framework: safe imports, score normalisation,
and rationale formatting.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def safe_import(module_name: str, *, package: str, install_hint: str | None = None):
    """Import a module with a clear error message on failure.

    Args:
        module_name: Fully qualified module to import (e.g. ``"deepeval.metrics"``)
        package: Human-readable package name for the error message
        install_hint: ``pip install`` command (auto-generated if *None*)

    Returns:
        The imported module

    Raises:
        ImportError: With actionable install instructions
    """
    import importlib

    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        hint = install_hint or f"pip install {package}"
        raise ImportError(
            f"FlowyML {package} adapter requires the '{package}' package. " f"Install it with: {hint}",
        ) from exc


def normalize_score(
    value: float,
    *,
    min_val: float = 0.0,
    max_val: float = 1.0,
    invert: bool = False,
) -> float:
    """Normalise a score to the 0-1 range.

    Args:
        value: Raw score
        min_val: Minimum of the input range
        max_val: Maximum of the input range
        invert: If *True*, flip so that lower raw values become higher normalised values

    Returns:
        Score clamped and mapped to ``[0.0, 1.0]``
    """
    if max_val == min_val:
        return 0.5
    normalised = (value - min_val) / (max_val - min_val)
    normalised = max(0.0, min(1.0, normalised))
    return 1.0 - normalised if invert else normalised


def format_rationale(
    metric_name: str,
    score: float,
    *,
    details: str | None = None,
    source: str | None = None,
) -> str:
    """Build a standardised rationale string.

    Args:
        metric_name: Name of the metric
        score: Numerical score
        details: Optional additional explanation
        source: Provider name (e.g. ``"DeepEval"``, ``"RAGAS"``)

    Returns:
        Formatted rationale string
    """
    parts = [f"{metric_name}: {score:.4f}"]
    if source:
        parts[0] = f"[{source}] {parts[0]}"
    if details:
        parts.append(details)
    return " — ".join(parts)
