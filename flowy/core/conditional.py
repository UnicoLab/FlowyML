"""Conditional execution for dynamic pipelines."""

from typing import Callable, Any, Optional
from functools import wraps


class Condition:
    """Condition for conditional step execution.

    Example:
        ```python
        from flowy import step, Condition

        @step
        def check_quality(data):
            return {"score": 0.95, "needs_cleaning": False}

        @step
        @Condition(lambda result: result["needs_cleaning"])
        def clean_data(data, quality_result):
            return cleaned_data
        ```
    """

    def __init__(self, condition_func: Callable[[Any], bool]):
        """Initialize condition.

        Args:
            condition_func: Function that takes step inputs and returns bool
        """
        self.condition_func = condition_func

    def should_execute(self, *args, **kwargs) -> bool:
        """Check if condition is met.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            True if step should execute
        """
        try:
            # Try to evaluate with first argument if available
            if args:
                return bool(self.condition_func(args[0]))
            elif kwargs:
                # Try with all kwargs
                return bool(self.condition_func(kwargs))
            return False
        except Exception:
            # If condition evaluation fails, don't execute
            return False

    def __call__(self, func: Callable) -> Callable:
        """Decorator to add conditional execution.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.should_execute(*args, **kwargs):
                return func(*args, **kwargs)
            else:
                # Return None or a special marker for skipped execution
                return SkippedExecution(func.__name__)

        # Mark function as conditional
        wrapper._is_conditional = True
        wrapper._condition = self

        return wrapper


class SkippedExecution:
    """Marker for skipped conditional execution."""

    def __init__(self, step_name: str):
        self.step_name = step_name
        self.skipped = True

    def __repr__(self):
        return f"<SkippedExecution: {self.step_name}>"

    def __bool__(self):
        return False


def condition(condition_func: Callable[[Any], bool]) -> Condition:
    """Create a condition decorator.

    Args:
        condition_func: Function that evaluates to bool

    Returns:
        Condition decorator

    Example:
        ```python
        @step
        @condition(lambda x: x["quality"] > 0.9)
        def train_complex_model(data):
            return complex_model
        ```
    """
    return Condition(condition_func)


class ConditionalBranch:
    """Branch execution based on condition.

    Example:
        ```python
        from flowy import ConditionalBranch

        branch = ConditionalBranch()

        @branch.if_condition(lambda x: x > 10)
        def process_large(data):
            return process_with_large_model(data)

        @branch.else_condition()
        def process_small(data):
            return process_with_small_model(data)
        ```
    """

    def __init__(self):
        self.if_func: Optional[Callable] = None
        self.if_condition_func: Optional[Callable] = None
        self.else_func: Optional[Callable] = None
        self.elif_branches: list[tuple[Callable, Callable]] = []

    def if_condition(self, condition_func: Callable[[Any], bool]) -> Callable:
        """Define if branch.

        Args:
            condition_func: Condition function

        Returns:
            Decorator
        """
        def decorator(func: Callable) -> Callable:
            self.if_func = func
            self.if_condition_func = condition_func
            return func
        return decorator

    def elif_condition(self, condition_func: Callable[[Any], bool]) -> Callable:
        """Define elif branch.

        Args:
            condition_func: Condition function

        Returns:
            Decorator
        """
        def decorator(func: Callable) -> Callable:
            self.elif_branches.append((condition_func, func))
            return func
        return decorator

    def else_condition(self) -> Callable:
        """Define else branch.

        Returns:
            Decorator
        """
        def decorator(func: Callable) -> Callable:
            self.else_func = func
            return func
        return decorator

    def execute(self, *args, **kwargs) -> Any:
        """Execute appropriate branch based on conditions.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from executed branch
        """
        # Try if condition
        if self.if_func and self.if_condition_func:
            try:
                if self.if_condition_func(*args, **kwargs):
                    return self.if_func(*args, **kwargs)
            except Exception:
                pass

        # Try elif conditions
        for condition_func, func in self.elif_branches:
            try:
                if condition_func(*args, **kwargs):
                    return func(*args, **kwargs)
            except Exception:
                pass

        # Execute else
        if self.else_func:
            return self.else_func(*args, **kwargs)

        # No branch executed
        return None


class Switch:
    """Switch-case style conditional execution.

    Example:
        ```python
        from flowy import Switch

        switch = Switch(lambda x: x["type"])

        @switch.case("image")
        def process_image(data):
            return process_image_data(data)

        @switch.case("text")
        def process_text(data):
            return process_text_data(data)

        @switch.default()
        def process_other(data):
            return process_generic(data)
        ```
    """

    def __init__(self, selector_func: Callable[[Any], Any]):
        """Initialize switch.

        Args:
            selector_func: Function to select case value
        """
        self.selector_func = selector_func
        self.cases: dict[Any, Callable] = {}
        self.default_func: Optional[Callable] = None

    def case(self, value: Any) -> Callable:
        """Define a case branch.

        Args:
            value: Value to match

        Returns:
            Decorator
        """
        def decorator(func: Callable) -> Callable:
            self.cases[value] = func
            return func
        return decorator

    def default(self) -> Callable:
        """Define default branch.

        Returns:
            Decorator
        """
        def decorator(func: Callable) -> Callable:
            self.default_func = func
            return func
        return decorator

    def execute(self, *args, **kwargs) -> Any:
        """Execute appropriate case based on selector.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from executed case
        """
        # Get selector value
        try:
            selector_value = self.selector_func(*args, **kwargs)
        except Exception:
            selector_value = None

        # Find matching case
        if selector_value in self.cases:
            return self.cases[selector_value](*args, **kwargs)

        # Execute default
        if self.default_func:
            return self.default_func(*args, **kwargs)

        return None


def when(condition_func: Callable[[Any], bool]) -> Callable:
    """Simple conditional execution helper.

    Args:
        condition_func: Condition to evaluate

    Returns:
        Decorator that executes function only if condition is true

    Example:
        ```python
        @step
        @when(lambda data: len(data) > 1000)
        def process_large_dataset(data):
            return expensive_processing(data)
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if condition_func(*args, **kwargs):
                return func(*args, **kwargs)
            return SkippedExecution(func.__name__)
        return wrapper
    return decorator


def unless(condition_func: Callable[[Any], bool]) -> Callable:
    """Execute unless condition is true.

    Args:
        condition_func: Condition to evaluate

    Returns:
        Decorator that executes function only if condition is false

    Example:
        ```python
        @step
        @unless(lambda data: data["cached"])
        def compute_features(data):
            return expensive_computation(data)
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not condition_func(*args, **kwargs):
                return func(*args, **kwargs)
            return SkippedExecution(func.__name__)
        return wrapper
    return decorator
