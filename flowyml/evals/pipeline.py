"""FlowyML Evaluations — Pipeline Step Integration.

Evaluation-as-a-Pipeline-Step: run evaluations as part of your ML pipeline,
with results automatically tracked alongside other step outputs.
"""

import logging
from typing import Any

from flowyml.evals.base import Scorer
from flowyml.evals.core import EvalResult, evaluate
from flowyml.evals.dataset import EvalDataset

logger = logging.getLogger(__name__)


class EvalStep:
    """Evaluation pipeline step — integrates evaluations into FlowyML pipelines.

    When added as a pipeline step, this runs scorers against data produced
    by prior steps and emits EvalResult as its output asset.

    Can be used with the @step decorator pattern or directly via add_step().

    Example:
        >>> from flowyml import Pipeline, step
        >>> from flowyml.evals import EvalStep, Accuracy, F1Score
        >>>
        >>> pipeline = Pipeline("training_pipeline")
        >>>
        >>> @step
        >>> def train_model(data):
        ...     model = ...
        ...     predictions = model.predict(data.X_test)
        ...     return {"predictions": predictions, "targets": data.y_test}
        >>>
        >>> eval_step = EvalStep(
        ...     scorers=[Accuracy(threshold=0.9), F1Score(threshold=0.85)],
        ...     fail_on_regression=True,
        ... )
        >>>
        >>> pipeline.add_step(train_model)
        >>> pipeline.add_step(eval_step)
        >>> result = pipeline.run(inputs={"data": dataset})
    """

    def __init__(
        self,
        scorers: list[Scorer] | None = None,
        baseline: EvalResult | None = None,
        fail_on_regression: bool = False,
        regression_threshold: float = 0.05,
        experiment: str | None = None,
        name: str = "evaluation",
        **kwargs: Any,
    ):
        """Initialize the evaluation step.

        Args:
            scorers: List of scorers to run
            baseline: Optional baseline EvalResult for regression checking
            fail_on_regression: Whether to fail the pipeline on regression
            regression_threshold: Regression detection threshold
            experiment: Experiment name for tracking
            name: Step name
            **kwargs: Additional arguments
        """
        self.scorers = scorers or []
        self.baseline = baseline
        self.fail_on_regression = fail_on_regression
        self.regression_threshold = regression_threshold
        self.experiment = experiment
        self.name = name
        self._config = kwargs

    def __call__(
        self,
        data: EvalDataset | dict | list | None = None,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> EvalResult:
        """Execute the evaluation step.

        Accepts either an EvalDataset, a dict with predictions/targets,
        or separate predictions and targets arguments.

        Args:
            data: Evaluation data (EvalDataset, dict, or list)
            predictions: Model predictions (alternative to data)
            targets: Ground truth (alternative to data)
            **kwargs: Additional scorer arguments

        Returns:
            EvalResult
        """
        # Build EvalDataset if not provided
        if data is None:
            if predictions is not None and targets is not None:
                data = EvalDataset.create_classical(
                    name=f"eval_step_{self.name}",
                    predictions=predictions,
                    targets=targets,
                )
            else:
                raise ValueError(
                    "EvalStep requires either 'data' (EvalDataset) or 'predictions' + 'targets' arguments",
                )
        elif isinstance(data, dict):
            if "predictions" in data and "targets" in data:
                data = EvalDataset.create_classical(
                    name=f"eval_step_{self.name}",
                    predictions=data["predictions"],
                    targets=data["targets"],
                )
            else:
                data = EvalDataset(name=f"eval_step_{self.name}", data=data)

        result = evaluate(
            data=data,
            scorers=self.scorers,
            experiment=self.experiment,
            baseline=self.baseline,
            regression_threshold=self.regression_threshold,
            **kwargs,
        )

        # Check for regressions and optionally fail
        if self.fail_on_regression and self.baseline:
            regressions = result.regressions_from(
                self.baseline,
                threshold=self.regression_threshold,
            )
            if regressions:
                reg_msg = ", ".join(f"{k}: {v['baseline']:.4f} → {v['current']:.4f}" for k, v in regressions.items())
                raise RuntimeError(
                    f"Evaluation regressions detected in step '{self.name}': {reg_msg}",
                )

        logger.info("EvalStep '%s' complete: %s", self.name, result.summary)
        return result

    def with_baseline(self, baseline: EvalResult) -> "EvalStep":
        """Set the baseline for regression detection.

        Args:
            baseline: Baseline EvalResult

        Returns:
            self for chaining
        """
        self.baseline = baseline
        return self

    def add_scorer(self, scorer: Scorer) -> "EvalStep":
        """Add a scorer to the step.

        Args:
            scorer: Scorer to add

        Returns:
            self for chaining
        """
        self.scorers.append(scorer)
        return self

    def __repr__(self) -> str:
        return (
            f"EvalStep(name='{self.name}', scorers={len(self.scorers)}, fail_on_regression={self.fail_on_regression})"
        )
