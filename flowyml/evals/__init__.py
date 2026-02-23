"""FlowyML Evaluations — Public API.

The comprehensive evaluation framework for both classical ML and GenAI models.

Features:
- Unified Scorer protocol for all evaluation types
- 17 built-in scorers (classification, regression, GenAI)
- EvalDataset as a first-class versioned asset
- EvalSuite for grouping and reusing scorer collections
- evaluate() function with automatic regression detection
- JudgeArena for A/B testing evaluators
- TraceBridge for trace-to-evaluation conversion
- EvalAssert for CI/CD quality gates
- EvalStep for evaluation-as-a-pipeline-step
- EvalSchedule for continuous evaluation
- make_judge() and make_scorer() for custom evaluators
"""

# Core protocol and data models
from flowyml.evals.base import (
    Scorer,
    ScorerFeedback,
    ScorerType,
)

# Evaluate function and result
from flowyml.evals.core import (
    EvalResult,
    evaluate,
)

# Dataset asset
from flowyml.evals.dataset import EvalDataset

# Evaluation suite
from flowyml.evals.suite import EvalSuite

# Evaluation run tracking
from flowyml.evals.run import EvalRun

# Judge Arena (A/B testing evaluators)
from flowyml.evals.arena import JudgeArena, JudgeArenaResult

# Trace bridge
from flowyml.evals.bridge import TraceBridge, trace_bridge, evaluate_traces

# CI/CD assertions
from flowyml.evals.assertions import EvalAssert, AssertionResult

# Pipeline integration
from flowyml.evals.pipeline import EvalStep

# Continuous evaluation
from flowyml.evals.schedule import EvalSchedule

# Scorer registry and factories
from flowyml.evals.scorers import (
    # Registry
    get_scorer,
    register_scorer,
    list_scorers,
    discover_plugin_scorers,
    SCORER_REGISTRY,
    # Classification scorers
    Accuracy,
    Precision,
    Recall,
    F1Score,
    AUCROC,
    ConfusionMatrixScorer,
    LogLoss,
    # Regression scorers
    MSE,
    RMSE,
    MAE,
    R2Score,
    MAPE,
    MaxError,
    # GenAI scorers
    Relevance,
    Coherence,
    Toxicity,
    Faithfulness,
    # Custom factories
    FunctionScorer,
    CustomJudge,
    make_judge,
    make_scorer,
    # DeepEval adapters
    DeepEvalAnswerRelevancy,
    DeepEvalHallucination,
    DeepEvalBias,
    DeepEvalToxicity,
    # RAGAS adapters
    RagasFaithfulness,
    RagasContextPrecision,
    RagasContextRecall,
    RagasAnswerRelevancy,
    # Phoenix adapters
    PhoenixHallucination,
    PhoenixToxicity,
    PhoenixQACorrectness,
    PhoenixSummarization,
)


__all__ = [
    # Core
    "Scorer",
    "ScorerFeedback",
    "ScorerType",
    "EvalResult",
    "evaluate",
    "EvalDataset",
    "EvalSuite",
    "EvalRun",
    # Arena
    "JudgeArena",
    "JudgeArenaResult",
    # Bridge
    "TraceBridge",
    "trace_bridge",
    "evaluate_traces",
    # CI/CD
    "EvalAssert",
    "AssertionResult",
    # Pipeline
    "EvalStep",
    # Schedules
    "EvalSchedule",
    # Registry
    "get_scorer",
    "register_scorer",
    "list_scorers",
    "discover_plugin_scorers",
    "SCORER_REGISTRY",
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
]
