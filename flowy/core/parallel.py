"""Parallel and distributed execution utilities."""

import concurrent.futures
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import multiprocessing


@dataclass
class ParallelConfig:
    """Configuration for parallel execution."""

    max_workers: int = None  # None = CPU count
    backend: str = "thread"  # "thread" or "process"
    timeout: Optional[float] = None
    chunk_size: int = 1


class ParallelExecutor:
    """Execute steps in parallel.

    Example:
        ```python
        from flowy.core.parallel import ParallelExecutor

        executor = ParallelExecutor(max_workers=4)

        @step(parallel=True)
        def process_shard(shard):
            return expensive_processing(shard)

        results = executor.map(process_shard, shards)
        ```
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        backend: str = "thread",
        timeout: Optional[float] = None,
    ):
        """Initialize parallel executor.

        Args:
            max_workers: Maximum worker threads/processes (None = CPU count)
            backend: "thread" for threading or "process" for multiprocessing
            timeout: Timeout for each task in seconds
        """
        self.config = ParallelConfig(
            max_workers=max_workers or multiprocessing.cpu_count(),
            backend=backend,
            timeout=timeout,
        )

    def map(
        self,
        func: Callable,
        items: List[Any],
        **kwargs
    ) -> List[Any]:
        """Execute function in parallel over items.

        Args:
            func: Function to execute
            items: Items to process
            **kwargs: Additional arguments for function

        Returns:
            List of results in same order as items
        """
        if self.config.backend == "thread":
            executor_class = concurrent.futures.ThreadPoolExecutor
        else:
            executor_class = concurrent.futures.ProcessPoolExecutor

        with executor_class(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            futures = []
            for item in items:
                if kwargs:
                    future = executor.submit(func, item, **kwargs)
                else:
                    future = executor.submit(func, item)
                futures.append(future)

            # Collect results
            results = []
            for future in concurrent.futures.as_completed(
                futures,
                timeout=self.config.timeout
            ):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ParallelExecutionError(str(e)))

        return results

    def starmap(
        self,
        func: Callable,
        items: List[tuple],
    ) -> List[Any]:
        """Execute function with multiple arguments in parallel.

        Args:
            func: Function to execute
            items: List of tuples (each tuple is arguments for one call)

        Returns:
            List of results
        """
        if self.config.backend == "thread":
            executor_class = concurrent.futures.ThreadPoolExecutor
        else:
            executor_class = concurrent.futures.ProcessPoolExecutor

        with executor_class(max_workers=self.config.max_workers) as executor:
            futures = [executor.submit(func, *args) for args in items]

            results = []
            for future in concurrent.futures.as_completed(
                futures,
                timeout=self.config.timeout
            ):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ParallelExecutionError(str(e)))

        return results

    def execute_parallel_steps(
        self,
        steps: List[Callable],
        inputs: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Execute multiple independent steps in parallel.

        Args:
            steps: List of step functions to execute
            inputs: Shared inputs for all steps

        Returns:
            List of results from each step
        """
        inputs = inputs or {}

        if self.config.backend == "thread":
            executor_class = concurrent.futures.ThreadPoolExecutor
        else:
            executor_class = concurrent.futures.ProcessPoolExecutor

        with executor_class(max_workers=self.config.max_workers) as executor:
            futures = {executor.submit(step, **inputs): step for step in steps}

            results = []
            for future in concurrent.futures.as_completed(
                futures,
                timeout=self.config.timeout
            ):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ParallelExecutionError(str(e)))

        return results


class ParallelExecutionError:
    """Marker for failed parallel execution."""

    def __init__(self, error_message: str):
        self.error_message = error_message
        self.failed = True

    def __repr__(self):
        return f"<ParallelExecutionError: {self.error_message}>"

    def __bool__(self):
        return False


def parallel_map(
    func: Callable,
    items: List[Any],
    max_workers: Optional[int] = None,
    backend: str = "thread",
) -> List[Any]:
    """Quick parallel map function.

    Args:
        func: Function to apply
        items: Items to process
        max_workers: Maximum workers
        backend: "thread" or "process"

    Returns:
        List of results

    Example:
        ```python
        from flowy.core.parallel import parallel_map

        results = parallel_map(process_item, items, max_workers=4)
        ```
    """
    executor = ParallelExecutor(max_workers=max_workers, backend=backend)
    return executor.map(func, items)


