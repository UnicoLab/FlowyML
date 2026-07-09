"""Pipeline versioning system."""

import json
import hashlib
from pathlib import Path
from typing import Any, NoReturn
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class PipelineVersion:
    """Represents a pipeline version."""

    version: str
    pipeline_name: str
    created_at: str
    steps: list[str]
    step_hashes: dict[str, str]
    context_params: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class PipelineSnapshot:
    """Immutable snapshot of a pipeline definition at execution time.

    Created automatically when a pipeline runs, this captures the full
    definition (steps, code hashes, DAG, parameters) in a sealed format
    that cannot be modified after creation.

    Attributes:
        pipeline_name: Name of the pipeline
        snapshot_hash: SHA-256 hash of the entire snapshot (seal)
        created_at: ISO timestamp of when the snapshot was created
        version: Optional version string
        steps: Ordered list of step definitions
        dag_edges: DAG edges (list of {source, target} dicts)
        context_params: Context parameters at snapshot time
        step_hashes: Per-step code hashes for reproducibility
    """

    pipeline_name: str = ""
    snapshot_hash: str = ""
    created_at: str = ""
    version: str | None = None
    steps: list[dict[str, Any]] = None
    dag_edges: list[dict[str, str]] = None
    context_params: dict[str, Any] = None
    step_hashes: dict[str, str] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.dag_edges is None:
            self.dag_edges = []
        if self.context_params is None:
            self.context_params = {}
        if self.step_hashes is None:
            self.step_hashes = {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize snapshot to dictionary."""
        return asdict(self)

    def verify(self) -> bool:
        """Verify the snapshot hash is still valid (not tampered)."""
        data = {
            "pipeline_name": self.pipeline_name,
            "steps": self.steps,
            "dag_edges": self.dag_edges,
            "context_params": self.context_params,
            "step_hashes": self.step_hashes,
        }
        expected = hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode(),
        ).hexdigest()
        return self.snapshot_hash == expected


def freeze_pipeline(pipeline: Any) -> PipelineSnapshot:
    """Create an immutable snapshot of a pipeline's current state.

    Called automatically at Pipeline.run() time to capture the exact
    pipeline definition for reproducibility.

    Args:
        pipeline: Pipeline instance to snapshot

    Returns:
        Sealed PipelineSnapshot
    """

    # Ensure pipeline is built
    if not pipeline._built:
        pipeline.build()

    # Capture step definitions
    steps = []
    step_hashes = {}
    for step in pipeline.steps:
        step_def = {
            "name": step.name,
            "inputs": step.inputs,
            "outputs": step.outputs,
            "tags": getattr(step, "tags", []),
            "execution_group": getattr(step, "execution_group", None),
        }
        steps.append(step_def)

        # Hash the step source code
        source = getattr(step, "source_code", "") or ""
        step_hash = hashlib.sha256(source.encode()).hexdigest()
        step_hashes[step.name] = step_hash

    # Capture DAG edges
    dag_edges = [{"source": dep, "target": node_name} for node_name, deps in pipeline.dag.edges.items() for dep in deps]

    # Capture context
    context_params = {}
    if hasattr(pipeline, "context") and pipeline.context:
        context_params = dict(pipeline.context.params) if hasattr(pipeline.context, "params") else {}

    # Compute seal hash
    data = {
        "pipeline_name": pipeline.name,
        "steps": steps,
        "dag_edges": dag_edges,
        "context_params": context_params,
        "step_hashes": step_hashes,
    }
    snapshot_hash = hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode(),
    ).hexdigest()

    return PipelineSnapshot(
        pipeline_name=pipeline.name,
        snapshot_hash=snapshot_hash,
        created_at=datetime.now().isoformat(),
        version=getattr(pipeline, "version", None),
        steps=steps,
        dag_edges=dag_edges,
        context_params=context_params,
        step_hashes=step_hashes,
    )


class VersionedPipeline:
    """Pipeline with version control.

    Tracks changes between versions and allows comparison.

    Examples:
        >>> from flowyml import VersionedPipeline, step, context
        >>> ctx = context(learning_rate=0.001, epochs=10)
        >>> pipeline = VersionedPipeline("training", context=ctx, version="v1.0.0", project_name="ml_project")
        >>> pipeline.add_step(load_data)
        >>> pipeline.add_step(train_model)
        >>> pipeline.save_version()
        >>> # Make changes
        >>> pipeline.add_step(evaluate)
        >>> pipeline.version = "v1.1.0"
        >>> pipeline.save_version()
        >>> # Compare versions
        >>> diff = pipeline.compare_with("v1.0.0")

        # Or use Pipeline with version parameter (automatically creates VersionedPipeline)
        >>> from flowyml import Pipeline
        >>> pipeline = Pipeline("training", context=ctx, version="v1.0.1", project_name="ml_project")
    """

    def __init__(
        self,
        name: str,
        version: str = "v0.1.0",
        versions_dir: str = ".flowyml/versions",
        context: Any | None = None,
        **kwargs,
    ):
        from flowyml.core.pipeline import Pipeline

        self.name = name
        self._version = version
        # Pass context and other kwargs to the internal Pipeline
        # Remove 'version' from kwargs to avoid recursion
        pipeline_kwargs = {k: v for k, v in kwargs.items() if k != "version"}
        self.pipeline = Pipeline(name, context=context, **pipeline_kwargs)

        # Version storage
        self.versions_dir = Path(versions_dir) / name
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        # Load version history
        self.versions: dict[str, PipelineVersion] = {}
        self._load_versions()

    @property
    def version(self) -> str:
        """Get current version."""
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        """Set version."""
        self._version = value

    def add_step(self, step):
        """Add a step to the pipeline."""
        self.pipeline.add_step(step)
        return self

    def _compute_step_hash(self, step) -> str:
        """Compute hash of step definition."""
        # Hash based on source code
        if hasattr(step, "source_code") and step.source_code:
            return hashlib.md5(step.source_code.encode()).hexdigest()
        # Fallback to name
        return hashlib.md5(step.name.encode()).hexdigest()

    def save_version(self, metadata: dict[str, Any] | None = None):
        """Save current version."""
        # Compute step hashes
        step_hashes = {}
        step_names = []

        for step in self.pipeline.steps:
            step_names.append(step.name)
            step_hashes[step.name] = self._compute_step_hash(step)

        # Create version record
        version_data = PipelineVersion(
            version=self._version,
            pipeline_name=self.name,
            created_at=datetime.now().isoformat(),
            steps=step_names,
            step_hashes=step_hashes,
            context_params=self.pipeline.context._params if hasattr(self.pipeline.context, "_params") else {},
            metadata=metadata or {},
        )

        # Save to disk
        version_file = self.versions_dir / f"{self._version}.json"
        with open(version_file, "w") as f:
            json.dump(asdict(version_data), f, indent=2)

        self.versions[self._version] = version_data

        return version_data

    def _load_versions(self) -> None:
        """Load version history."""
        for version_file in self.versions_dir.glob("*.json"):
            with open(version_file) as f:
                data = json.load(f)
                version = data["version"]
                self.versions[version] = PipelineVersion(**data)

    def list_versions(self) -> list[str]:
        """List all saved versions."""
        return sorted(self.versions.keys())

    def get_version(self, version: str) -> PipelineVersion | None:
        """Get specific version details."""
        return self.versions.get(version)

    def compare_with(self, other_version: str) -> dict[str, Any]:
        """Compare current pipeline with another version.

        Returns:
            Dictionary with differences
        """
        if other_version not in self.versions:
            raise ValueError(f"Version {other_version} not found")

        current_steps = {s.name: self._compute_step_hash(s) for s in self.pipeline.steps}
        other = self.versions[other_version]

        # Find differences
        added_steps = set(current_steps.keys()) - set(other.steps)
        removed_steps = set(other.steps) - set(current_steps.keys())

        # Modified steps (same name, different hash)
        modified_steps = []
        for step_name in set(current_steps.keys()) & set(other.steps):
            if current_steps[step_name] != other.step_hashes.get(step_name):
                modified_steps.append(step_name)

        comparison = {
            "current_version": self._version,
            "compared_to": other_version,
            "added_steps": list(added_steps),
            "removed_steps": list(removed_steps),
            "modified_steps": modified_steps,
            "step_order_changed": current_steps.keys() != other.steps,
            "context_changes": self._compare_dicts(
                self.pipeline.context._params if hasattr(self.pipeline.context, "_params") else {},
                other.context_params,
            ),
        }

        return comparison

    def _compare_dicts(self, d1: dict, d2: dict) -> dict[str, Any]:
        """Compare two dictionaries."""
        added = set(d1.keys()) - set(d2.keys())
        removed = set(d2.keys()) - set(d1.keys())
        modified = {k for k in set(d1.keys()) & set(d2.keys()) if d1[k] != d2[k]}

        return {
            "added": {k: d1[k] for k in added},
            "removed": {k: d2[k] for k in removed},
            "modified": {k: {"old": d2[k], "new": d1[k]} for k in modified},
        }

    def display_comparison(self, other_version: str) -> None:
        """Display comparison in readable format."""
        import logging

        logger = logging.getLogger(__name__)

        diff = self.compare_with(other_version)

        logger.info(
            "Version comparison: %s vs %s",
            self.version,
            other_version,
        )

        if diff["added_steps"]:
            logger.info("  Added steps: %s", ", ".join(diff["added_steps"]))

        if diff["removed_steps"]:
            logger.info("  Removed steps: %s", ", ".join(diff["removed_steps"]))

        if diff["modified_steps"]:
            logger.info("  Modified steps: %s", ", ".join(diff["modified_steps"]))

        if diff["step_order_changed"]:
            logger.info("  Step order has changed")

        changes = diff["context_changes"]
        if any([changes["added"], changes["removed"], changes["modified"]]):
            if changes["added"]:
                logger.info("  Added context params: %s", changes["added"])
            if changes["removed"]:
                logger.info("  Removed context params: %s", changes["removed"])
            if changes["modified"]:
                logger.info("  Modified context params: %s", changes["modified"])

        if not any(
            [
                diff["added_steps"],
                diff["removed_steps"],
                diff["modified_steps"],
                diff["step_order_changed"],
                changes["added"],
                changes["removed"],
                changes["modified"],
            ],
        ):
            logger.info("  No differences found")

    def rollback(self, version: str) -> NoReturn:
        """Rollback to a previous version (not implemented - would need to reconstruct pipeline)."""
        raise NotImplementedError("Rollback requires pipeline reconstruction from saved state")

    def run(self, *args, **kwargs):
        """Run the pipeline."""
        return self.pipeline.run(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate to underlying pipeline."""
        return getattr(self.pipeline, name)
