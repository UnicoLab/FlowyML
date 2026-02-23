"""FlowyML Evaluations — Continuous Evaluation via Schedules.

Enables scheduling recurring evaluations using the existing PipelineScheduler.
"""

import logging
from typing import Any

from flowyml.evals.base import Scorer
from flowyml.evals.core import EvalResult
from flowyml.evals.dataset import EvalDataset
from flowyml.evals.run import EvalRun

logger = logging.getLogger(__name__)


class EvalSchedule:
    """Schedule recurring evaluations.

    Integrates with FlowyML's PipelineScheduler to run evaluations
    on a regular basis (cron schedule), with automatic regression
    detection against the previous run.

    Example:
        >>> from flowyml.evals import EvalSchedule, Accuracy, Relevance
        >>>
        >>> schedule = EvalSchedule(
        ...     name="daily_quality_check",
        ...     scorers=[Accuracy(), Relevance()],
        ...     cron="0 6 * * *",  # 6 AM daily
        ...     dataset_loader=lambda: load_latest_test_data(),
        ...     alert_on_regression=True,
        ... )
        >>> schedule.start()
    """

    def __init__(
        self,
        name: str,
        scorers: list[Scorer],
        dataset_loader: Any | None = None,
        dataset: EvalDataset | None = None,
        cron: str = "0 0 * * *",  # Daily at midnight
        experiment: str | None = None,
        alert_on_regression: bool = True,
        regression_threshold: float = 0.05,
        alert_callback: Any | None = None,
        max_history: int = 100,
        **kwargs: Any,
    ):
        self.name = name
        self.scorers = scorers
        self.dataset_loader = dataset_loader
        self.dataset = dataset
        self.cron = cron
        self.experiment = experiment or f"scheduled_{name}"
        self.alert_on_regression = alert_on_regression
        self.regression_threshold = regression_threshold
        self.alert_callback = alert_callback
        self.max_history = max_history
        self._history: list[EvalResult] = []
        self._config = kwargs
        self._scheduler = None

    def run_once(self) -> EvalResult:
        """Execute a single evaluation run.

        Returns:
            EvalResult from this run
        """
        # Get dataset
        if self.dataset_loader:
            data = self.dataset_loader()
            if not isinstance(data, EvalDataset):
                data = EvalDataset(name=f"scheduled_{self.name}", data=data)
        elif self.dataset:
            data = self.dataset
        else:
            raise ValueError("Either dataset or dataset_loader must be provided")

        # Determine baseline
        baseline = self._history[-1] if self._history else None

        # Run evaluation
        run = EvalRun(experiment=self.experiment)
        result = run.execute(
            data=data,
            scorers=self.scorers,
            baseline=baseline,
            regression_threshold=self.regression_threshold,
        )

        # Store history
        self._history.append(result)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

        # Alert on regression
        if self.alert_on_regression and run.has_regressions:
            self._send_alert(result, run.regressions)

        return result

    def _send_alert(self, result: EvalResult, regressions: dict) -> None:
        """Send regression alert."""
        message = f"⚠️ Evaluation regression detected in '{self.name}':\n" + "\n".join(
            f"  - {k}: {v['baseline']:.4f} → {v['current']:.4f} (Δ{v['delta']:.4f})" for k, v in regressions.items()
        )
        logger.warning(message)

        if self.alert_callback:
            try:
                self.alert_callback(message, result, regressions)
            except Exception as e:
                logger.error("Alert callback failed: %s", e)

    def start(self) -> None:
        """Start the scheduled evaluations.

        Integrates with FlowyML's PipelineScheduler if available,
        otherwise logs a warning.
        """
        try:
            from flowyml.core.scheduler import PipelineScheduler

            self._scheduler = PipelineScheduler()
            self._scheduler.add_job(
                func=self.run_once,
                trigger="cron",
                name=self.name,
                **self._parse_cron(),
            )
            self._scheduler.start()
            logger.info("Scheduled evaluation '%s' started: %s", self.name, self.cron)
        except ImportError:
            logger.warning(
                "PipelineScheduler not available. " "Use run_once() manually or install scheduling dependencies.",
            )
        except Exception as e:
            logger.error("Failed to start schedule '%s': %s", self.name, e)

    def stop(self) -> None:
        """Stop the scheduled evaluations."""
        if self._scheduler:
            self._scheduler.stop()
            logger.info("Scheduled evaluation '%s' stopped", self.name)

    def _parse_cron(self) -> dict:
        """Parse cron expression into scheduler kwargs."""
        parts = self.cron.split()
        if len(parts) == 5:
            return {
                "minute": parts[0],
                "hour": parts[1],
                "day": parts[2],
                "month": parts[3],
                "day_of_week": parts[4],
            }
        return {}

    @property
    def history(self) -> list[EvalResult]:
        """Get evaluation history."""
        return list(self._history)

    @property
    def latest(self) -> EvalResult | None:
        """Get the most recent evaluation result."""
        return self._history[-1] if self._history else None

    def __repr__(self) -> str:
        return (
            f"EvalSchedule(name='{self.name}', cron='{self.cron}', "
            f"scorers={len(self.scorers)}, history={len(self._history)})"
        )
