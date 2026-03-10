"""Map Task — First-class parallel processing over typed collections.

Inspired by Flyte's array node handler, this module provides a `@map_task`
decorator that automatically distributes work over collections with
configurable concurrency, per-item retries, and partial failure tolerance.

Usage:
    from flowyml.core.map_task import map_task

    @map_task(concurrency=4, retries=2, min_success_ratio=0.9)
    def process_record(record: dict) -> ProcessedRecord:
        return transform(record)

    # In pipeline:
    pipeline.add_step(process_record, inputs=["raw_records"], outputs=["processed"])
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from flowyml.core.step import Step

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class MapTaskResult:
    """Result of a map task execution.

    Attributes:
        results: List of individual results (None for failed items)
        successes: Number of successful items
        failures: Number of failed items
        errors: Dict mapping index to error message for failed items
        total: Total number of items processed
        success_ratio: Ratio of successful items
    """

    results: list[Any] = field(default_factory=list)
    successes: int = 0
    failures: int = 0
    errors: dict[int, str] = field(default_factory=dict)
    total: int = 0

    @property
    def success_ratio(self) -> float:
        """Ratio of successful items."""
        return self.successes / self.total if self.total > 0 else 0.0

    @property
    def successful_results(self) -> list[Any]:
        """Only the successful results (no Nones)."""
        return [r for r in self.results if r is not None]


@dataclass
class MapTaskConfig:
    """Configuration for a map task.

    Attributes:
        concurrency: Maximum number of parallel workers
        retries: Number of retries per item on failure
        retry_delay: Delay in seconds between retries
        min_success_ratio: Minimum ratio of items that must succeed (0.0-1.0)
        fail_fast: If True, stop on first failure instead of processing all items
        timeout_per_item: Optional timeout in seconds per item
    """

    concurrency: int = 4
    retries: int = 0
    retry_delay: float = 1.0
    min_success_ratio: float = 1.0
    fail_fast: bool = False
    timeout_per_item: int | None = None


class MapTaskStep(Step):
    """A step that maps a function over a collection in parallel.

    Extends the standard Step with map-task-specific behavior: the function
    processes a single item, and the runtime distributes it over the input
    collection.
    """

    def __init__(
        self,
        func: Callable,
        config: MapTaskConfig,
        name: str | None = None,
        **step_kwargs,
    ):
        super().__init__(func=func, name=name, **step_kwargs)
        self.map_config = config
        self._is_map_task = True

    def __call__(self, collection: list[Any], *args, **kwargs) -> MapTaskResult:
        """Execute the map task over a collection.

        Args:
            collection: Iterable of items to process
            *args: Additional positional arguments passed to each invocation
            **kwargs: Additional keyword arguments passed to each invocation

        Returns:
            MapTaskResult with results and metadata

        Raises:
            RuntimeError: If success ratio falls below min_success_ratio
        """
        if not isinstance(collection, (list, tuple)):
            # If a single item is passed, wrap it
            collection = [collection]

        total = len(collection)
        result = MapTaskResult(
            results=[None] * total,
            total=total,
        )

        if total == 0:
            return result

        # Execute with thread pool
        with ThreadPoolExecutor(max_workers=self.map_config.concurrency) as executor:
            futures = {}

            for idx, item in enumerate(collection):
                future = executor.submit(
                    self._process_item,
                    item,
                    idx,
                    *args,
                    **kwargs,
                )
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    item_result = future.result()
                    result.results[idx] = item_result
                    result.successes += 1
                except Exception as e:
                    result.failures += 1
                    result.errors[idx] = str(e)
                    logger.warning(
                        f"Map task '{self.name}' item {idx} failed: {e}",
                    )

                    if self.map_config.fail_fast:
                        # Cancel remaining futures
                        for f in futures:
                            f.cancel()
                        break

        # Check success ratio
        if result.success_ratio < self.map_config.min_success_ratio:
            raise RuntimeError(
                f"Map task '{self.name}' failed: success ratio "
                f"{result.success_ratio:.1%} < minimum "
                f"{self.map_config.min_success_ratio:.1%}. "
                f"{result.failures}/{result.total} items failed.",
            )

        return result

    def _process_item(self, item: Any, index: int, *args, **kwargs) -> Any:
        """Process a single item with retry logic.

        Args:
            item: The item to process
            index: Index in the collection
            *args: Additional args
            **kwargs: Additional kwargs

        Returns:
            Result from processing the item

        Raises:
            Last exception if all retries fail
        """
        last_error = None
        max_attempts = 1 + self.map_config.retries

        for attempt in range(max_attempts):
            try:
                return self.func(item, *args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_attempts - 1:
                    delay = self.map_config.retry_delay * (2**attempt)
                    logger.debug(
                        f"Map task '{self.name}' item {index} attempt "
                        f"{attempt + 1}/{max_attempts} failed, "
                        f"retrying in {delay}s: {e}",
                    )
                    time.sleep(delay)

        raise last_error


def map_task(
    _func: Callable | None = None,
    *,
    concurrency: int = 4,
    retries: int = 0,
    retry_delay: float = 1.0,
    min_success_ratio: float = 1.0,
    fail_fast: bool = False,
    timeout_per_item: int | None = None,
    name: str | None = None,
    **step_kwargs,
):
    """Decorator to create a map task from a single-item processing function.

    The decorated function should process a single item. When called in a
    pipeline, it will automatically be distributed over the input collection.

    Args:
        _func: Function being decorated (when used as @map_task)
        concurrency: Maximum parallel workers (default: 4)
        retries: Per-item retry count (default: 0)
        retry_delay: Base delay between retries in seconds (default: 1.0)
        min_success_ratio: Minimum success ratio before failing (default: 1.0)
        fail_fast: Stop on first failure (default: False)
        timeout_per_item: Optional timeout per item in seconds
        name: Optional custom step name
        **step_kwargs: Additional Step kwargs (inputs, outputs, etc.)

    Example:
        >>> @map_task(concurrency=8, retries=2, min_success_ratio=0.95)
        ... def process_document(doc: dict) -> ProcessedDoc:
        ...     return transform(doc)
        >>>
        >>> # Use in pipeline
        >>> pipeline.add_step(process_document)
    """
    config = MapTaskConfig(
        concurrency=concurrency,
        retries=retries,
        retry_delay=retry_delay,
        min_success_ratio=min_success_ratio,
        fail_fast=fail_fast,
        timeout_per_item=timeout_per_item,
    )

    def decorator(func: Callable) -> MapTaskStep:
        return MapTaskStep(
            func=func,
            config=config,
            name=name or func.__name__,
            **step_kwargs,
        )

    if _func is None:
        return decorator
    else:
        return decorator(_func)
