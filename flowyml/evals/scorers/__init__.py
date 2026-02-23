"""FlowyML Evaluations — Scorer Registry with Auto-Discovery.

Central registry of all available scorers. Supports built-in scorers,
plugin-based scorers, and user-registered custom scorers.
"""

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType

# Import scorer registries
from flowyml.evals.scorers.classification import CLASSIFICATION_SCORERS
from flowyml.evals.scorers.regression import REGRESSION_SCORERS
from flowyml.evals.scorers.genai import GENAI_SCORERS
from flowyml.evals.scorers.custom import (
    FunctionScorer,
    CustomJudge,
    make_judge,
    make_scorer,
)

# Import individual scorers for direct access
from flowyml.evals.scorers.classification import (
    Accuracy,
    Precision,
    Recall,
    F1Score,
    AUCROC,
    ConfusionMatrixScorer,
    LogLoss,
)
from flowyml.evals.scorers.regression import (
    MSE,
    RMSE,
    MAE,
    R2Score,
    MAPE,
    MaxError,
)
from flowyml.evals.scorers.genai import (
    Relevance,
    Coherence,
    Toxicity,
    Faithfulness,
)

# Third-party adapter scorers (optional dependencies)
from flowyml.evals.scorers.deepeval_adapter import (
    DEEPEVAL_SCORERS,
    DeepEvalAnswerRelevancy,
    DeepEvalHallucination,
    DeepEvalBias,
    DeepEvalToxicity,
)
from flowyml.evals.scorers.ragas_adapter import (
    RAGAS_SCORERS,
    RagasFaithfulness,
    RagasContextPrecision,
    RagasContextRecall,
    RagasAnswerRelevancy,
)
from flowyml.evals.scorers.phoenix_adapter import (
    PHOENIX_SCORERS,
    PhoenixHallucination,
    PhoenixToxicity,
    PhoenixQACorrectness,
    PhoenixSummarization,
)

# Unified registry of all built-in scorers
SCORER_REGISTRY: dict[str, type[Scorer]] = {}
SCORER_REGISTRY.update(CLASSIFICATION_SCORERS)
SCORER_REGISTRY.update(REGRESSION_SCORERS)
SCORER_REGISTRY.update(GENAI_SCORERS)
# Third-party adapters (namespaced: "deepeval.", "ragas.", "phoenix.")
SCORER_REGISTRY.update(DEEPEVAL_SCORERS)
SCORER_REGISTRY.update(RAGAS_SCORERS)
SCORER_REGISTRY.update(PHOENIX_SCORERS)


def get_scorer(name: str, **kwargs) -> Scorer:
    """Get a scorer by name from the registry.

    Args:
        name: Scorer name (e.g., 'accuracy', 'deepeval.hallucination', 'ragas.faithfulness')
        **kwargs: Scorer configuration arguments

    Returns:
        Scorer instance

    Raises:
        ValueError: If scorer name is not found

    Example:
        >>> scorer = get_scorer("accuracy", threshold=0.9)
    """
    if name not in SCORER_REGISTRY:
        available = ", ".join(sorted(SCORER_REGISTRY.keys()))
        raise ValueError(f"Unknown scorer '{name}'. Available: {available}")
    return SCORER_REGISTRY[name](**kwargs)


def register_scorer(name: str, scorer_class: type[Scorer]) -> None:
    """Register a custom scorer class in the global registry.

    Args:
        name: Name to register under
        scorer_class: Scorer class (not instance)
    """
    SCORER_REGISTRY[name] = scorer_class


def list_scorers(scorer_type: str | None = None) -> list[dict]:
    """List all available scorers with metadata.

    Args:
        scorer_type: Optional filter by type ('classification', 'regression', 'genai')

    Returns:
        List of scorer metadata dicts
    """
    result = []
    for name, cls in sorted(SCORER_REGISTRY.items()):
        scorer = cls()
        st = scorer.scorer_type
        type_value = st.value if isinstance(st, ScorerType) else str(st)
        if scorer_type and type_value != scorer_type:
            continue
        result.append(
            {
                "name": name,
                "type": type_value,
                "description": scorer.description,
                "class": cls.__name__,
            },
        )
    return result


def discover_plugin_scorers() -> dict[str, type[Scorer]]:
    """Discover scorers registered as FlowyML plugins.

    Returns:
        Dict of discovered scorer name -> class
    """
    discovered = {}
    try:
        from flowyml.plugins.base import PluginType

        try:
            from flowyml.plugins.manager import PluginManager

            manager = PluginManager()
            evaluator_plugins = manager.get_plugins(PluginType.EVALUATOR)
            for plugin in evaluator_plugins:
                if isinstance(plugin, Scorer):
                    discovered[plugin.name] = type(plugin)
                    SCORER_REGISTRY[plugin.name] = type(plugin)
        except (ImportError, AttributeError):
            pass
    except ImportError:
        pass

    return discovered


__all__ = [
    # Base
    "Scorer",
    "ScorerFeedback",
    "ScorerType",
    # Classification
    "Accuracy",
    "Precision",
    "Recall",
    "F1Score",
    "AUCROC",
    "ConfusionMatrixScorer",
    "LogLoss",
    # Regression
    "MSE",
    "RMSE",
    "MAE",
    "R2Score",
    "MAPE",
    "MaxError",
    # GenAI
    "Relevance",
    "Coherence",
    "Toxicity",
    "Faithfulness",
    # Custom
    "FunctionScorer",
    "CustomJudge",
    "make_judge",
    "make_scorer",
    # DeepEval adapters
    "DeepEvalAnswerRelevancy",
    "DeepEvalHallucination",
    "DeepEvalBias",
    "DeepEvalToxicity",
    # RAGAS adapters
    "RagasFaithfulness",
    "RagasContextPrecision",
    "RagasContextRecall",
    "RagasAnswerRelevancy",
    # Phoenix adapters
    "PhoenixHallucination",
    "PhoenixToxicity",
    "PhoenixQACorrectness",
    "PhoenixSummarization",
    # Registry
    "get_scorer",
    "register_scorer",
    "list_scorers",
    "discover_plugin_scorers",
    "SCORER_REGISTRY",
]
