"""FlowyML Artifact Routing - Automatic Type-Based Artifact Routing.

This module provides automatic routing of step outputs to appropriate
infrastructure based on their Python types. When a step returns a
`Model`, `Dataset`, `Metrics`, or other artifact type, the runtime
automatically routes it to the configured stores and registries.

Usage:
    from flowyml.core.routing import route_artifact

    # After step execution
    result = step.func(**inputs)

    # Route based on type and stack config
    artifact_info = route_artifact(
        output=result,
        step_name="train_model",
        run_id="run-123",
    )

The routing is configured via flowyml.yaml:
    stacks:
      gcp-prod:
        artifact_routing:
          Model: { store: gcs, register: true }
          Dataset: { store: gcs }
          Metrics: { log_to_tracker: true }
"""

import logging
from typing import Any, get_type_hints
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RoutingResult:
    """Result of artifact routing.

    Attributes:
        artifact_type: Name of the artifact type (Model, Dataset, etc.)
        store_uri: URI where the artifact was stored
        registered: Whether the artifact was registered (e.g., in model registry)
        deployed: Whether the artifact was deployed (e.g., to endpoint)
        endpoint_uri: URI of the deployment endpoint
        logged: Whether the artifact was logged (e.g., metrics to tracker)
        metadata: Additional metadata from routing
    """

    artifact_type: str | None = None
    store_uri: str | None = None
    registered: bool = False
    deployed: bool = False
    endpoint_uri: str | None = None
    logged: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def get_step_return_type(step_func: callable) -> type | None:
    """Get the return type annotation from a step function.

    Args:
        step_func: The step function to inspect.

    Returns:
        The return type annotation, or None if not annotated.
    """
    try:
        hints = get_type_hints(step_func)
        return hints.get("return")
    except Exception:
        # Fallback to __annotations__ if get_type_hints fails
        try:
            return step_func.__annotations__.get("return")
        except Exception:
            return None


def detect_artifact_type(output: Any) -> str | None:
    """Detect the artifact type from an output value.

    This checks if the output is an instance of one of our artifact types
    or if it matches specific patterns (like dict for Metrics).

    Args:
        output: The step output value.

    Returns:
        Type name string or None.
    """
    # Import types here to avoid circular imports
    from flowyml.core.types import Artifact, Model, Dataset, Metrics, Parameters

    if isinstance(output, Model):
        return "Model"
    elif isinstance(output, Dataset):
        return "Dataset"
    elif isinstance(output, Metrics):
        return "Metrics"
    elif isinstance(output, Parameters):
        return "Parameters"
    elif isinstance(output, Artifact):
        return type(output).__name__

    return None


