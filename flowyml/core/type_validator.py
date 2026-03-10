"""Build-time type validation for pipeline connections.

Validates Python type annotations between connected steps at DAG build time,
catching type mismatches early instead of at runtime.

Inspired by Flyte's IDL-based type enforcement, adapted for Python's type system.

Usage:
    from flowyml.core.type_validator import TypeValidator, validate_pipeline

    # Automatic (called from Pipeline.build())
    errors, warnings = validate_pipeline(dag, steps)

    # Manual
    validator = TypeValidator()
    issues = validator.validate_connection(producer_step, consumer_step, "dataset")
"""

import logging
from dataclasses import dataclass
from typing import Any, Union, get_type_hints, get_origin, get_args

logger = logging.getLogger(__name__)


@dataclass
class TypeIssue:
    """A type validation issue found during pipeline build.

    Attributes:
        level: Severity level ('error' or 'warning')
        producer_step: Name of the step producing the output
        consumer_step: Name of the step consuming the input
        asset_name: Name of the asset/connection
        message: Human-readable description of the issue
        producer_type: String representation of the producer's type
        consumer_type: String representation of the consumer's type
    """

    level: str  # "error" or "warning"
    producer_step: str
    consumer_step: str
    asset_name: str
    message: str
    producer_type: str = ""
    consumer_type: str = ""

    def __str__(self) -> str:
        icon = "❌" if self.level == "error" else "⚠️"
        return (
            f"{icon} Type mismatch on '{self.asset_name}': "
            f"step '{self.producer_step}' outputs {self.producer_type or '?'} "
            f"→ step '{self.consumer_step}' expects {self.consumer_type or '?'} "
            f"— {self.message}"
        )


