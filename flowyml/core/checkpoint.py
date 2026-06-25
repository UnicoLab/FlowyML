"""Pipeline checkpointing for resumable execution."""

import json
import pickle
from pathlib import Path
from typing import Any
from datetime import datetime


class PipelineCheckpoint:
    """Save and restore pipeline execution state.

    Allows resuming failed pipelines from the last successful step.

    Examples:
        >>> checkpoint = PipelineCheckpoint(run_id="run_123")
        >>> # Save state after each step
        >>> checkpoint.save_step_state("step1", outputs)
        >>> # Resume from checkpoint
        >>> state = checkpoint.load()
        >>> last_step = state["last_completed_step"]
    """

    def __init__(
        self,
        run_id: str,
        checkpoint_dir: str = ".flowyml/checkpoints",
    ):
        self.run_id = run_id
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.checkpoint_file = self.checkpoint_dir / f"{run_id}.json"
        self.state_dir = self.checkpoint_dir / run_id
        self.state_dir.mkdir(exist_ok=True)

    def save_step_state(
        self,
        step_name: str,
        outputs: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save state after completing a step."""
        # Save outputs
        output_file = self.state_dir / f"{step_name}.pkl"
        with open(output_file, "wb") as f:
            pickle.dump(outputs, f)

        # Update checkpoint metadata
        checkpoint_data = self.load() if self.checkpoint_file.exists() else {}

        # Get existing completed steps (avoid duplicates)
        completed_steps = checkpoint_data.get("completed_steps", [])
        if step_name not in completed_steps:
            completed_steps.append(step_name)

        checkpoint_data.update(
            {
                "run_id": self.run_id,
                "last_completed_step": step_name,
                "last_update": datetime.now().isoformat(),
                "completed_steps": completed_steps,
                "step_metadata": checkpoint_data.get("step_metadata", {}),
            },
        )

        if metadata:
            checkpoint_data["step_metadata"][step_name] = metadata

        # Save checkpoint
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2)

    def load_step_state(self, step_name: str) -> Any:
        """Load state for a specific step."""
        output_file = self.state_dir / f"{step_name}.pkl"
        if not output_file.exists():
            raise FileNotFoundError(f"No checkpoint found for step: {step_name}")

        with open(output_file, "rb") as f:
            return pickle.load(f)

    def load(self) -> dict[str, Any]:
        """Load checkpoint metadata."""
        if not self.checkpoint_file.exists():
            return {}

        with open(self.checkpoint_file) as f:
            return json.load(f)

    def exists(self) -> bool:
        """Check if checkpoint exists."""
        return self.checkpoint_file.exists()

    def get_completed_steps(self) -> list:
        """Get list of completed steps."""
        data = self.load()
        return data.get("completed_steps", [])

    def save(self, data: dict[str, Any]) -> None:
        """Save arbitrary checkpoint data.

        This is a convenience method for saving full checkpoint state.
        For saving individual step results, use save_step_state().

        Args:
            data: Dictionary of checkpoint data to save
        """
        # Merge with existing data
        existing = self.load() if self.checkpoint_file.exists() else {}
        existing.update(data)
        existing.setdefault("run_id", self.run_id)
        existing.setdefault("last_update", datetime.now().isoformat())

        with open(self.checkpoint_file, "w") as f:
            json.dump(existing, f, indent=2)

    def clear(self) -> None:
        """Clear checkpoint data."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

        # Clear state files
        for file in self.state_dir.glob("*.pkl"):
            file.unlink()

    def resume_point(self) -> str | None:
        """Get the resume point (last completed step)."""
        data = self.load()
        return data.get("last_completed_step")


def checkpoint_enabled_pipeline(pipeline, run_id: str):
    """Wrap a pipeline to enable checkpointing.

    This is a decorator-style wrapper that adds checkpoint functionality.
    When resuming, completed steps are skipped and their cached outputs
    are injected automatically by the orchestrator.
    """
    checkpoint = PipelineCheckpoint(run_id)

    # Attach checkpoint to pipeline so orchestrator can access it
    pipeline._checkpoint = checkpoint

    # Store original run method
    original_run = pipeline.run

    def run_with_checkpoints(*args, **kwargs):
        """Modified run method with checkpointing."""
        if checkpoint.exists():
            completed = checkpoint.get_completed_steps()

            # Check if pipeline itself completed previously
            if "pipeline_complete" in completed:
                import warnings

                warnings.warn(
                    f"Pipeline run '{run_id}' already completed. "
                    "Re-running from scratch. Use a new run_id for fresh runs.",
                    stacklevel=2,
                )
                checkpoint.clear()
                pipeline._resume_from_checkpoint = False
                pipeline._completed_steps_from_checkpoint = set()
            else:
                # Resume: mark completed steps so orchestrator skips them
                pipeline._resume_from_checkpoint = True
                pipeline._completed_steps_from_checkpoint = set(completed)

                resume_pt = checkpoint.resume_point()
                import logging

                logger = logging.getLogger("flowyml.checkpoint")
                logger.info(
                    f"Resuming pipeline from checkpoint. Completed steps: {completed}. Last completed: {resume_pt}",
                )
        else:
            pipeline._resume_from_checkpoint = False
            pipeline._completed_steps_from_checkpoint = set()

        # Run the pipeline (orchestrator handles skip logic)
        result = original_run(*args, **kwargs)

        # Save final checkpoint on success
        if result.success:
            checkpoint.save_step_state(
                "pipeline_complete",
                result.outputs,
                metadata={"duration": result.duration_seconds},
            )

        return result

    # Replace run method
    pipeline.run = run_with_checkpoints

    return pipeline