def route_artifact(
    output: Any,
    step_name: str,
    run_id: str,
    return_type: type | None = None,
    project_name: str = "default",
) -> RoutingResult:
    """Route a step output to appropriate infrastructure based on type.

    This is the main entry point for type-based artifact routing.
    It inspects the output type and routes to configured stores/registries.

    Args:
        output: The step output to route.
        step_name: Name of the step that produced this output.
        run_id: Current run identifier.
        return_type: Optional return type annotation (if known).
        project_name: Project name for namespacing.

    Returns:
        RoutingResult with routing information.
    """
    result = RoutingResult()

    # Skip None outputs
    if output is None:
        return result

    # Detect artifact type
    artifact_type = detect_artifact_type(output)

    # If not detected from value, try from type annotation
    if artifact_type is None and return_type is not None:
        try:
            type_name = return_type.__name__ if hasattr(return_type, "__name__") else str(return_type)
            if type_name in ("Model", "Dataset", "Metrics", "Parameters"):
                artifact_type = type_name
        except Exception:
            pass

    if artifact_type is None:
        # Not a routable artifact type
        return result

    result.artifact_type = artifact_type
    logger.debug(f"Routing {artifact_type} artifact from step '{step_name}'")

    # Get routing configuration from active stack
    try:
        from flowyml.plugins.stack_config import get_routing_for_type, get_active_stack

        routing_rule = get_routing_for_type(artifact_type)
        stack = get_active_stack()

        if routing_rule is None:
            logger.debug(f"No routing rule for {artifact_type}, using defaults")
            return result

        # Route to artifact store
        if routing_rule.store:
            result.store_uri = _save_to_store(
                output=output,
                artifact_type=artifact_type,
                store_name=routing_rule.store,
                path=routing_rule.format_path(
                    run_id=run_id,
                    step_name=step_name,
                    artifact_name=artifact_type.lower(),
                ),
                stack=stack,
            )

        # Register model if configured
        if routing_rule.register and artifact_type == "Model":
            result.registered = _register_model(
                output=output,
                step_name=step_name,
                run_id=run_id,
                stack=stack,
            )

        # Deploy model if configured and conditions are met
        # Note: deploy=True just enables deployment - actual deployment depends on deploy_condition
        if routing_rule.deploy and artifact_type == "Model":
            # Get metrics from model metadata for conditional deployment
            model_metrics = None
            if hasattr(output, "metadata") and output.metadata:
                model_metrics = output.metadata.get("metrics", {})

            # Check if auto-deployment should proceed
            if routing_rule.should_auto_deploy(model_metrics):
                endpoint_name = routing_rule.endpoint_name or f"{step_name}-endpoint"
                result.deployed, result.endpoint_uri = _deploy_model(
                    output=output,
                    step_name=step_name,
                    run_id=run_id,
                    endpoint_name=endpoint_name,
                    stack=stack,
                )
            else:
                # Log that deployment is pending approval/manual action
                condition = routing_rule.deploy_condition
                if condition == "manual":
                    logger.info(
                        f"Model registered but not deployed (deploy_condition='manual'). "
                        f"Use 'flowyml model deploy {output.name}' to deploy.",
                    )
                elif condition == "on_approval":
                    logger.info("Model registered, awaiting approval for deployment.")
                elif condition == "auto" and routing_rule.deploy_min_metrics:
                    logger.info(
                        f"Model not deployed - metrics did not meet thresholds: {routing_rule.deploy_min_metrics}",
                    )

        # Log metrics if configured
        if routing_rule.log_to_tracker and artifact_type == "Metrics":
            result.logged = _log_metrics(
                output=output,
                step_name=step_name,
                run_id=run_id,
                stack=stack,
            )

        # Log parameters if configured
        if routing_rule.log_to_tracker and artifact_type == "Parameters":
            result.logged = _log_parameters(
                output=output,
                step_name=step_name,
                run_id=run_id,
                stack=stack,
            )

        # Add routing metadata
        result.metadata = {
            "store": routing_rule.store,
            "path": routing_rule.path,
            "registered": result.registered,
            "deployed": result.deployed,
            "logged": result.logged,
        }

    except ImportError:
        logger.debug("Stack config not available, skipping routing")
    except Exception as e:
        logger.warning(f"Error during artifact routing: {e}")

    return result


def _save_to_store(
    output: Any,
    artifact_type: str,
    store_name: str,
    path: str,
    stack: Any,
) -> str | None:
    """Save artifact to the configured store.

    Args:
        output: The artifact to save.
        artifact_type: Type of the artifact.
        store_name: Name of the store (gcs, s3, local).
        path: Path within the store.
        stack: Stack configuration.

    Returns:
        URI of the saved artifact or None.
    """
    try:
        # Get artifact store from stack
        if store_name and stack and stack.artifact_stores:
            store_config = stack.artifact_stores.get(store_name)
            if store_config:
                # Instantiate and use the store
                from flowyml.plugins.config import get_artifact_store

                store = get_artifact_store()
                if store:
                    # Extract data if it's an Artifact wrapper
                    from flowyml.core.types import Artifact

                    data = output.data if isinstance(output, Artifact) else output
                    return store.save(data, path)

        # Fallback to default artifact store
        from flowyml.plugins.config import get_artifact_store

        store = get_artifact_store()
        if store:
            from flowyml.core.types import Artifact

            data = output.data if isinstance(output, Artifact) else output
            return store.save(data, path)

    except Exception as e:
        logger.warning(f"Failed to save artifact to store: {e}")

    return None


def _register_model(
    output: Any,
    step_name: str,
    run_id: str,
    stack: Any,
) -> bool:
    """Register a model in the model registry.

    Args:
        output: The Model artifact.
        step_name: Step that produced the model.
        run_id: Current run ID.
        stack: Stack configuration.

    Returns:
        True if registration was successful.
    """
    try:
        from flowyml.core.types import Model

        if not isinstance(output, Model):
            return False

        # Get model registry from plugins
        from flowyml.plugins.config import get_config

        config = get_config()
        registry = config._get_plugin("model_registry")

        if registry:
            model_name = output.name or f"{step_name}_model"
            model_uri = output.uri or f"runs/{run_id}/models/{step_name}"

            registry.register_model(
                name=model_name,
                model_uri=model_uri,
                version=output.version,
                metadata={
                    "framework": output.framework,
                    "step_name": step_name,
                    "run_id": run_id,
                    **output.metadata,
                },
            )
            logger.info(f"Registered model '{model_name}' to registry")
            return True

    except Exception as e:
        logger.warning(f"Failed to register model: {e}")

    return False


