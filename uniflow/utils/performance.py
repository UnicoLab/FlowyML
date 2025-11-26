"""
Performance optimization utilities.
"""

import time
import functools
from typing import Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

class LazyValue:
    """
    Lazy evaluation wrapper.
    
    Computes value only when accessed.
    
    Examples:
        >>> lazy = LazyValue(lambda: expensive_computation())
        >>> # Not computed yet
        >>> result = lazy.value  # Now computed
    """
    
    def __init__(self, compute_func: Callable):
        self._compute_func = compute_func
        self._value = None
        self._computed = False
        
    @property
    def value(self):
        """Get the computed value."""
        if not self._computed:
            self._value = self._compute_func()
            self._computed = True
        return self._value
        
    def __repr__(self):
        if self._computed:
            return f"LazyValue(computed={self._value})"
        return "LazyValue(not computed)"

def lazy_property(func):
    """
    Decorator for lazy property evaluation.
    
    Example:
        >>> class Model:
        ...     @lazy_property
        ...     def expensive_data(self):
        ...         return load_large_dataset()
    """
    attr_name = '_lazy_' + func.__name__
    
    @property
    @functools.wraps(func)
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
        
    return wrapper

class ParallelExecutor:
    """
    Smart parallelization for pipeline steps.
    
    Automatically determines best parallelization strategy.
    
    Examples:
        >>> executor = ParallelExecutor(max_workers=4)
        >>> results = executor.map(process_item, items)
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        mode: str = "thread"  # 'thread' or 'process'
    ):
        self.max_workers = max_workers or mp.cpu_count()
        self.mode = mode
        
    def map(self, func: Callable, items: list) -> list:
        """
        Parallel map operation.
        
        Args:
            func: Function to apply
            items: Items to process
            
        Returns:
            List of results
        """
        if self.mode == "process":
            executor_class = ProcessPoolExecutor
        else:
            executor_class = ThreadPoolExecutor
            
        with executor_class(max_workers=self.max_workers) as executor:
            results = list(executor.map(func, items))
            
        return results
        
    def submit(self, func: Callable, *args, **kwargs):
        """Submit a single task."""
        if self.mode == "process":
            executor = ProcessPoolExecutor(max_workers=1)
        else:
            executor = ThreadPoolExecutor(max_workers=1)
            
        future = executor.submit(func, *args, **kwargs)
        return future

class IncrementalComputation:
    """
    Incremental computation for data processing.
    
    Processes data in chunks and caches intermediate results.
    
    Examples:
        >>> computer = IncrementalComputation(chunk_size=1000)
        >>> result = computer.compute(large_dataset, process_chunk)
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        cache_dir: str = ".uniflow/incremental"
    ):
        self.chunk_size = chunk_size
        from pathlib import Path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def compute(
        self,
        data: list,
        func: Callable,
        aggregate_func: Optional[Callable] = None
    ) -> Any:
        """
        Compute incrementally over data chunks.
        
        Args:
            data: Input data
            func: Function to apply to each chunk
            aggregate_func: Optional function to aggregate chunk results
            
        Returns:
            Aggregated result
        """
        results = []
        
        # Process in chunks
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            
            # Check cache
            cache_key = f"chunk_{i}"
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            
            if cache_file.exists():
                import pickle
                with open(cache_file, 'rb') as f:
                    chunk_result = pickle.load(f)
                print(f"   Loaded cached chunk {i//self.chunk_size + 1}")
            else:
                # Compute
                chunk_result = func(chunk)
                
                # Cache result
                import pickle
                with open(cache_file, 'wb') as f:
                    pickle.dump(chunk_result, f)
                    
            results.append(chunk_result)
            
        # Aggregate
        if aggregate_func:
            return aggregate_func(results)
        return results

class GPUResourceManager:
    """
    GPU resource management and allocation.
    
    Helps manage GPU memory and device placement.
    
    Examples:
        >>> gpu = GPUResourceManager()
        >>> if gpu.has_gpu():
        ...     with gpu.allocate_device(0):
        ...         # Run GPU operations
        ...         pass
    """
    
    def __init__(self):
        self._check_gpu_availability()
        
    def _check_gpu_availability(self):
        """Check for GPU availability."""
        try:
            import torch
            self.has_torch = True
            self.torch_available = torch.cuda.is_available()
            self.torch_device_count = torch.cuda.device_count() if self.torch_available else 0
        except ImportError:
            self.has_torch = False
            self.torch_available = False
            self.torch_device_count = 0
            
        try:
            import tensorflow as tf
            self.has_tf = True
            gpus = tf.config.list_physical_devices('GPU')
            self.tf_available = len(gpus) > 0
            self.tf_device_count = len(gpus)
        except ImportError:
            self.has_tf = False
            self.tf_available = False
            self.tf_device_count = 0
            
    def has_gpu(self) -> bool:
        """Check if GPU is available."""
        return self.torch_available or self.tf_available
        
    def get_device_count(self) -> int:
        """Get number of available GPUs."""
        return max(self.torch_device_count, self.tf_device_count)
        
    def allocate_device(self, device_id: int = 0):
        """Context manager to allocate specific GPU."""
        import os
        
        class DeviceContext:
            def __enter__(ctx_self):
                os.environ['CUDA_VISIBLE_DEVICES'] = str(device_id)
                return device_id
                
            def __exit__(ctx_self, *args):
                # Reset
                if 'CUDA_VISIBLE_DEVICES' in os.environ:
                    del os.environ['CUDA_VISIBLE_DEVICES']
                    
        return DeviceContext()
        
    def get_memory_info(self, device_id: int = 0) -> dict:
        """Get GPU memory information."""
        if not self.has_gpu():
            return {'available': False}
            
        info = {'available': True}
        
        if self.has_torch:
            import torch
            if self.torch_available:
                info['torch'] = {
                    'allocated': torch.cuda.memory_allocated(device_id),
                    'cached': torch.cuda.memory_reserved(device_id),
                }
                
        if self.has_tf:
            import tensorflow as tf
            if self.tf_available:
                # TensorFlow memory info
                pass
                
        return info
        
    def clear_cache(self, device_id: int = 0):
        """Clear GPU cache."""
        if self.has_torch and self.torch_available:
            import torch
            torch.cuda.empty_cache()
            print(f"🗑️  Cleared PyTorch GPU cache for device {device_id}")
            
def optimize_dataframe(df, inplace: bool = False):
    """
    Optimize pandas DataFrame memory usage.
    
    Args:
        df: DataFrame to optimize
        inplace: Whether to modify inplace
        
    Returns:
        Optimized DataFrame
    """
    import pandas as pd
    import numpy as np
    
    if not inplace:
        df = df.copy()
        
    # Optimize integers
    for col in df.select_dtypes(include=['int']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
        
    # Optimize floats
    for col in df.select_dtypes(include=['float']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
        
    # Convert objects to categories if appropriate
    for col in df.select_dtypes(include=['object']).columns:
        num_unique = df[col].nunique()
        num_total = len(df[col])
        
        if num_unique / num_total < 0.5:  # Less than 50% unique
            df[col] = df[col].astype('category')
            
    return df

def batch_iterator(items: list, batch_size: int):
    """
    Iterate over items in batches.
    
    Args:
        items: List of items
        batch_size: Size of each batch
        
    Yields:
        Batches of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]