class DataParallelExecutor:
    """Execute operations on data-parallel partitions.

    Example:
        ```python
        from flowy.core.parallel import DataParallelExecutor

        executor = DataParallelExecutor(num_partitions=4)

        @step
        def process_partition(data_partition):
            return train_on_partition(data_partition)

        results = executor.execute_data_parallel(process_partition, large_dataset)
        ```
    """

    def __init__(self, num_partitions: int = 4):
        """Initialize data parallel executor.

        Args:
            num_partitions: Number of data partitions
        """
        self.num_partitions = num_partitions
        self.executor = ParallelExecutor(max_workers=num_partitions)

    def partition_data(self, data: Any) -> List[Any]:
        """Partition data for parallel processing.

        Args:
            data: Data to partition

        Returns:
            List of data partitions
        """
        try:
            # Try to partition list-like data
            if hasattr(data, "__len__"):
                n = len(data)
                partition_size = n // self.num_partitions
                partitions = []

                for i in range(self.num_partitions):
                    start = i * partition_size
                    end = start + partition_size if i < self.num_partitions - 1 else n
                    partitions.append(data[start:end])

                return partitions
        except:
            pass

        # If partitioning fails, return single partition
        return [data]

    def execute_data_parallel(
        self,
        func: Callable,
        data: Any,
    ) -> List[Any]:
        """Execute function on data partitions in parallel.

        Args:
            func: Function to execute on each partition
            data: Data to partition and process

        Returns:
            List of results from each partition
        """
        partitions = self.partition_data(data)
        return self.executor.map(func, partitions)

    def reduce_results(
        self,
        results: List[Any],
        reduce_func: Optional[Callable] = None,
    ) -> Any:
        """Reduce parallel results to single output.

        Args:
            results: List of partition results
            reduce_func: Function to reduce results (default: concatenate)

        Returns:
            Reduced result
        """
        if reduce_func:
            return reduce_func(results)

        # Default: try to concatenate
        try:
            # Try list concatenation
            if all(isinstance(r, list) for r in results):
                result = []
                for r in results:
                    result.extend(r)
                return result

            # Try dict merge
            if all(isinstance(r, dict) for r in results):
                result = {}
                for r in results:
                    result.update(r)
                return result

            # Return as-is
            return results

        except:
            return results


def distribute_across_gpus(
    func: Callable,
    items: List[Any],
    gpu_ids: Optional[List[int]] = None,
) -> List[Any]:
    """Distribute work across multiple GPUs.

    Args:
        func: Function to execute
        items: Items to process
        gpu_ids: List of GPU IDs to use (None = use all available)

    Returns:
        List of results

    Example:
        ```python
        from flowy.core.parallel import distribute_across_gpus

        results = distribute_across_gpus(
            train_on_gpu,
            data_shards,
            gpu_ids=[0, 1, 2, 3]
        )
        ```
    """
    try:
        import torch

        if gpu_ids is None:
            if torch.cuda.is_available():
                gpu_ids = list(range(torch.cuda.device_count()))
            else:
                gpu_ids = [-1]  # CPU fallback

    except ImportError:
        gpu_ids = [-1]  # CPU fallback

    # Distribute items across GPUs
    num_gpus = len(gpu_ids)
    results = []

    def execute_on_gpu(item_and_gpu):
        item, gpu_id = item_and_gpu
        # Set device for this process
        if gpu_id >= 0:
            try:
                import torch
                torch.cuda.set_device(gpu_id)
            except:
                pass
        return func(item)

    # Pair items with GPU IDs in round-robin fashion
    items_with_gpus = [(item, gpu_ids[i % num_gpus]) for i, item in enumerate(items)]

    # Execute in parallel
    executor = ParallelExecutor(max_workers=num_gpus, backend="process")
    return executor.map(execute_on_gpu, items_with_gpus)


class BatchExecutor:
    """Execute function on batches in parallel.

    Example:
        ```python
        from flowy.core.parallel import BatchExecutor

        executor = BatchExecutor(batch_size=32, max_workers=4)

        results = executor.execute_batches(
            inference_func,
            large_dataset
        )
        ```
    """

    def __init__(
        self,
        batch_size: int = 32,
        max_workers: Optional[int] = None,
    ):
        """Initialize batch executor.

        Args:
            batch_size: Size of each batch
            max_workers: Maximum parallel workers
        """
        self.batch_size = batch_size
        self.executor = ParallelExecutor(max_workers=max_workers)

    def create_batches(self, items: List[Any]) -> List[List[Any]]:
        """Create batches from items.

        Args:
            items: Items to batch

        Returns:
            List of batches
        """
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batches.append(batch)
        return batches

    def execute_batches(
        self,
        func: Callable,
        items: List[Any],
    ) -> List[Any]:
        """Execute function on batches in parallel.

        Args:
            func: Function to execute on each batch
            items: Items to process

        Returns:
            List of all results (flattened)
        """
        batches = self.create_batches(items)
        batch_results = self.executor.map(func, batches)

        # Flatten results
        results = []
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)

        return results