def _deploy_model(
    output: Any,
    step_name: str,
    run_id: str,
    endpoint_name: str,
    stack: Any,
) -> tuple[bool, str | None]:
    """Deploy a model to an endpoint.

    Args:
        output: The Model artifact.
        step_name: Step that produced the model.
        run_id: Current run ID.
        endpoint_name: Name for the endpoint.
        stack: Stack configuration.

    Returns:
        Tuple of (success, endpoint_uri).
    """
    try:
        from flowyml.core.types import Model

        if not isinstance(output, Model):
            return False, None

        # Get model deployer from stack config
        if stack and stack.model_deployer:
            deployer_config = stack.model_deployer
            deployer_type = deployer_config.get("type", "")

            deployer = None

            # Instantiate the appropriate deployer
            if "vertex" in deployer_type:
                from flowyml.plugins.deployers.vertex import VertexEndpointDeployer

                deployer = VertexEndpointDeployer(
                    project=deployer_config.get("project"),
                    location=deployer_config.get("location", "us-central1"),
                )
            elif "sagemaker" in deployer_type:
                from flowyml.plugins.deployers.sagemaker import SageMakerEndpointDeployer

                deployer = SageMakerEndpointDeployer(
                    region=deployer_config.get("region"),
                    role_arn=deployer_config.get("role_arn"),
                )

            if deployer:
                deployer.initialize()

                # Get model URI (from artifact store or output)
                model_uri = output.uri or f"runs/{run_id}/models/{step_name}"

                endpoint_uri = deployer.deploy(
                    model_uri=model_uri,
                    endpoint_name=endpoint_name,
                )

                logger.info(f"Deployed model to endpoint: {endpoint_uri}")
                return True, endpoint_uri

        # No deployer configured
        logger.debug("No model deployer configured in stack")
        return False, None

    except Exception as e:
        logger.warning(f"Failed to deploy model: {e}")

    return False, None


def _log_metrics(
    output: Any,
    step_name: str,
    run_id: str,
    stack: Any,
) -> bool:
    """Log metrics to the experiment tracker.

    Args:
        output: The Metrics artifact (dict-like).
        step_name: Step that produced the metrics.
        run_id: Current run ID.
        stack: Stack configuration.

    Returns:
        True if logging was successful.
    """
    try:
        from flowyml.core.types import Metrics
        from flowyml.plugins.config import get_tracker

        tracker = get_tracker()
        if tracker:
            # Get metrics values
            if isinstance(output, Metrics):
                metrics_dict = dict(output)
                step_num = output._step
            else:
                metrics_dict = dict(output)
                step_num = None

            tracker.log_metrics(metrics_dict, step=step_num)
            logger.debug(f"Logged metrics from step '{step_name}': {list(metrics_dict.keys())}")
            return True

    except Exception as e:
        logger.warning(f"Failed to log metrics: {e}")

    return False


def _log_parameters(
    output: Any,
    step_name: str,
    run_id: str,
    stack: Any,
) -> bool:
    """Log parameters to the experiment tracker.

    Args:
        output: The Parameters artifact (dict-like).
        step_name: Step that uses the parameters.
        run_id: Current run ID.
        stack: Stack configuration.

    Returns:
        True if logging was successful.
    """
    try:
        from flowyml.core.types import Parameters
        from flowyml.plugins.config import get_tracker

        tracker = get_tracker()
        if tracker:
            # Get parameter values
            if isinstance(output, Parameters):
                params_dict = dict(output)
            else:
                params_dict = dict(output)

            # Log parameters (with step prefix for clarity)
            prefixed_params = {f"{step_name}/{k}": v for k, v in params_dict.items()}
            tracker.log_params(prefixed_params)
            logger.debug(f"Logged parameters from step '{step_name}': {list(params_dict.keys())}")
            return True

    except Exception as e:
        logger.warning(f"Failed to log parameters: {e}")

    return False


def should_route(output: Any) -> bool:
    """Check if an output should be routed.

    Args:
        output: The step output.

    Returns:
        True if the output should be routed.
    """
    if output is None:
        return False

    from flowyml.core.types import is_artifact_type

    return is_artifact_type(output)


def auto_route_metrics_and_params(
    output: Any,
    step_name: str,
    run_id: str,
) -> bool:
    """Automatically route Metrics and Parameters without explicit config.

    This is a convenience function that can be called to log Metrics
    and Parameters even when no routing rule is configured.

    Args:
        output: The step output.
        step_name: Step name.
        run_id: Run ID.

    Returns:
        True if logging was successful.
    """
    from flowyml.core.types import Metrics, Parameters

    if isinstance(output, Metrics):
        return _log_metrics(output, step_name, run_id, None)
    elif isinstance(output, Parameters):
        return _log_parameters(output, step_name, run_id, None)

    return False
