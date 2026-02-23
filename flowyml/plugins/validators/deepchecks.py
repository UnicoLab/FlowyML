"""Deepchecks Data Validator - Native FlowyML Plugin.

This plugin integrates Deepchecks for robust data validation,
including integrity, drift, and performance checks.
"""

import logging
from typing import Any

from flowyml.plugins.base import DataValidatorPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class DeepchecksValidator(DataValidatorPlugin):
    """Deepchecks data validator for FlowyML.

    Run suites of data validation checks using Deepchecks.

    Args:
        suite: Name of the default suite to run (e.g., 'integrity', 'train_test_validation').
    """

    metadata = PluginMetadata(
        name="deepchecks",
        version="1.0.0",
        description="Deepchecks Data Validator",
        author="FlowyML Team",
        plugin_type=PluginType.DATA_VALIDATOR,
        tags=["validation", "data-quality", "drift"],
        packages=["deepchecks>=0.17.0"],
    )

    def __init__(self, suite: str = "integrity", **kwargs):
        super().__init__(**kwargs)
        self.default_suite = suite
        self._deepchecks = None

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DATA_VALIDATOR

    def initialize(self) -> None:
        """Initialize Deepchecks."""
        try:
            import deepchecks
            from deepchecks.tabular import Dataset
            from deepchecks.tabular import suites

            self._deepchecks = deepchecks
            self._dc_suites = suites
            self._dc_dataset = Dataset

            logger.info("Deepchecks validator initialized.")

        except ImportError:
            raise ImportError(
                "deepchecks is required. Install with: pip install deepchecks",
            )

    def validate(self, data: Any, expectations: Any = None) -> dict[str, Any]:
        """Validate data using Deepchecks.

        Args:
            data: Pandas DataFrame or supported Deepchecks dataset.
            expectations: Optional suite name or Suite object.
                         If None, uses self.default_suite.

        Returns:
            Validation result dictionary (passed, results json).
        """
        self.initialize()

        # Resolve suite
        suite_obj = None
        suite_name = expectations or self.default_suite

        if isinstance(suite_name, str):
            if hasattr(self._dc_suites, suite_name):
                suite_obj = getattr(self._dc_suites, suite_name)()
            else:
                # Try to create a full suite if name not found in presets
                logger.warning(
                    f"Suite '{suite_name}' not found in default suites, falling back to full suite.",
                )
                suite_obj = self._dc_suites.full_suite()
        else:
            # Assume it's a Suite object passed directly
            suite_obj = suite_name

        # Wrap data if needed
        # This is a simplified wrapper; real usage might require label/cat_features config
        if not isinstance(data, self._dc_dataset):
            from pandas import DataFrame

            if isinstance(data, DataFrame):
                ds = self._dc_dataset(data)
            else:
                raise ValueError(f"Deepchecks requires DataFrame or Dataset, got {type(data)}")
        else:
            ds = data

        logger.info(f"Running Deepchecks suite: {suite_name}")
        result = suite_obj.run(ds)

        # Determine overall success (if any check failed)
        # Deepchecks results structure varies, but we can serialize to json/dict
        passed = result.passed() if hasattr(result, "passed") else True  # simplified check

        return {
            "passed": passed,
            "suite_name": str(suite_name),
            "results": result.to_json(),
            "report_html": result.save_as_html(),  # Returns path string usually
        }

    def get_data_profile(self, data: Any) -> dict[str, Any]:
        """Profile data using Deepchecks integrity suite as a proxy."""
        # Deepchecks doesn't have a pure "profile" methods like pandas-profiling
        # but we can run a quick check
        return self.validate(data, expectations="integrity")