class TypeValidator:
    """Validates type compatibility between connected pipeline steps.

    Inspects Python type annotations on step functions and checks that
    producer return types are compatible with consumer parameter types
    for each shared asset/connection.

    Example:
        >>> validator = TypeValidator()
        >>> issues = validator.validate_connection(train_step, eval_step, "model")
        >>> for issue in issues:
        ...     print(issue)
    """

    # Types that are always compatible (pass-through)
    _PASSTHROUGH_TYPES = {Any, object}

    def validate_connection(
        self,
        producer_step: Any,
        consumer_step: Any,
        asset_name: str,
    ) -> list[TypeIssue]:
        """Validate type compatibility between a producer and consumer step.

        Args:
            producer_step: Step that produces the asset
            consumer_step: Step that consumes the asset
            asset_name: Name of the shared asset

        Returns:
            List of TypeIssue objects (empty if compatible)
        """
        issues = []

        producer_return_type = self._get_return_type(producer_step)
        consumer_param_type = self._get_param_type_for_asset(consumer_step, asset_name)

        # If either side lacks annotations, just warn
        if producer_return_type is None and consumer_param_type is None:
            return issues  # No annotations, nothing to validate

        if producer_return_type is None:
            issues.append(
                TypeIssue(
                    level="warning",
                    producer_step=producer_step.name,
                    consumer_step=consumer_step.name,
                    asset_name=asset_name,
                    message=f"Step '{producer_step.name}' has no return type annotation — cannot validate output type",
                    producer_type="<untyped>",
                    consumer_type=self._type_name(consumer_param_type) if consumer_param_type else "<untyped>",
                ),
            )
            return issues

        if consumer_param_type is None:
            # Producer is typed but consumer isn't — this is fine (consumer accepts anything)
            return issues

        # Both are typed — check compatibility
        if not self._is_compatible(producer_return_type, consumer_param_type):
            issues.append(
                TypeIssue(
                    level="error",
                    producer_step=producer_step.name,
                    consumer_step=consumer_step.name,
                    asset_name=asset_name,
                    message=(
                        f"Type mismatch: '{producer_step.name}' returns "
                        f"{self._type_name(producer_return_type)} but "
                        f"'{consumer_step.name}' expects {self._type_name(consumer_param_type)}"
                    ),
                    producer_type=self._type_name(producer_return_type),
                    consumer_type=self._type_name(consumer_param_type),
                ),
            )

        return issues

    def _get_return_type(self, step: Any) -> type | None:
        """Extract return type annotation from a step's function.

        Args:
            step: Step object with a .func attribute

        Returns:
            Return type or None if not annotated
        """
        func = getattr(step, "func", None)
        if func is None:
            return None

        try:
            hints = get_type_hints(func)
            return hints.get("return")
        except Exception:
            # Fallback to __annotations__
            try:
                annotations = getattr(func, "__annotations__", {})
                return annotations.get("return")
            except Exception:
                return None

    def _get_param_type_for_asset(self, step: Any, asset_name: str) -> type | None:
        """Get the parameter type for a specific asset input.

        Maps the asset name to a function parameter and returns its type.

        For steps with explicit inputs like `inputs=["dataset"]`, we try to
        find a parameter named like the asset (with / stripped) or fall back
        to the first non-context parameter.

        Args:
            step: Step object with a .func attribute
            asset_name: Name of the asset being consumed

        Returns:
            Parameter type or None if not annotated
        """
        func = getattr(step, "func", None)
        if func is None:
            return None

        try:
            hints = get_type_hints(func)
        except Exception:
            try:
                hints = getattr(func, "__annotations__", {})
            except Exception:
                return {}

        # Remove 'return' from hints
        param_hints = {k: v for k, v in hints.items() if k != "return"}

        if not param_hints:
            return None

        # Try exact match first (e.g., asset "dataset" → param "dataset")
        clean_name = asset_name.split("/")[-1]  # "data/train" → "train"
        if clean_name in param_hints:
            return param_hints[clean_name]

        # Try the full asset name with / replaced
        normalized = asset_name.replace("/", "_")
        if normalized in param_hints:
            return param_hints[normalized]

        # If step has only one input asset and one typed param (excluding context),
        # assume they correspond
        step_inputs = getattr(step, "inputs", [])
        if len(step_inputs) == 1 and asset_name == step_inputs[0]:
            # Get the first non-self, non-context parameter
            import inspect

            sig = inspect.signature(func)
            for param_name, _param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                if param_name in param_hints:
                    return param_hints[param_name]

        return None

    def _is_compatible(self, producer_type: type, consumer_type: type) -> bool:
        """Check if producer output type is compatible with consumer input type.

        Handles:
        - Direct type matches
        - Subclass relationships
        - Union types (Optional, Union[A, B])
        - Any type (always compatible)
        - FlowyML artifact types

        Args:
            producer_type: Type annotation of the producer's output
            consumer_type: Type annotation of the consumer's input

        Returns:
            True if types are compatible
        """
        # Any is always compatible
        if producer_type is Any or consumer_type is Any:
            return True

        # None check
        if producer_type is None or consumer_type is None:
            return True

        # Handle Optional / Union on consumer side
        consumer_origin = get_origin(consumer_type)
        if consumer_origin is Union:
            consumer_args = get_args(consumer_type)
            # Producer must be compatible with at least one branch of the Union
            return any(self._is_compatible(producer_type, arg) for arg in consumer_args)

        # Handle Union on producer side
        producer_origin = get_origin(producer_type)
        if producer_origin is Union:
            producer_args = get_args(producer_type)
            # ALL branches of the producer Union must be compatible with consumer
            return all(self._is_compatible(arg, consumer_type) for arg in producer_args)

        # Handle generic types (list[int], dict[str, float], etc.)
        if get_origin(producer_type) is not None or get_origin(consumer_type) is not None:
            p_origin = get_origin(producer_type) or producer_type
            c_origin = get_origin(consumer_type) or consumer_type
            try:
                if isinstance(p_origin, type) and isinstance(c_origin, type):
                    return issubclass(p_origin, c_origin)
            except TypeError:
                return True  # Can't determine, assume compatible

        # Direct type comparison
        try:
            if isinstance(producer_type, type) and isinstance(consumer_type, type):
                return issubclass(producer_type, consumer_type)
        except TypeError:
            pass

        # String comparison fallback
        return self._type_name(producer_type) == self._type_name(consumer_type)

    def _type_name(self, t: type | None) -> str:
        """Get a human-readable name for a type.

        Args:
            t: Type to name

        Returns:
            Human-readable type name string
        """
        if t is None:
            return "<untyped>"

        if hasattr(t, "__name__"):
            return t.__name__

        # Handle Union, Optional, generic types
        return str(t).replace("typing.", "")


def validate_pipeline(
    dag: Any,
    steps: list[Any],
    strict: bool = False,
) -> tuple[list[TypeIssue], list[TypeIssue]]:
    """Validate type annotations across all connections in a pipeline DAG.

    This is the main entry point called from Pipeline.build().

    Args:
        dag: The pipeline DAG with nodes and edges
        steps: List of Step objects
        strict: If True, treat warnings as errors

    Returns:
        Tuple of (errors, warnings) — lists of TypeIssue objects
    """
    validator = TypeValidator()
    errors: list[TypeIssue] = []
    warnings: list[TypeIssue] = []

    # Build step lookup
    step_map = {s.name: s for s in steps}

    # For each edge (asset connection), validate types
    for consumer_name, dependencies in dag.edges.items():
        consumer_step = step_map.get(consumer_name)
        if consumer_step is None:
            continue

        for producer_name in dependencies:
            producer_step = step_map.get(producer_name)
            if producer_step is None:
                continue

            # Find the shared asset(s) between producer and consumer
            shared_assets = set(producer_step.outputs) & set(consumer_step.inputs)

            for asset_name in shared_assets:
                issues = validator.validate_connection(
                    producer_step=producer_step,
                    consumer_step=consumer_step,
                    asset_name=asset_name,
                )

                for issue in issues:
                    if issue.level == "error" or (strict and issue.level == "warning"):
                        errors.append(issue)
                    else:
                        warnings.append(issue)

    # Log results
    if warnings:
        for w in warnings:
            logger.warning(str(w))

    if errors:
        for e in errors:
            logger.error(str(e))

    return errors, warnings
